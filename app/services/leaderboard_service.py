"""Leaderboard service"""
from typing import List, Optional, Dict
from sqlalchemy.orm import Session
from collections import defaultdict

from app.models.leaderboard import LeaderboardEntry
from app.repositories.leaderboard_repo import LeaderboardRepository


class LeaderboardService:
    """Service for leaderboard operations"""
    
    def __init__(self, db: Session):
        self.db = db
        self.leaderboard_repo = LeaderboardRepository(db)
    
    def get_leaderboard(
        self,
        challenge_name: str,
        difficulty: Optional[str] = None,
        limit: int = 100
    ) -> List[LeaderboardEntry]:
        """
        Get leaderboard for a challenge (optionally filtered by difficulty)
        
        Args:
            challenge_name: Name of the challenge
            difficulty: Optional difficulty filter (e.g., "GIGA_CHAD", "10x10")
            limit: Maximum number of entries to return
            
        Returns:
            List of LeaderboardEntry objects, sorted by best score
        """
        return self.leaderboard_repo.get_by_challenge(challenge_name, difficulty=difficulty, limit=limit)
    
    def get_leaderboard_by_difficulties(
        self,
        challenge_name: str,
        limit: int = 100
    ) -> Dict[str, List[LeaderboardEntry]]:
        """
        Get leaderboard grouped by difficulty levels
        
        Args:
            challenge_name: Name of the challenge
            limit: Maximum number of entries per difficulty
            
        Returns:
            Dictionary mapping difficulty -> list of entries
        """
        # Get all entries for this challenge
        all_entries = self.leaderboard_repo.get_by_challenge(challenge_name, difficulty=None, limit=limit * 10)
        
        # Group by difficulty
        by_difficulty = defaultdict(list)
        for entry in all_entries:
            diff_key = entry.difficulty if entry.difficulty else "default"
            if len(by_difficulty[diff_key]) < limit:
                by_difficulty[diff_key].append(entry)
        
        return dict(by_difficulty)
    
    def get_user_leaderboard_entries(self, username: str) -> List[LeaderboardEntry]:
        """Get all leaderboard entries for a user"""
        return self.leaderboard_repo.get_by_user(username)
    
    def get_user_rank(self, username: str, challenge_name: str) -> tuple[int, LeaderboardEntry]:
        """
        Get user's rank on a specific leaderboard
        
        Returns:
            Tuple of (rank, entry) or (None, None) if not on leaderboard
        """
        leaderboard = self.get_leaderboard(challenge_name, limit=1000)
        
        for idx, entry in enumerate(leaderboard, start=1):
            if entry.username == username:
                return idx, entry
        
        return None, None
