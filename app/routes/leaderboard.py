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
    
    return templates.TemplateResponse(
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
    
    return templates.TemplateResponse(
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
    challenge_name: str,
    username: str = None,
    current_user: User = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """Get user's progress for a challenge (unlocked levels).
    
    Supports both authenticated users and anonymous users with username param.
    """
    # Determine effective username: authenticated user takes priority, then query param
    effective_username = None
    if current_user:
        effective_username = current_user.username
    elif username:
        effective_username = username
    
    # No username = no progress, return level 1 only
    if not effective_username:
        return {"unlocked_levels": [1]}
    
    leaderboard_service = LeaderboardService(db)
    
    # For Giga Chad (4 difficulties: BABY_CHAD, CHAD, MEGA_CHAD, GIGA_CHAD)
    if challenge_name == "giga_chad":
        unlocked_levels = [1]  # Always have level 1 (BABY_CHAD)
        
        # Get all difficulties leaderboard
        leaderboards = leaderboard_service.get_leaderboard_by_difficulties(
            challenge_name, limit=1000
        )
        
        # Check BABY_CHAD (level 1) - unlocks CHAD (level 2)
        if any(entry.username == effective_username for entry in leaderboards.get("BABY_CHAD", [])):
            unlocked_levels.append(2)
        
        # Check CHAD (level 2) - unlocks MEGA_CHAD (level 3)
        if any(entry.username == effective_username for entry in leaderboards.get("CHAD", [])):
            unlocked_levels.append(3)
        
        # Check MEGA_CHAD (level 3) - unlocks GIGA_CHAD (level 4)
        if any(entry.username == effective_username for entry in leaderboards.get("MEGA_CHAD", [])):
            unlocked_levels.append(4)
        
        return {"unlocked_levels": unlocked_levels}
    
    # For progressive challenges (Glitch, Interrogation), check which levels are beaten
    if challenge_name in ["glitch", "interrogation"]:
        unlocked_levels = [1]  # Always have level 1
        
        # Check level 1
        level1_entries = leaderboard_service.get_leaderboard_by_difficulties(
            challenge_name, limit=1000
        ).get("level_1", [])
        
        if any(entry.username == effective_username for entry in level1_entries):
            unlocked_levels.append(2)
        
        # Check level 2
        level2_entries = leaderboard_service.get_leaderboard_by_difficulties(
            challenge_name, limit=1000
        ).get("level_2", [])
        
        if any(entry.username == effective_username for entry in level2_entries):
            unlocked_levels.append(3)
        
        return {"unlocked_levels": unlocked_levels}
    
    # For Firewall (3 levels: LEVEL_1, LEVEL_2, LEVEL_3)
    if challenge_name == "firewall":
        unlocked_levels = [1]  # Always have level 1
        
        # Get all difficulties leaderboard
        leaderboards = leaderboard_service.get_leaderboard_by_difficulties(
            challenge_name, limit=1000
        )
        
        # Check LEVEL_1 (level 1) - unlocks LEVEL_2
        if any(entry.username == effective_username for entry in leaderboards.get("LEVEL_1", [])):
            unlocked_levels.append(2)
        
        # Check LEVEL_2 (level 2) - unlocks LEVEL_3
        if any(entry.username == effective_username for entry in leaderboards.get("LEVEL_2", [])):
            unlocked_levels.append(3)
        
        return {"unlocked_levels": unlocked_levels}
    
    # For Debate and Arena (2 levels: easy, hard)
    if challenge_name in ["debate_battle", "arena"]:
        unlocked_levels = [1]  # Always have level 1
        
        # Get all difficulties leaderboard
        leaderboards = leaderboard_service.get_leaderboard_by_difficulties(
            challenge_name, limit=1000
        )
        
        # Check easy (level 1) - unlocks hard (level 2)
        # Also check 'normal' for backward compatibility
        if any(entry.username == effective_username for entry in leaderboards.get("easy", [])) or \
           any(entry.username == effective_username for entry in leaderboards.get("normal", [])):
            unlocked_levels.append(2)
        
        return {"unlocked_levels": unlocked_levels}
    
    # Generic: Auto-detect from challenge DIFFICULTIES (NEW!)
    challenge = ChallengeRegistry.get_challenge(challenge_name)
    if challenge and hasattr(challenge, 'DIFFICULTIES'):
        unlocked_levels = [1]  # Always have level 1
        
        # Get all difficulties leaderboard
        leaderboards = leaderboard_service.get_leaderboard_by_difficulties(
            challenge_name, limit=1000
        )
        
        # Check each difficulty in order to unlock next
        for i, difficulty in enumerate(challenge.DIFFICULTIES[:-1], start=1):
            if any(entry.username == effective_username for entry in leaderboards.get(difficulty, [])):
                unlocked_levels.append(i + 1)
        
        return {"unlocked_levels": unlocked_levels}
    
    # Default for other challenges
    return {"unlocked_levels": [1]}
