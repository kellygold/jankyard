"""Rate limit repository"""
from typing import Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.models.rate_limit import RateLimit
from app.repositories.base import BaseRepository


class RateLimitRepository(BaseRepository[RateLimit]):
    """Repository for RateLimit model"""
    
    def __init__(self, db: Session):
        super().__init__(RateLimit, db)
    
    def get_limit(
        self,
        identifier: str,
        endpoint: str,
        window_type: str,
        window_start: datetime
    ) -> Optional[RateLimit]:
        """Get rate limit entry for a specific window"""
        return (
            self.db.query(RateLimit)
            .filter(
                RateLimit.identifier == identifier,
                RateLimit.endpoint == endpoint,
                RateLimit.window_type == window_type,
                RateLimit.window_start == window_start
            )
            .first()
        )
    
    def increment_or_create(
        self,
        identifier: str,
        identifier_type: str,
        endpoint: str,
        window_type: str,
        window_start: datetime
    ) -> RateLimit:
        """Increment request count or create new entry"""
        entry = self.get_limit(identifier, endpoint, window_type, window_start)
        
        if entry:
            # Increment existing entry
            entry.request_count += 1
            entry.updated_at = datetime.utcnow()
            self.db.flush()
            return entry
        else:
            # Create new entry
            return self.create(
                identifier=identifier,
                identifier_type=identifier_type,
                endpoint=endpoint,
                window_type=window_type,
                window_start=window_start,
                request_count=1
            )
    
    def cleanup_old_entries(self, days: int = 7):
        """Delete rate limit entries older than specified days"""
        cutoff = datetime.utcnow() - timedelta(days=days)
        deleted = (
            self.db.query(RateLimit)
            .filter(RateLimit.created_at < cutoff)
            .delete()
        )
        self.db.flush()
        return deleted
    
    def get_usage_count(
        self,
        identifier: str,
        endpoint: str,
        window_type: str,
        window_start: datetime
    ) -> int:
        """Get current usage count for a window"""
        entry = self.get_limit(identifier, endpoint, window_type, window_start)
        return entry.request_count if entry else 0
