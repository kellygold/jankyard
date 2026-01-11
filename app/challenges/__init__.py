"""
Challenges module - Auto-discovers all challenges

No manual imports needed! Just add a challenge file and it's automatically registered.
"""
from app.challenges.registry import ChallengeRegistry
from app.challenges.base import BaseChallenge

# 🎉 Auto-discover all challenges in this directory
ChallengeRegistry.auto_discover()

# Export CHALLENGES dictionary for backward compatibility
CHALLENGES = ChallengeRegistry.get_all()

# Export base classes for convenience
__all__ = [
    'BaseChallenge',
    'ChallengeRegistry',
    'CHALLENGES'
]
