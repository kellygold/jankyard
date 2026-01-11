"""Challenge schemas"""
from typing import Optional
from pydantic import BaseModel


class ChallengeInfo(BaseModel):
    """Schema for challenge information"""
    name: str
    description: Optional[str]
    max_steps: Optional[int]
    timeout: Optional[int]


class ChallengeList(BaseModel):
    """Schema for list of challenges"""
    challenges: dict
