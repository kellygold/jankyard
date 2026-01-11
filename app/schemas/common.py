"""Common/shared Pydantic schemas"""
from typing import Optional
from pydantic import BaseModel


class ErrorResponse(BaseModel):
    """Standard error response"""
    error: str
    detail: Optional[str] = None


class SuccessResponse(BaseModel):
    """Standard success response"""
    success: bool
    message: str


class PaginationParams(BaseModel):
    """Pagination parameters"""
    skip: int = 0
    limit: int = 100
    
    class Config:
        from_attributes = True
