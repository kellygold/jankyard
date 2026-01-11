"""Submission API endpoints - refactored"""
import json
import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, Form, UploadFile, File, Request
from fastapi.responses import StreamingResponse, JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.core import get_db
from app.core.config import config
from app.routes.deps import get_current_user_optional
from app.services.submission_service import SubmissionService
from app.services.challenge_service import ChallengeService
from app.services.rate_limit_service import RateLimitService
from app.models.user import User
from app.sandbox.runner import SandboxRunner
from app.sandbox.prompt_runner import PromptRunner
from app.utils.generic_stream import stream_challenge
from app.utils.validation import validate_and_sanitize_username
from app.utils.fingerprint import generate_fingerprint
from app.utils.name_generator import generate_anonymous_username
from app.challenges import ChallengeRegistry
from app.challenges.base import ChallengeResult, ChallengeStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="", tags=["submissions"])

# Initialize runners
sandbox = SandboxRunner()
prompt_runner = PromptRunner()


@router.post("/submit")
async def submit_agent(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    """Submit an agent for a challenge"""
    
    # Parse form data (multipart works best for code with special chars)
    try:
        form = await request.form()
        challenge_name = form.get('challenge_name')
        username = form.get('username')
        agent_type = form.get('agent_type', 'code')
        agent_code = form.get('agent_code')
        difficulty = form.get('difficulty')
        agent_file = form.get('agent_file')
    except Exception as e:
        logger.error(f"❌ Failed to parse form data: {e}")
        return JSONResponse(
            content={"error": f"Failed to parse request: {str(e)}"},
            status_code=400
        )
    
    logger.info(f"📥 Challenge submitted: {challenge_name} (difficulty: {difficulty})")
    
    # Generate user fingerprint for rate limiting (IP + User-Agent hash)
    fingerprint = generate_fingerprint(request)
    
    # Check rate limit
    rate_limit_service = RateLimitService(db)
    rate_limit_service.check_rate_limit(fingerprint, "/submit", "fingerprint")
    
    # Get challenge with difficulty config
    challenge_service = ChallengeService(db)
    challenge_config = {'difficulty': difficulty} if difficulty else {}
    challenge = challenge_service.get_challenge(challenge_name, challenge_config)
    
    # Get agent code
    if agent_file and hasattr(agent_file, 'filename') and agent_file.filename:
        code = (await agent_file.read()).decode('utf-8')
        if len(code) > config.MAX_UPLOAD_SIZE:
            return JSONResponse(content={"error": "File too large"}, status_code=400)
    else:
        code = agent_code
    
    if not code:
        return {"error": "No agent code provided"}
    
    # Determine username for logging and saving
    if current_user:
        effective_username = current_user.username
        user_id = current_user.id
    elif username:
        # Validate user-provided username
        sanitized_username, validation_error = validate_and_sanitize_username(username)
        if validation_error:
            return JSONResponse(
                content={"error": f"Invalid username: {validation_error}"},
                status_code=400
            )
        effective_username = sanitized_username or generate_anonymous_username()
        user_id = None
    else:
        # Generate fun anonymous name like "GoofyPanther420"
        effective_username = generate_anonymous_username()
        user_id = None
    
    # Run challenge
    logger.info(f"🎯 Running: {challenge_name} ({effective_username})")
    
    try:
        if agent_type == "prompt":
            result = prompt_runner.run_challenge(code, challenge)
        else:
            result = sandbox.run_challenge(code, challenge)
        
        logger.info(f"✅ Completed: {result.status.value} | Score: {result.score}")
    except Exception as e:
        logger.error(f"❌ CRITICAL ERROR in challenge execution: {e}", exc_info=True)
        return JSONResponse(
            content={"error": f"Challenge execution failed: {str(e)}"},
            status_code=500
        )
    
    # Close existing session to release DB locks
    try:
        db.close()
    except Exception:
        pass  # Session may already be closed
    
    # Save submission
    submission_service = SubmissionService(db)
    try:
        # Run blocking psycopg2 calls in thread pool to avoid blocking event loop
        submission = await run_in_threadpool(
            submission_service.create_submission,
            challenge_name=challenge_name,
            result=result,
            agent_code=None,  # Don't save code - not needed and causes issues
            username=effective_username,
            user_id=user_id,  # Now we already have it!
            difficulty=difficulty
        )
        submission_id = getattr(submission, 'id', None) or 0
        logger.info(f"💾 Saved: ID {submission_id}")
    except Exception as e:
        logger.error(f"❌ DATABASE SAVE FAILED: {e}", exc_info=True)
        db.rollback()
        # Return success anyway - submission ran even if we couldn't save it
        return JSONResponse(
            content={
                "submission_id": 0,
                "status": result.status.value,
                "score": result.score,
                "steps": result.steps,
                "success": result.success,
                "logs": [],
                "error_message": f"Challenge completed but failed to save: {str(e)}"
            }
        )
    
    # Record rate limit
    rate_limit_service.record_request(fingerprint, "/submit", "fingerprint")
    
    # Build safe JSON response
    minimal_response = {
        "submission_id": submission_id,
        "status": "error",
        "score": 0,
        "steps": 0,
        "success": False,
        "logs": [],
        "error_message": "Failed to build response"
    }
    
    try:
        # Build full response
        minimal_response["status"] = result.status.value
        minimal_response["score"] = result.score if result.score is not None else 0
        minimal_response["steps"] = result.steps if result.steps is not None else 0
        minimal_response["success"] = bool(result.success)
        minimal_response["error_message"] = str(result.error_message) if result.error_message else ""
        
        # Add logs WITH render field for maze visualization
        if result.logs:
            for log in result.logs[:10]:  # First 10 steps only
                try:
                    safe_log = {
                        "step": int(log.get("step", 0)),
                        "action": str(log.get("action", ""))[:50],
                        "reward": float(log.get("reward", 0)) if log.get("reward") is not None else 0
                    }
                    # Include render if present (for maze visualization)
                    if "render" in log:
                        safe_log["render"] = str(log.get("render", ""))
                    minimal_response["logs"].append(safe_log)
                except (TypeError, ValueError, KeyError):
                    pass  # Skip malformed log entries
        
        return JSONResponse(content=minimal_response)
        
    except Exception as e:
        logger.error(f"❌ Failed to build response: {e}", exc_info=True)
        minimal_response["error_message"] = f"Response build failed: {str(e)}"
        return JSONResponse(content=minimal_response, status_code=500)


@router.get("/submission/{submission_id}", response_class=HTMLResponse)
async def get_submission(
    request: Request,
    submission_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific submission"""
    submission_service = SubmissionService(db)
    submission = submission_service.get_submission(submission_id)
    
    if not submission:
        return {"error": "Submission not found"}
    
    # Render template instead of JSON
    BASE_DIR = Path(__file__).resolve().parent.parent
    templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
    
    return templates.TemplateResponse(
        "submission_detail.html",
        {"request": request, "submission": submission}
    )


@router.get("/recent")
async def get_recent_submissions(
    challenge_name: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Get recent submissions"""
    submission_service = SubmissionService(db)
    submissions = submission_service.get_recent_submissions(challenge_name, limit)
    return submissions


@router.api_route("/submit/stream", methods=["GET", "POST"])
async def submit_agent_stream(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    """
    Submit an agent and stream challenge progress in real-time (SSE)
    Supports: debate_battle, giga_chad (all difficulties)
    """
    # Extract data from either query params (GET) or form data (POST)
    if request.method == "POST":
        form = await request.form()
        challenge_name = form.get("challenge_name")
        agent_code = form.get("agent_code")
        difficulty = form.get("difficulty")
        username = form.get("username")
    else:
        challenge_name = request.query_params.get("challenge_name")
        agent_code = request.query_params.get("agent_code")
        difficulty = request.query_params.get("difficulty")
        username = request.query_params.get("username")
    
    # Use logged-in user's username if available
    if current_user:
        username = current_user.username
    elif username:
        # Validate user-provided username
        sanitized_username, validation_error = validate_and_sanitize_username(username)
        if validation_error:
            return JSONResponse(
                content={"error": f"Invalid username: {validation_error}"},
                status_code=400
            )
        username = sanitized_username or generate_anonymous_username()
    else:
        # Generate fun anonymous username if none provided
        username = generate_anonymous_username()
    
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
    
    logger.info(f"📥 Challenge submitted: {challenge_name} ({username})")
    
    async def event_generator():
        """Generate SSE events"""
        final_result = None
        try:
            async for event in stream_challenge(agent_code, challenge, challenge_type):
                # Capture final result for DB save
                if '"type": "complete"' in event:
                    event_data = json.loads(event.replace('data: ', ''))
                    # Result is nested under 'data' key in standardized event format
                    final_result = event_data.get('data', {}).get('result')
                yield event
        except Exception as e:
            yield f"data: {{'error': '{str(e)}'}}\n\n"
        finally:
            # Save to DB after streaming completes
            logger.info(f"🔍 Stream ended - final_result: {bool(final_result)}, username: {username}")
            
            if final_result and username:
                try:
                    submission_service = SubmissionService(db)
                    
                    # Reconstruct ChallengeResult from streamed data
                    result = ChallengeResult(
                        status=ChallengeStatus(final_result['status']),
                        score=final_result['score'],
                        steps=final_result['steps'],
                        success=final_result['success'],
                        logs=final_result['logs']
                    )
                    
                    logger.info(f"💾 Saving submission: {challenge_name} - {username} - {result.score}pts (success={result.success})")
                    
                    # Save submission (this updates leaderboard too)
                    submission = submission_service.create_submission(
                        challenge_name=challenge_name,
                        result=result,
                        agent_code=agent_code,
                        username=username,
                        user_id=current_user.id if current_user else None,
                        difficulty=difficulty
                    )
                    
                    if result.success:
                        logger.info(f"✅ Score recorded: {username} - {result.score}pts")
                except Exception as e:
                    logger.error(f"❌ Failed to save submission: {e}", exc_info=True)
            elif not final_result:
                logger.warning("⚠️  No final result captured - submission not saved")
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
