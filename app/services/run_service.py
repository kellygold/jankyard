"""One transaction owns a turn, completion, score, and retry receipt.

PostgreSQL row locks serialize turns and scores. Model calls have a bounded timeout;
the caller receives no success until the entire transaction commits.
"""
import hashlib
import json
from fastapi import HTTPException
from sqlalchemy import or_, and_

from app.challenges import ChallengeRegistry
from app.challenges.runtime import PersistedGame, GameAction, ActionError, TurnOutcome
from app.models.run import ChallengeRun, RunTurn, RunScore
from app.models.submission import Submission
from app.models.user import User


def game_definition(name, difficulty=None):
    cls = ChallengeRegistry.get(name)
    if cls is None or not issubclass(cls, PersistedGame):
        raise HTTPException(404, "Challenge is not available in the recovered runtime")
    try:
        return cls({"difficulty": difficulty} if difficulty is not None else {})
    except ValueError:
        raise HTTPException(422, "Unknown difficulty")


class RunService:
    def __init__(self, db):
        self.db = db

    def progress(self, user_id, game):
        scores = self.db.query(RunScore).filter_by(
            user_id=user_id, challenge=game.name, rules_version=game.rules_version
        ).all()
        completed = {s.difficulty for s in scores}
        unlocked = [game.DIFFICULTIES[0]]
        for previous, following in zip(game.DIFFICULTIES, game.DIFFICULTIES[1:]):
            if previous not in completed:
                break
            unlocked.append(following)
        return {"unlocked": unlocked, "completed": sorted(completed)}

    def view(self, run):
        game = game_definition(run.challenge, run.difficulty)
        return {
            "id": run.id, "challenge": run.challenge, "difficulty": run.difficulty,
            "rules_version": run.rules_version, "revision": run.revision,
            "status": run.status, "history": run.state["history"],
            "attempts": run.state["attempts"], "max_attempts": game.max_steps,
            "result": run.result, "progress": self.progress(run.user_id, game),
            "presentation": game.public_state(run.state), "actions": game.actions(run.state),
        }

    def owned(self, run_id, user_id, lock=False):
        query = self.db.query(ChallengeRun).filter_by(id=run_id, user_id=user_id)
        if lock:
            query = query.with_for_update()
        run = query.first()
        if run is None:
            raise HTTPException(404, "Run not found")
        return run

    def lock_player(self, user_id):
        # Consistent lock order across creation and turns; also protects best-score
        # insert/update when one player completes different runs concurrently.
        self.db.query(User).filter_by(id=user_id).with_for_update().one()

    def create(self, run_id, user_id, challenge, difficulty):
        game = game_definition(challenge, difficulty)
        self.lock_player(user_id)
        existing = self.db.query(ChallengeRun).filter_by(id=run_id).first()
        if existing:
            if (existing.user_id, existing.challenge, existing.difficulty) != (user_id, challenge, game.level_id):
                raise HTTPException(409, "Run identifier already used")
            return existing
        if game.level_id not in self.progress(user_id, game)["unlocked"]:
            raise HTTPException(403, "Complete the preceding level first")
        run = ChallengeRun(id=run_id, user_id=user_id, challenge=challenge,
                           difficulty=game.level_id, rules_version=game.rules_version, state=game.initial_state())
        self.db.add(run)
        self.db.flush()
        return run

    def turn(self, run_id, user_id, request_id, revision, prompt):
        self.lock_player(user_id)
        run = self.owned(run_id, user_id, lock=True)
        digest = hashlib.sha256(json.dumps([revision, prompt], sort_keys=True).encode()).hexdigest()
        prior = self.db.query(RunTurn).filter_by(run_id=run_id, request_id=request_id).first()
        if prior:
            if prior.request_hash != digest:
                raise HTTPException(409, "Retry identifier belongs to a different request")
            return prior.receipt
        game = game_definition(run.challenge, run.difficulty)
        if run.rules_version != game.rules_version:
            raise HTTPException(409, "Game rules changed; start a new run")
        if run.status != "in_progress" or run.revision != revision:
            raise HTTPException(409, "Run changed or finished; reload before continuing")
        action = GameAction.model_validate({'text': prompt} if isinstance(prompt, str) else prompt)
        try:
            game.validate_action(run.state, action)
        except ActionError as exc:
            raise HTTPException(422, str(exc))
        if run.state['attempts'] >= game.max_steps:
            raise HTTPException(409, 'Run has no attempts remaining')
        outcome = TurnOutcome.model_validate(game.play(run.state, action)).model_dump()
        if outcome['steps'] != run.state['attempts'] + 1:
            raise ValueError('A turn must consume exactly one attempt')
        run.state = outcome["state"]
        run.status = outcome["status"]
        run.revision += 1
        if run.status != "in_progress":
            submission = Submission(
                user_id=user_id, challenge_name=run.challenge, difficulty=run.difficulty,
                score=outcome["score"], steps=outcome["steps"], success=outcome["success"],
                status=outcome["status"], logs=run.state["history"], agent_code=None,
            )
            self.db.add(submission)
            self.db.flush()
            run.result = {k: outcome[k] for k in ("status", "success", "score", "steps")}
            run.result = dict(run.result, submission_id=submission.id)
            if outcome["success"]:
                self.record_score(run, submission)
        self.db.flush()
        receipt = {"saved": True, "run": self.view(run)}
        self.db.add(RunTurn(run_id=run_id, request_id=request_id, request_hash=digest, receipt=receipt))
        self.db.flush()
        return receipt

    def record_score(self, run, submission):
        query = self.db.query(RunScore).filter_by(
            user_id=run.user_id, challenge=run.challenge, difficulty=run.difficulty,
            rules_version=run.rules_version,
        )
        entry = query.first()
        if entry is None:
            entry = RunScore(user_id=run.user_id, challenge=run.challenge,
                             difficulty=run.difficulty, rules_version=run.rules_version,
                             score=submission.score, steps=submission.steps, submission_id=submission.id)
            self.db.add(entry)
        elif (submission.score, -submission.steps) > (entry.score, -entry.steps):
            entry.score, entry.steps, entry.submission_id = submission.score, submission.steps, submission.id
        self.db.flush()
        rank = 1 + self.db.query(RunScore).filter(
            RunScore.challenge == run.challenge, RunScore.difficulty == run.difficulty,
            RunScore.rules_version == run.rules_version,
            or_(RunScore.score > entry.score, and_(RunScore.score == entry.score, RunScore.steps < entry.steps)),
        ).count()
        run.result = dict(run.result, best_score=entry.score, rank=rank)
