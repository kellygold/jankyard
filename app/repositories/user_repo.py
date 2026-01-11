"""User repository"""
from typing import Optional
from sqlalchemy.orm import Session

from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Repository for User model"""
    
    def __init__(self, db: Session):
        super().__init__(User, db)
    
    def get_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        return self.db.query(User).filter(User.username == username).first()
    
    def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        return self.db.query(User).filter(User.email == email).first()
    
    def get_active_users(self, skip: int = 0, limit: int = 100):
        """Get all active users"""
        return self.db.query(User).filter(User.is_active == True).offset(skip).limit(limit).all()
    
    def create_user(
        self,
        username: str,
        hashed_password: Optional[str] = None,
        email: Optional[str] = None,
        is_active: bool = True
    ) -> User:
        """Create a new user"""
        return self.create(
            username=username,
            hashed_password=hashed_password,
            email=email,
            is_active=is_active
        )
    
    def deactivate_user(self, user: User) -> User:
        """Deactivate a user"""
        return self.update(user, is_active=False)
    
    def activate_user(self, user: User) -> User:
        """Activate a user"""
        return self.update(user, is_active=True)
