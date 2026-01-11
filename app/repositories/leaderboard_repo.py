"""Leaderboard repository"""
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.leaderboard import LeaderboardEntry
from app.repositories.base import BaseRepository


class LeaderboardRepository(BaseRepository[LeaderboardEntry]):
    """Repository for LeaderboardEntry model"""
    
    def __init__(self, db: Session):
        super().__init__(LeaderboardEntry, db)
    
    def get_by_challenge(
        self,
        challenge_name: str,
        difficulty: Optional[str] = None,
        limit: int = 100
    ) -> List[LeaderboardEntry]:
        """Get leaderboard entries for a challenge (optionally filtered by difficulty)"""
        query = self.db.query(LeaderboardEntry).filter(
            LeaderboardEntry.challenge_name == challenge_name
        )
        
        if difficulty is not None:
            query = query.filter(LeaderboardEntry.difficulty == difficulty)
        
        return (
            query
            .order_by(desc(LeaderboardEntry.best_score), LeaderboardEntry.best_steps)
            .limit(limit)
            .all()
        )
    
    def get_by_user_and_challenge(
        self,
        username: str,
        challenge_name: str
    ) -> Optional[LeaderboardEntry]:
        """Get leaderboard entry for a specific user and challenge (legacy - doesn't filter by difficulty)"""
        return (
            self.db.query(LeaderboardEntry)
            .filter(
                LeaderboardEntry.username == username,
                LeaderboardEntry.challenge_name == challenge_name
            )
            .first()
        )
    
    def get_by_user_challenge_difficulty(
        self,
        username: str,
        challenge_name: str,
        difficulty: Optional[str] = None
    ) -> Optional[LeaderboardEntry]:
        """Get leaderboard entry for a specific user, challenge, and difficulty"""
        query = self.db.query(LeaderboardEntry).filter(
            LeaderboardEntry.username == username,
            LeaderboardEntry.challenge_name == challenge_name
        )
        
        # Handle NULL difficulty properly
        if difficulty is None:
            query = query.filter(LeaderboardEntry.difficulty.is_(None))
        else:
            query = query.filter(LeaderboardEntry.difficulty == difficulty)
        
        return query.first()
    
    def get_by_user(self, username: str) -> List[LeaderboardEntry]:
        """Get all leaderboard entries for a user"""
        return (
            self.db.query(LeaderboardEntry)
            .filter(LeaderboardEntry.username == username)
            .order_by(desc(LeaderboardEntry.best_score))
            .all()
        )
    
    def create_or_update(
        self,
        challenge_name: str,
        username: str,
        user_id: Optional[int],
        best_score: int,
        best_steps: int,
        submission_id: int,
        difficulty: Optional[str] = None
    ) -> LeaderboardEntry:
        """Create or update a leaderboard entry for specific difficulty"""
        entry = self.get_by_user_challenge_difficulty(username, challenge_name, difficulty)
        
        if entry:
            # Update existing entry
            return self.update(
                entry,
                best_score=best_score,
                best_steps=best_steps,
                submission_id=submission_id
            )
        else:
            # Create new entry
            return self.create(
                challenge_name=challenge_name,
                username=username,
                user_id=user_id,
                best_score=best_score,
                best_steps=best_steps,
                submission_id=submission_id,
                difficulty=difficulty
            )
