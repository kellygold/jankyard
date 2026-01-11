"""Submission model"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship

from app.core.database import Base


class Submission(Base):
    """Submission model - stores agent submission results"""
    __tablename__ = "submissions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    challenge_name = Column(String(50), nullable=False, index=True)
    difficulty = Column(String(50), nullable=True, index=True)  # e.g., "GIGA_CHAD", "10x10", NULL
    score = Column(Integer, nullable=False)
    steps = Column(Integer, nullable=False)
    success = Column(Boolean, nullable=False)
    status = Column(String(20), nullable=False)  # in_progress, success, failure, timeout, error
    logs = Column(JSON, nullable=True)  # Full execution logs
    agent_code = Column(Text, nullable=True)  # Store agent code for replay
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationships
    user = relationship("User", back_populates="submissions")
    
    def __repr__(self):
        return f"<Submission(id={self.id}, challenge='{self.challenge_name}', score={self.score})>"
