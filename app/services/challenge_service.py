"""Challenge service"""
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from app.challenges import CHALLENGES
from app.challenges.base import BaseChallenge, ChallengeResult
from app.core.exceptions import ChallengeNotFoundError, SubmissionError
from app.core.logging import get_logger

logger = get_logger(__name__)


class ChallengeService:
    """Service for challenge operations"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_challenge(self, challenge_name: str, config: Optional[Dict[str, Any]] = None) -> BaseChallenge:
        """
        Get a challenge instance by name
        
        Args:
            challenge_name: Name of the challenge
            config: Optional configuration dict (e.g., {'difficulty': 'hard'})
            
        Returns:
            Challenge instance
            
        Raises:
            ChallengeNotFoundError: If challenge not found
        """
        challenge_class = CHALLENGES.get(challenge_name)
        if not challenge_class:
            raise ChallengeNotFoundError(challenge_name)
        
        return challenge_class(config) if config else challenge_class()
    
    def list_challenges(self) -> dict:
        """
        List all available challenges
        
        Returns:
            Dictionary of challenge names to classes
        """
        return CHALLENGES.copy()
    
    def validate_challenge_exists(self, challenge_name: str) -> bool:
        """Check if a challenge exists"""
        return challenge_name in CHALLENGES
    
    def get_challenge_info(self, challenge_name: str) -> dict:
        """
        Get information about a challenge
        
        Args:
            challenge_name: Name of the challenge
            
        Returns:
            Dictionary with challenge metadata
        """
        challenge = self.get_challenge(challenge_name)
        
        return {
            "name": challenge_name,
            "description": challenge.description if hasattr(challenge, 'description') else None,
            "max_steps": challenge.max_steps if hasattr(challenge, 'max_steps') else None,
            "timeout": challenge.timeout if hasattr(challenge, 'timeout') else None,
        }
