"""Leaderboard API endpoints"""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from pathlib import Path

from app.core import get_db
from app.services.leaderboard_service import LeaderboardService
from app.challenges import CHALLENGES
from app.challenges.base import ChallengeRegistry
from app.routes.deps import get_current_user, get_current_user_optional
from app.models.user import User

router = APIRouter(prefix="/leaderboard", tags=["leaderboard"])

# Templates
BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@router.get("", response_class=HTMLResponse)
async def leaderboard_home(request: Request):
    """Leaderboard home page"""
    from app.challenges import ChallengeRegistry
    
    # Get all registered challenges as instances
    all_challenges = ChallengeRegistry.list_challenges()
    # Hide jank_maze from public list
    challenges = [c for c in all_challenges if c['name'] != 'jank_maze']
    
    return templates.TemplateResponse(request,
        "leaderboard_home.html",
        {"request": request, "challenges": challenges}
    )


@router.get("/{challenge_name}", response_class=HTMLResponse)
async def get_leaderboard(
    request: Request,
    challenge_name: str,
    db: Session = Depends(get_db)
):
    """Get leaderboard for a specific challenge"""
    from app.challenges import ChallengeRegistry
    
    leaderboard_service = LeaderboardService(db)
    challenge = ChallengeRegistry.get_challenge(challenge_name)
    
    # Auto-detect difficulties from challenge class (NEW: no manual config!)
    expected_difficulties = []
    if challenge and hasattr(challenge, 'DIFFICULTY_TIERS'):
        # Challenge defines difficulty tiers (e.g., Firewall, Giga Chad)
        expected_difficulties = list(challenge.DIFFICULTY_TIERS.keys())
    elif challenge and hasattr(challenge, 'DIFFICULTIES'):
        # Challenge has a DIFFICULTIES list
        expected_difficulties = challenge.DIFFICULTIES
    
    # Get entries grouped by difficulty
    entries_by_difficulty = leaderboard_service.get_leaderboard_by_difficulties(challenge_name, limit=100)
    
    # Ensure all expected difficulties are present (even if empty)
    for difficulty in expected_difficulties:
        if difficulty not in entries_by_difficulty:
            entries_by_difficulty[difficulty] = []
    
    # Also get flat list for backward compatibility
    entries = leaderboard_service.get_leaderboard(challenge_name, limit=100)
    
    return templates.TemplateResponse(request,
        "leaderboard_detail.html",
        {
            "request": request,
            "challenge_name": challenge_name,
            "challenge": challenge,
            "entries": entries,
            "entries_by_difficulty": entries_by_difficulty,
            "expected_difficulties": expected_difficulties
        }
    )


@router.get("/{challenge_name}/progress", response_class=JSONResponse)
async def get_user_progress(
    request: Request,
    challenge_name: str,
    username: str = None,
    current_user: User = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """Get user's progress for a challenge (unlocked levels).
    
    Supports both authenticated users and anonymous users with username param.
    """
    from app.routes.runs import player
    current_user = player(request, db, current_user)
    # Determine effective username: authenticated/cookie owner takes priority.
    effective_username = None
    if current_user:
        effective_username = current_user.username
    elif username:
        effective_username = username
    
    # No username = no progress, return level 1 only
    if not effective_username:
        return {"unlocked_levels": [1]}
    
    from app.models.leaderboard import LeaderboardEntry
    challenge = ChallengeRegistry.get_challenge(challenge_name)
    if challenge is None:
        return {"unlocked_levels": [1]}
    difficulties = list(getattr(challenge, 'DIFFICULTIES', []) or getattr(challenge, 'DIFFICULTY_TIERS', {}))
    aliases = getattr(challenge, 'DIFFICULTY_ALIASES', {})
    rows = db.query(LeaderboardEntry.difficulty).filter_by(
        challenge_name=challenge_name, username=effective_username
    ).all()
    completed = {aliases.get(row.difficulty, row.difficulty) for row in rows}
    # Preserve historical unlock semantics, without scanning other players' scores.
    return {"unlocked_levels": [1] + [index + 2 for index, difficulty in enumerate(difficulties[:-1])
                                       if difficulty in completed]}
