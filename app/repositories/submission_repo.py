"""Submission repository"""
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.submission import Submission
from app.repositories.base import BaseRepository


class SubmissionRepository(BaseRepository[Submission]):
    """Repository for Submission model"""
    
    def __init__(self, db: Session):
        super().__init__(Submission, db)
    
    def get_by_user(self, user_id: int, skip: int = 0, limit: int = 50) -> List[Submission]:
        """Get submissions by user"""
        return (
            self.db.query(Submission)
            .filter(Submission.user_id == user_id)
            .order_by(desc(Submission.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def get_by_challenge(
        self,
        challenge_name: str,
        skip: int = 0,
        limit: int = 50
    ) -> List[Submission]:
        """Get submissions by challenge"""
        return (
            self.db.query(Submission)
            .filter(Submission.challenge_name == challenge_name)
            .order_by(desc(Submission.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def get_successful_by_challenge(
        self,
        challenge_name: str,
        skip: int = 0,
        limit: int = 50
    ) -> List[Submission]:
        """Get successful submissions for a challenge"""
        return (
            self.db.query(Submission)
            .filter(
                Submission.challenge_name == challenge_name,
                Submission.success == True
            )
            .order_by(desc(Submission.score), Submission.steps)
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def get_recent(self, skip: int = 0, limit: int = 50) -> List[Submission]:
        """Get recent submissions"""
        return (
            self.db.query(Submission)
            .order_by(desc(Submission.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def create_submission(
        self,
        challenge_name: str,
        score: int,
        steps: int,
        success: bool,
        status: str,
        user_id: Optional[int] = None,
        logs: Optional[dict] = None,
        agent_code: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> Submission:
        """Create a new submission"""
        return self.create(
            user_id=user_id,
            challenge_name=challenge_name,
            score=score,
            steps=steps,
            success=success,
            status=status,
            logs=logs,
            agent_code=agent_code,
            error_message=error_message
        )
