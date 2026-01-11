"""Submission schemas"""
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class SubmissionBase(BaseModel):
    """Base submission schema"""
    challenge_name: str = Field(..., min_length=1, max_length=50)
    agent_code: Optional[str] = Field(None, max_length=100000)


class SubmissionCreate(SubmissionBase):
    """Schema for creating a submission"""
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    agent_type: str = Field("code", pattern="^(code|prompt)$")
    difficulty: Optional[str] = None


class SubmissionResponse(BaseModel):
    """Schema for submission response"""
    id: int
    user_id: Optional[int]
    challenge_name: str
    score: int
    steps: int
    success: bool
    status: str
    error_message: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


class SubmissionDetail(SubmissionResponse):
    """Schema for detailed submission (includes logs and code)"""
    logs: Optional[dict]
    agent_code: Optional[str]
    
    class Config:
        from_attributes = True
