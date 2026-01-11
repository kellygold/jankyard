"""Rate limit service - DB-backed rate limiting"""
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.core.config import config
from app.core.exceptions import RateLimitExceededError
from app.repositories.rate_limit_repo import RateLimitRepository


class RateLimitService:
    """Service for database-backed rate limiting"""
    
    def __init__(self, db: Session):
        self.db = db
        self.rate_limit_repo = RateLimitRepository(db)
    
    def check_rate_limit(
        self,
        identifier: str,
        endpoint: str,
        identifier_type: str = "ip"
    ):
        """
        Check if request is within rate limits
        
        Args:
            identifier: IP address or user_id
            endpoint: API endpoint being accessed
            identifier_type: 'ip' or 'user'
            
        Raises:
            RateLimitExceededError: If rate limit is exceeded
        """
        if not config.RATE_LIMIT_ENABLED:
            return
        
        # Check minute limit
        minute_window = self._get_window_start('minute')
        minute_count = self.rate_limit_repo.get_usage_count(
            identifier, endpoint, 'minute', minute_window
        )
        
        if minute_count >= config.SUBMISSIONS_PER_MINUTE:
            raise RateLimitExceededError(
                f"Rate limit exceeded: {config.SUBMISSIONS_PER_MINUTE} requests per minute"
            )
        
        # Check daily limit
        day_window = self._get_window_start('day')
        day_count = self.rate_limit_repo.get_usage_count(
            identifier, endpoint, 'day', day_window
        )
        
        if day_count >= config.SUBMISSIONS_PER_DAY:
            raise RateLimitExceededError(
                f"Daily limit exceeded: {config.SUBMISSIONS_PER_DAY} requests per day"
            )
    
    def record_request(
        self,
        identifier: str,
        endpoint: str,
        identifier_type: str = "ip"
    ):
        """
        Record a request in the rate limit tracker
        
        Args:
            identifier: IP address or user_id
            endpoint: API endpoint being accessed
            identifier_type: 'ip' or 'user'
        """
        if not config.RATE_LIMIT_ENABLED:
            return
        
        # Record for minute window
        minute_window = self._get_window_start('minute')
        self.rate_limit_repo.increment_or_create(
            identifier=identifier,
            identifier_type=identifier_type,
            endpoint=endpoint,
            window_type='minute',
            window_start=minute_window
        )
        
        # Record for day window
        day_window = self._get_window_start('day')
        self.rate_limit_repo.increment_or_create(
            identifier=identifier,
            identifier_type=identifier_type,
            endpoint=endpoint,
            window_type='day',
            window_start=day_window
        )
        
        self.rate_limit_repo.commit()
    
    def cleanup_old_entries(self, days: int = 7) -> int:
        """
        Clean up old rate limit entries
        
        Args:
            days: Delete entries older than this many days
            
        Returns:
            Number of entries deleted
        """
        deleted = self.rate_limit_repo.cleanup_old_entries(days)
        self.rate_limit_repo.commit()
        return deleted
    
    @staticmethod
    def _get_window_start(window_type: str) -> datetime:
        """
        Get the start of the current rate limit window
        
        Args:
            window_type: 'minute' or 'day'
            
        Returns:
            Datetime at the start of the window
        """
        now = datetime.utcnow()
        
        if window_type == 'minute':
            # Start of current minute
            return now.replace(second=0, microsecond=0)
        elif window_type == 'day':
            # Start of current day
            return now.replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            raise ValueError(f"Invalid window_type: {window_type}")
