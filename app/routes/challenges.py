"""Challenge API endpoints"""
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from sqlalchemy.orm import Session
import os

from app.challenges import ChallengeRegistry  # Import from challenges module, not base
from app.core import get_db
from app.routes.deps import get_current_user_optional
from app.models.user import User
from app.challenges.runtime import PersistedGame

router = APIRouter(prefix="/challenges", tags=["challenges"])

# Templates
BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

def get_challenge_template(challenge_name: str) -> str:
    """
    Auto-discover challenge template by convention.
    
    Convention: challenges/{challenge_name}.html
    
    Falls back to manual template_map for backward compatibility,
    then to base_challenge.html as last resort.
    
    Args:
        challenge_name: Name of the challenge (e.g., 'firewall', 'debate_battle')
        
    Returns:
        Template path relative to templates directory
    """
    # Try convention first: challenges/{name}.html
    convention_template = f"challenges/{challenge_name}.html"
    template_path = BASE_DIR / "templates" / convention_template
    
    if template_path.exists():
        return convention_template
    
    # Fallback to manual mapping (backward compatibility during migration)
    template_map = {
        "debate_battle": "challenges/debate.html",
        "giga_chad": "challenges/giga_chad.html",
        "firewall": "challenges/firewall.html",
        "arena": "challenges/arena.html",
        "glitch": "challenges/glitch.html",
        "interrogation": "challenges/interrogation.html",
        "jank_maze": "challenges/jank_maze.html"
    }
    
    if challenge_name in template_map:
        return template_map[challenge_name]
    
    # Last resort: base challenge template
    return "challenges/base_challenge.html"


@router.get("", response_class=HTMLResponse)
async def list_challenges(request: Request):
    """List all available challenges"""
    all_challenges = ChallengeRegistry.list_challenges()
    # Hide jank_maze from public list
    challenges = [c for c in all_challenges if c['name'] != 'jank_maze']
    return templates.TemplateResponse(request,
        "challenges.html",
        {"request": request, "challenges": challenges}
    )


@router.get("/{challenge_name}", response_class=HTMLResponse)
async def get_challenge_detail(
    request: Request,
    challenge_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    """Get challenge details page"""
    try:
        challenge = ChallengeRegistry.get_challenge(challenge_name)
        if not challenge:
            return templates.TemplateResponse(request,
                "error.html",
                {"request": request, "error": f"Challenge '{challenge_name}' not found"}, status_code=404
            )
        
        # Auto-discover template by convention (NEW: contributors don't need to edit this!)
        template = "challenges/prompt_game.html" if isinstance(challenge, PersistedGame) else get_challenge_template(challenge_name)
        
        # Prepare challenge-specific context
        context = {
            "request": request,
            "challenge": challenge,
            "challenge_name": challenge_name,
            "current_user": current_user
        }
        
        # Add debate topic for debate challenges
        if challenge_name == "debate_battle":
            from app.challenges.debate_battle import DEBATE_TOPICS
            topic = DEBATE_TOPICS[0]  # Pineapple pizza
            # Add your_position to the topic context
            context["debate_topic"] = {
                "topic": topic.topic,
                "your_position": "PRO",
                "description": topic.pro_description,
                "rounds": topic.rounds
            }
        
        # Add template code for jank_maze
        if challenge_name == "jank_maze":
            template_code = """def act(observation, memory):
    # random is already available - no need to import!
    
    # Get visible cells (what's around us)
    visible = observation.get('visible_cells', {})
    
    # Build list of valid moves (not walls)
    valid_moves = []
    if visible.get('north') != '#':
        valid_moves.append('MOVE_N')
    if visible.get('south') != '#':
        valid_moves.append('MOVE_S')
    if visible.get('east') != '#':
        valid_moves.append('MOVE_E')
    if visible.get('west') != '#':
        valid_moves.append('MOVE_W')
    
    # Pick a random valid move (or WAIT if stuck)
    if valid_moves:
        action = random.choice(valid_moves)
    else:
        action = 'WAIT'
    
    return action, memory"""
            context["template_code"] = template_code
        
        # Check unlocked levels for progressive challenges (AUTO-DETECT!)
        if current_user and challenge and hasattr(challenge, 'DIFFICULTIES'):
            # Generic progress tracking for any challenge with DIFFICULTIES
            from app.repositories.leaderboard_repo import LeaderboardRepository
            leaderboard_repo = LeaderboardRepository(db)
            
            unlocked_levels = [1]  # Always start with level 1
            
            # Check each difficulty in order
            for i, difficulty in enumerate(challenge.DIFFICULTIES[:-1], start=1):
                entry = leaderboard_repo.get_by_user_challenge_difficulty(
                    current_user.username,
                    challenge_name,
                    difficulty
                )
                if entry and entry.best_score > 0:
                    unlocked_levels.append(i + 1)
            
            context["unlocked_levels"] = unlocked_levels
        else:
            context["unlocked_levels"] = [1]  # Default for non-logged-in users or no difficulties
        
        return templates.TemplateResponse(request, template, context)
    except Exception as e:
        return templates.TemplateResponse(request,
            "error.html",
            {"request": request, "error": str(e)}
        )
