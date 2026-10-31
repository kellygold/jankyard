"""Persisted prompt games. JSON POSTs, opaque run IDs, authenticated ownership."""
from datetime import datetime, timedelta, timezone
import logging
from uuid import UUID, uuid4
import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field, model_validator
from app.challenges.runtime import GameAction
from sqlalchemy.orm import Session
from sqlalchemy import text
import hashlib
import math
from app.core.exceptions import RateLimitExceededError

from app.core import get_db
from app.core.config import config
from app.models.user import User
from app.models.run import ChallengeRun, RunScore
from app.routes.deps import get_current_user_optional
from app.services.run_service import RunService, game_definition
from app.services.rate_limit_service import RateLimitService
from app.utils.fingerprint import generate_fingerprint

router = APIRouter(prefix="/api", tags=["runs"])
logger = logging.getLogger(__name__)
COOKIE = "jankyard_player"


def player(request: Request, db: Session, current_user=None):
    if current_user:
        return current_user
    token = request.cookies.get(COOKIE)
    if not token:
        return None
    try:
        claims = jwt.decode(token, config.SECRET_KEY, algorithms=["HS256"], audience="anonymous-player")
        user_id = int(claims["sub"])
    except (jwt.InvalidTokenError, ValueError, KeyError):
        return None
    # A guest cookie can never authenticate a registered account.
    return db.query(User).filter_by(id=user_id, hashed_password=None).first()


def require_player(request: Request, db=Depends(get_db), current_user=Depends(get_current_user_optional)):
    user = player(request, db, current_user)
    if user is None:
        raise HTTPException(401, "Start a run to establish a player session")
    return user


class CreateRun(BaseModel):
    request_id: UUID
    challenge: str = Field(min_length=1, max_length=50)
    difficulty: str = Field(min_length=1, max_length=50)


class SubmitTurn(BaseModel):
    request_id: UUID
    revision: int = Field(ge=0)
    prompt: str | None = Field(default=None, min_length=1, max_length=8000)
    action: GameAction | None = None

    @model_validator(mode='after')
    def one_action(self):
        if (self.prompt is None) == (self.action is None):
            raise ValueError('Provide either prompt or action')
        return self


def rate_limit(request, db, user_id=None, model_request=False):
    if not config.RATE_LIMIT_ENABLED:
        return
    # Gameplay budgets belong to verified players, independent of the hosting
    # proxy address. Provisioning guests has a separate, larger peer budget.
    bootstrap = user_id is None
    key = f"guest-peer:{request.client.host if request.client else 'unknown'}" if bootstrap else f"player:{user_id}"
    identifier = hashlib.sha256(key.encode()).hexdigest()
    endpoint = "/api/guest-sessions" if bootstrap else "/api/runs"
    if db.bind.dialect.name == "postgresql":
        db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": int(identifier[:15], 16)})
    limits = RateLimitService(db)
    windows = [("minute", config.GUEST_SESSIONS_PER_MINUTE if bootstrap else config.SUBMISSIONS_PER_MINUTE),
               ("day", config.GUEST_SESSIONS_PER_DAY if bootstrap else config.SUBMISSIONS_PER_DAY)]
    for window, limit in windows:
        used = limits.rate_limit_repo.get_usage_count(identifier, endpoint, window, limits._get_window_start(window))
        if used >= limit:
            db.rollback()
            raise HTTPException(429, "Request budget reached. Your saved progress is safe.",
                                headers={"Retry-After": str(retry_after(limits, window))})
    limits.record_request(identifier, endpoint, "ip" if bootstrap else "user")
    if model_request:
        # A separate site-wide admission ceiling bounds paid recovered turns even
        # when a caller rotates guest sessions. Reservations survive turn failure;
        # retries conservatively consume budget too. No game state exists here yet.
        if db.bind.dialect.name == "postgresql":
            db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": 892174630112})
        window = limits._get_window_start("day")
        used = limits.rate_limit_repo.get_usage_count("global", "/api/recovered-turns", "day", window)
        if used >= config.RECOVERED_TURNS_PER_DAY:
            db.rollback()
            raise HTTPException(429, "The playground's daily model budget has been reached. Please try again tomorrow.",
                                headers={"Retry-After": str(retry_after(limits, 'day'))})
        limits.rate_limit_repo.increment_or_create(identifier="global", identifier_type="global", endpoint="/api/recovered-turns", window_type="day", window_start=window)
        db.commit()


def retry_after(limits, window):
    start = limits._get_window_start(window)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    end = start.replace(tzinfo=None) + (timedelta(minutes=1) if window == 'minute' else timedelta(days=1))
    return max(1, math.ceil((end - now).total_seconds()))


@router.get("/games/{name}")
def get_game(name: str):
    game = game_definition(name)
    levels = []
    for level in game.public_levels():
        selected = game_definition(name, level['id'])
        levels.append(dict(level, actions=selected.actions(selected.initial_state()),
                           presentation=selected.public_state(selected.initial_state())))
    return {"name": game.name, "title": game.display_name, "description": game.description,
            "version": game.rules_version, "levels": levels}


@router.get("/games/{name}/progress")
def get_progress(name: str, request: Request, db=Depends(get_db), current_user=Depends(get_current_user_optional)):
    game = game_definition(name)
    user = player(request, db, current_user)
    service = RunService(db)
    latest = None
    if user:
        latest = db.query(ChallengeRun).filter_by(user_id=user.id, challenge=name, rules_version=game.rules_version).order_by(ChallengeRun.created_at.desc(), ChallengeRun.id).first()
    return {"username": user.username if user else None,
            "progress": service.progress(user.id if user else -1, game),
            "latest_run": service.view(latest) if latest else None}


@router.get("/games/{name}/leaderboard")
def get_scores(name: str, difficulty: str, db=Depends(get_db)):
    game = game_definition(name, difficulty)
    rows = db.query(RunScore, User.username).join(User, User.id == RunScore.user_id).filter(
        RunScore.challenge == name, RunScore.difficulty == game.level_id, RunScore.rules_version == game.rules_version
    ).order_by(RunScore.score.desc(), RunScore.steps, RunScore.id).limit(100).all()
    entries, previous, rank = [], None, 0
    for index, (score, username) in enumerate(rows, 1):
        if previous != (score.score, score.steps):
            rank = index
        previous = (score.score, score.steps)
        entries.append({"rank": rank, "username": username, "score": score.score, "steps": score.steps})
    return {"version": game.rules_version, "entries": entries}


@router.post("/runs")
def create_run(body: CreateRun, request: Request, response: Response, db=Depends(get_db), current_user=Depends(get_current_user_optional)):
    game_definition(body.challenge, body.difficulty)
    user = player(request, db, current_user)
    rate_limit(request, db, user.id if user else None)
    guest_token = None
    try:
        if user is None:
            user = User(username="Guest_" + uuid4().hex[:20], is_active=False)
            db.add(user)
            db.flush()
            guest_token = jwt.encode({"sub": str(user.id), "aud": "anonymous-player",
                                      "exp": datetime.now(timezone.utc) + timedelta(days=30)}, config.SECRET_KEY, algorithm="HS256")
        service = RunService(db)
        run = service.create(str(body.request_id), user.id, body.challenge, body.difficulty)
        receipt = {"saved": True, "username": user.username, "run": service.view(run)}
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        logger.exception("Run creation failed")
        raise HTTPException(503, "Could not save the run. Please retry.")
    if guest_token:
        response.set_cookie(COOKIE, guest_token, httponly=True, secure=not config.DEBUG, samesite="lax", max_age=30 * 86400)
    return receipt


@router.get("/runs/{run_id}")
def get_run(run_id: UUID, db=Depends(get_db), user=Depends(require_player)):
    service = RunService(db)
    return service.view(service.owned(str(run_id), user.id))


@router.post("/runs/{run_id}/turns")
def submit_turn(run_id: UUID, body: SubmitTurn, request: Request, db=Depends(get_db), user=Depends(require_player)):
    if body.prompt is not None and not body.prompt.strip():
        raise HTTPException(422, "Enter a prompt")
    rate_limit(request, db, user.id, model_request=True)
    try:
        receipt = RunService(db).turn(str(run_id), user.id, str(body.request_id), body.revision, body.prompt if body.prompt is not None else body.action.model_dump())
        db.commit()
        return receipt
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        logger.exception("Turn failed; no outcome committed")
        raise HTTPException(503, "Turn was not saved. Retry the same prompt; saved attempts will not be counted twice.")
