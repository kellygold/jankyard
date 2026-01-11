"""Leaderboard model"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from app.core.database import Base


class LeaderboardEntry(Base):
    """Leaderboard model - stores best scores per user per challenge per difficulty"""
    __tablename__ = "leaderboard"
    
    id = Column(Integer, primary_key=True, index=True)
    challenge_name = Column(String(50), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    username = Column(String(50), nullable=False)  # Denormalized for easier queries
    difficulty = Column(String(50), nullable=True, index=True)  # e.g., "GIGA_CHAD", "10x10", NULL for no difficulty
    best_score = Column(Integer, nullable=False)
    best_steps = Column(Integer, nullable=False)
    submission_id = Column(Integer, ForeignKey("submissions.id"), nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Unique constraint: one entry per user per challenge per difficulty
    __table_args__ = (
        UniqueConstraint('challenge_name', 'username', 'difficulty', name='uix_leaderboard_challenge_user_difficulty'),
    )
    
    # Relationships
    user = relationship("User", back_populates="leaderboard_entries")
    submission = relationship("Submission")
    
    def __repr__(self):
        diff_str = f", difficulty='{self.difficulty}'" if self.difficulty else ""
        return f"<LeaderboardEntry(challenge='{self.challenge_name}', user='{self.username}'{diff_str}, score={self.best_score})>"
