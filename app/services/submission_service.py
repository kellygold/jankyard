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
        import logging
        logger = logging.getLogger(__name__)
        
        # Get or create user with psycopg2 if needed
        if not user_id and username:
            import psycopg2
            import os
            try:
                conn = psycopg2.connect(os.getenv('DATABASE_URL'))
                conn.autocommit = True
                cursor = conn.cursor()
                
                # Try to get existing user
                cursor.execute("SELECT id FROM users WHERE username = %s LIMIT 1", (username,))
                row = cursor.fetchone()
                
                if row:
                    user_id = row[0]
                else:
                    # Create new user
                    from datetime import datetime
                    cursor.execute("""
                        INSERT INTO users (username, email, hashed_password, is_active, created_at)
                        VALUES (%s, %s, %s, %s, %s)
                        RETURNING id
                    """, (username, None, None, False, datetime.utcnow()))
                    user_id = cursor.fetchone()[0]
                    logger.info(f"👤 Created user: {username}")
                
                cursor.close()
                conn.close()
            except Exception as e:
                logger.error(f"❌ Failed to get/create user: {e}")
                user_id = None
        
        # Sanitize logs for JSON serialization
        safe_logs = []
        if result.logs:
            for log in result.logs:
                try:
                    # Convert to JSON-safe dict
                    safe_log = {}
                    for key, value in log.items():
                        # Convert non-JSON types to strings
                        if isinstance(value, (str, int, float, bool, type(None))):
                            safe_log[key] = value
                        else:
                            safe_log[key] = str(value)  # Convert sets, tuples, etc. to strings
                    safe_logs.append(safe_log)
                except (TypeError, ValueError, KeyError) as e:
                    pass  # Skip problematic logs - expected for malformed data
        
        # Insert submission with raw SQL
        import json
        from datetime import datetime
        
        try:
            # Use psycopg2 directly - bypass SQLAlchemy session issues
            import psycopg2
            import os
            
            conn = psycopg2.connect(os.getenv('DATABASE_URL'))
            conn.autocommit = True
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO submissions 
                (user_id, challenge_name, difficulty, score, steps, success, status, logs, agent_code, error_message, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                user_id,
                challenge_name,
                difficulty,
                result.score,
                result.steps,
                result.success,
                result.status.value,
                json.dumps(safe_logs),
                agent_code,
                result.error_message,
                datetime.utcnow()
            ))
            
            submission_id = cursor.fetchone()[0]
            cursor.close()
            conn.close()
            
            # Create a mock submission object with the ID
            from app.models.submission import Submission
            submission = Submission(id=submission_id)
        except Exception as e:
            logger.error(f"❌ Submission insert failed: {e}", exc_info=True)
            # Create dummy submission
            submission = type('obj', (object,), {'id': 0})()
        
        # Update leaderboard if successful
        if result.success and username:
            self._update_leaderboard(
                challenge_name=challenge_name,
                username=username,
                user_id=user_id,
                score=result.score,
                steps=result.steps,
                submission_id=submission.id,
                difficulty=difficulty
            )
        
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
            self.leaderboard_repo.commit()
    
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
        challenges_completed = len(leaderboard_entries)
        
        return {
            'username': username,
            'total_submissions': total_submissions,
            'successful_submissions': successful_submissions,
            'challenges_completed': challenges_completed
        }
