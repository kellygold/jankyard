"""Authentication service"""
from typing import Optional
from sqlalchemy.orm import Session

from app.core import (
    get_password_hash,
    verify_password,
    create_access_token,
    UserAlreadyExistsError,
    InvalidCredentialsError,
    UserInactiveError,
    UserNotFoundError
)
from app.models.user import User
from app.repositories.user_repo import UserRepository
from app.schemas.auth import UserCreate, UserLogin


class AuthService:
    """Service for authentication operations"""
    
    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)
    
    def register_user(self, user_data: UserCreate) -> User:
        """
        Register a new user
        
        Args:
            user_data: User registration data
            
        Returns:
            Created User object
            
        Raises:
            UserAlreadyExistsError: If username or email already exists
        """
        # Check if username exists
        if self.user_repo.get_by_username(user_data.username):
            raise UserAlreadyExistsError(user_data.username)
        
        # Check if email exists (if provided)
        if user_data.email and self.user_repo.get_by_email(user_data.email):
            raise UserAlreadyExistsError(f"email {user_data.email}")
        
        # Hash password
        hashed_password = get_password_hash(user_data.password)
        
        # Create user
        user = self.user_repo.create_user(
            username=user_data.username,
            email=user_data.email,
            hashed_password=hashed_password,
            is_active=True
        )
        
        self.user_repo.commit()
        return user
    
    def authenticate_user(self, username: str, password: str) -> User:
        """
        Authenticate a user with username and password
        
        Args:
            username: Username
            password: Plain text password
            
        Returns:
            Authenticated User object
            
        Raises:
            InvalidCredentialsError: If credentials are invalid
            UserInactiveError: If user account is disabled
        """
        # Get user
        user = self.user_repo.get_by_username(username)
        
        if not user or not user.hashed_password:
            raise InvalidCredentialsError()
        
        # Verify password
        if not verify_password(password, user.hashed_password):
            raise InvalidCredentialsError()
        
        # Check if user is active
        if not user.is_active:
            raise UserInactiveError()
        
        return user
    
    def create_access_token_for_user(self, user: User) -> str:
        """
        Create JWT access token for a user
        
        Args:
            user: User object
            
        Returns:
            JWT access token string
        """
        return create_access_token(data={"sub": user.username})
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        return self.user_repo.get_by_username(username)
    
    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID"""
        return self.user_repo.get(user_id)
    
    def deactivate_user(self, user_id: int) -> User:
        """Deactivate a user account"""
        user = self.user_repo.get(user_id)
        if not user:
            raise UserNotFoundError(f"user_id {user_id}")
        
        user = self.user_repo.deactivate_user(user)
        self.user_repo.commit()
        return user
