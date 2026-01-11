"""Authentication API endpoints"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core import get_db, InvalidCredentialsError, UserAlreadyExistsError
from app.routes.deps import get_current_user
from app.services.auth_service import AuthService
from app.schemas.auth import UserCreate, UserResponse, Token
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse)
async def register(
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    """Register a new user account"""
    try:
        auth_service = AuthService(db)
        user = auth_service.register_user(user_data)
        return user
    except UserAlreadyExistsError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e.message))


@router.post("/token", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Login to get JWT access token"""
    try:
        auth_service = AuthService(db)
        user = auth_service.authenticate_user(form_data.username, form_data.password)
        access_token = auth_service.create_access_token_for_user(user)
        return {"access_token": access_token, "token_type": "bearer"}
    except (InvalidCredentialsError, Exception) as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """Get current user information"""
    return current_user


@router.get("/check")
async def check_auth(
    current_user: User = Depends(get_current_user)
):
    """Check if user is authenticated"""
    if current_user:
        return {
            "authenticated": True,
            "username": current_user.username,
            "user_id": current_user.id
        }
    return {"authenticated": False}
