"""Submission API endpoints - refactored"""
import json
import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, Request, HTTPException, Query
from fastapi.responses import StreamingResponse, JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core import get_db
from app.core.config import config
from app.routes.deps import get_current_user_optional
from app.services.submission_service import SubmissionService
from app.services.rate_limit_service import RateLimitService
from app.models.user import User
from app.utils.generic_stream import stream_challenge
from app.utils.fingerprint import generate_fingerprint
from app.challenges import ChallengeRegistry
from app.challenges.base import ChallengeResult, ChallengeStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="", tags=["submissions"])

@router.post("/submit")
async def submit_agent(request: Request):
    """The old in-process Python sandbox is unsafe and has been retired."""
    return JSONResponse(status_code=410, content={"error": "Code submissions are disabled. Open a challenge page to play a prompt game."})


@router.get("/submission/{submission_id}", response_class=HTMLResponse)
async def get_submission(
    request: Request,
    submission_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    """Get an owned submission, including its private conversation."""
    submission_service = SubmissionService(db)
    submission = submission_service.get_submission(submission_id)
    
    from app.routes.runs import player
    owner = player(request, db, current_user)
    if not submission or owner is None or owner.id != submission.user_id:
        raise HTTPException(404, "Submission not found")
    
    # Render template instead of JSON
    BASE_DIR = Path(__file__).resolve().parent.parent
    templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
    
    return templates.TemplateResponse(request,
        "submission_detail.html",
        {"request": request, "submission": submission}
    )


from app.schemas.submission import SubmissionResponse


@router.get("/recent", response_model=list[SubmissionResponse])
async def get_recent_submissions(
    challenge_name: Optional[str] = None,
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Get recent submissions"""
    submission_service = SubmissionService(db)
    submissions = submission_service.get_recent_submissions(challenge_name, limit)
    return submissions


@router.post("/submit/stream")
async def submit_agent_stream(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    """
    Submit an agent and stream challenge progress in real-time (SSE)
    Supports: debate_battle, giga_chad (all difficulties)
    """
    # Legacy prompt form. Code submissions are never executed here.
    form = await request.form()
    challenge_name = form.get("challenge_name")
    agent_code = form.get("agent_code")
    difficulty = form.get("difficulty")
    if not all(isinstance(value, str) for value in (challenge_name, agent_code)):
        raise HTTPException(422, "Expected text challenge_name and agent_code")
    if difficulty is not None and not isinstance(difficulty, str):
        raise HTTPException(422, "Expected a text difficulty")
    from app.challenges.runtime import PersistedGame
    cls = ChallengeRegistry.get(challenge_name)
    if cls and issubclass(cls, PersistedGame):
        return JSONResponse(status_code=410, content={"error": "This game now uses /api/runs. Reload the challenge page."})
    if len(agent_code or "") > 8000:
        return JSONResponse(status_code=413, content={"error": "Prompt too long"})

    # Validate required fields
    if not challenge_name or not agent_code:
        return JSONResponse(
            content={"error": "Missing challenge_name or agent_code"},
            status_code=400
        )
    
    # Generate user fingerprint for rate limiting (IP + User-Agent hash)
    fingerprint = generate_fingerprint(request)
    
    # Check rate limit
    rate_limit_service = RateLimitService(db)
    try:
        rate_limit_service.check_rate_limit(fingerprint, "/submit/stream", "fingerprint")
    except Exception as e:
        return JSONResponse(
            content={"error": str(e)},
            status_code=429
        )
    
    # Record rate limit (do this early since streaming might disconnect)
    rate_limit_service.record_request(fingerprint, "/submit/stream", "fingerprint")
    
    # Build config for challenge (includes difficulty if provided)
    challenge_config = {}
    if difficulty:
        challenge_config["difficulty"] = difficulty
    
    # Get challenge
    challenge = ChallengeRegistry.get_challenge(challenge_name, challenge_config)
    if not challenge:
        return JSONResponse(
            content={"error": f"Challenge '{challenge_name}' not found"},
            status_code=404
        )
    
    # Check if challenge supports streaming
    if not challenge.supports_streaming:
        return JSONResponse(
            content={"error": f"Streaming not supported for {challenge_name}"},
            status_code=400
        )
    
    challenge_type = challenge.challenge_type
    
    # Guest identities are cookie-owned; caller-supplied usernames are labels only
    # and cannot claim an existing account or another guest's scores.
    from app.routes.runs import player, COOKIE
    from uuid import uuid4
    import jwt
    from datetime import datetime, timedelta, timezone
    owner = player(request, db, current_user)
    guest_token = None
    if owner is None:
        owner = User(username="Guest_" + uuid4().hex[:20], is_active=False)
        db.add(owner)
        db.flush()
        guest_token = jwt.encode({"sub": str(owner.id), "aud": "anonymous-player",
                                  "exp": datetime.now(timezone.utc) + timedelta(days=30)}, config.SECRET_KEY, algorithm="HS256")
        db.commit()
    username, user_id = owner.username, owner.id


    logger.info(f"📥 Challenge submitted: {challenge_name} ({username})")
    
    async def event_generator():
        # Buffer until persistence succeeds: no completion or win animation may
        # escape a transaction that later rolls back.
        events, final_result = [], None
        try:
            async for event in stream_challenge(agent_code, challenge, challenge_type):
                payload = json.loads(event.removeprefix('data: ').strip())
                if payload.get('type') == 'error':
                    raise RuntimeError("Challenge execution failed")
                if payload.get('type') == 'complete':
                    final_result = payload.get('data', payload).get('result')
                events.append(payload)
            if final_result:
                result = ChallengeResult(
                    status=ChallengeStatus(final_result['status']), score=final_result['score'],
                    steps=final_result['steps'], success=final_result['success'], logs=final_result.get('logs', [])
                )
                submission = SubmissionService(db).create_submission(
                    challenge_name, result, agent_code, username, user_id, difficulty
                )
                submission_id = submission.id
                db.commit()
                for event in events:
                    if event.get('type') == 'complete':
                        event.setdefault('data', {}).update(saved=True, submission_id=submission_id)
            for event in events:
                yield f"data: {json.dumps(event)}\n\n"
        except Exception:
            db.rollback()
            logger.exception("Challenge failed before completion could be saved")
            yield 'data: {"type":"error","data":{"message":"The result could not be saved. Please retry."}}\n\n'

    response = StreamingResponse(event_generator(), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
    if guest_token:
        response.set_cookie(COOKIE, guest_token, httponly=True, secure=not config.DEBUG,
                            samesite="lax", max_age=30 * 86400)
    return response
