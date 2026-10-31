"""Submission service - refactored to use repositories"""
from typing import Optional, List, Dict
from sqlalchemy.orm import Session

from app.models.submission import Submission
from app.models.user import User
from app.repositories.submission_repo import SubmissionRepository
from app.repositories.user_repo import UserRepository
from app.repositories.leaderboard_repo import LeaderboardRepository
from app.challenges.base import ChallengeResult


class SubmissionService:
    """Service for managing submissions"""
    
    def __init__(self, db: Session):
        self.db = db
        self.submission_repo = SubmissionRepository(db)
        self.user_repo = UserRepository(db)
        self.leaderboard_repo = LeaderboardRepository(db)
    
    def create_submission(
        self,
        challenge_name: str,
        result: ChallengeResult,
        agent_code: str,
        username: Optional[str] = None,
        user_id: Optional[int] = None,
        difficulty: Optional[str] = None
    ) -> Submission:
        """
        Create a new submission and update leaderboard if successful
        
        Args:
            challenge_name: Name of the challenge
            result: Challenge result object
            agent_code: The agent code submitted
            username: Optional username (for anonymous submissions)
            user_id: Optional user ID (for authenticated submissions)
            difficulty: Optional difficulty level (e.g., "GIGA_CHAD", "10x10")
            
        Returns:
            Created Submission object
        """
        # A display name is never proof of account ownership. Callers must resolve
        # the authenticated or cookie-owned player before reaching this service.
        if user_id is None:
            raise ValueError("A verified player is required")
        user = self.db.query(User).filter_by(id=user_id).with_for_update().one()
        status = result.status.value if hasattr(result.status, "value") else result.status
        if status not in {"success", "failure", "error", "timeout"} or result.success != (status == "success"):
            raise ValueError("Inconsistent challenge outcome")
        submission = Submission(
            user_id=user.id, challenge_name=challenge_name, difficulty=difficulty,
            score=result.score, steps=result.steps, success=result.success, status=status,
            logs=result.logs or [], agent_code=agent_code, error_message=result.error_message,
        )
        self.db.add(submission)
        self.db.flush()
        if result.success:
            self._update_leaderboard(challenge_name, user.username, user.id,
                                     result.score, result.steps, submission.id, difficulty)
        self.db.flush()
        # Caller owns the transaction, including rollback on leaderboard failure.
        return submission

    def _update_leaderboard(
        self,
        challenge_name: str,
        username: str,
        user_id: Optional[int],
        score: int,
        steps: int,
        submission_id: int,
        difficulty: Optional[str] = None
    ):
        """Update leaderboard if score is better for this difficulty level"""
        # Get existing entry for this difficulty
        entry = self.leaderboard_repo.get_by_user_challenge_difficulty(username, challenge_name, difficulty)
        
        # Check if this score is better
        is_better = False
        if not entry:
            is_better = True
        elif score > entry.best_score:
            is_better = True
        elif score == entry.best_score and steps < entry.best_steps:
            is_better = True
        
        if is_better:
            self.leaderboard_repo.create_or_update(
                challenge_name=challenge_name,
                username=username,
                user_id=user_id,
                best_score=score,
                best_steps=steps,
                submission_id=submission_id,
                difficulty=difficulty
            )

    
    def get_submission(self, submission_id: int) -> Optional[Submission]:
        """Get a submission by ID"""
        return self.submission_repo.get(submission_id)
    
    def get_recent_submissions(
        self,
        challenge_name: Optional[str] = None,
        limit: int = 50
    ) -> List[Submission]:
        """Get recent submissions, optionally filtered by challenge"""
        if challenge_name:
            return self.submission_repo.get_by_challenge(challenge_name, limit=limit)
        return self.submission_repo.get_recent(limit=limit)
    
    def get_user_submissions(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 50
    ) -> List[Submission]:
        """Get submissions by user"""
        return self.submission_repo.get_by_user(user_id, skip=skip, limit=limit)
    
    def get_user_stats(self, username: str) -> Optional[Dict]:
        """Get statistics for a user"""
        user = self.user_repo.get_by_username(username)
        if not user:
            return None
        
        # Count submissions
        all_submissions = self.submission_repo.get_by_user(user.id, limit=10000)
        total_submissions = len(all_submissions)
        successful_submissions = sum(1 for s in all_submissions if s.success)
        
        # Count leaderboard entries
        leaderboard_entries = self.leaderboard_repo.get_by_user(username)
        challenges_completed = len({entry.challenge_name for entry in leaderboard_entries})
        
        return {
            'username': username,
            'total_submissions': total_submissions,
            'successful_submissions': successful_submissions,
            'challenges_completed': challenges_completed
        }
