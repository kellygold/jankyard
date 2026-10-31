"""Submission API endpoints - refactored"""
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, Request, HTTPException, Query
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core import get_db
from app.routes.deps import get_current_user_optional
from app.services.submission_service import SubmissionService
from app.models.user import User

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
async def submit_agent_stream():
    """All public games use the persisted runtime; retire the legacy writer."""
    return JSONResponse(status_code=410, content={
        "error": "Legacy streaming submissions are retired. Reload a challenge page to play."
    })
