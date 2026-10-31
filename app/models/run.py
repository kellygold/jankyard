"""Additive recovery schema. Historic leaderboards are deliberately untouched."""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, UniqueConstraint
from app.core.database import Base


class ChallengeRun(Base):
    __tablename__ = "challenge_runs"
    id = Column(String(36), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    challenge = Column(String(50), nullable=False)
    difficulty = Column(String(50), nullable=False)
    rules_version = Column(String(50), nullable=False)
    revision = Column(Integer, nullable=False, default=0)
    status = Column(String(20), nullable=False, default="in_progress")
    state = Column(JSON, nullable=False)
    result = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class RunTurn(Base):
    __tablename__ = "run_turns"
    id = Column(Integer, primary_key=True)
    run_id = Column(String(36), ForeignKey("challenge_runs.id"), nullable=False, index=True)
    request_id = Column(String(36), nullable=False)
    request_hash = Column(String(64), nullable=False)
    receipt = Column(JSON, nullable=False)
    __table_args__ = (UniqueConstraint("run_id", "request_id", name="uq_run_request"),)


class RunScore(Base):
    __tablename__ = "run_scores"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    challenge = Column(String(50), nullable=False)
    difficulty = Column(String(50), nullable=False)
    rules_version = Column(String(50), nullable=False)
    score = Column(Integer, nullable=False)
    steps = Column(Integer, nullable=False)
    submission_id = Column(Integer, ForeignKey("submissions.id"), nullable=False)
    __table_args__ = (UniqueConstraint("user_id", "challenge", "difficulty", "rules_version", name="uq_run_score"),)
