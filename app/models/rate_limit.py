"""Rate limit tracking model"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Index

from app.core.database import Base


class RateLimit(Base):
    """Rate limit model - tracks API usage per identifier"""
    __tablename__ = "rate_limits"
    
    id = Column(Integer, primary_key=True, index=True)
    identifier = Column(String(100), nullable=False, index=True)  # IP address or user_id
    identifier_type = Column(String(20), nullable=False)  # 'ip' or 'user'
    endpoint = Column(String(100), nullable=False, index=True)  # e.g., '/submit'
    request_count = Column(Integer, default=1, nullable=False)
    window_start = Column(DateTime, nullable=False, index=True)
    window_type = Column(String(20), nullable=False)  # 'minute' or 'day'
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    __table_args__ = (
        # Composite index for fast lookups
        Index('idx_rate_limit_lookup', 'identifier', 'endpoint', 'window_type', 'window_start'),
    )
    
    def __repr__(self):
        return f"<RateLimit(identifier='{self.identifier}', endpoint='{self.endpoint}', count={self.request_count})>"
