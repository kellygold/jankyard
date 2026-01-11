"""Custom exceptions for the application"""
from fastapi import HTTPException, status


class JankyardException(Exception):
    """Base exception for all Jankyard errors"""
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class AuthenticationError(JankyardException):
    """Raised when authentication fails"""
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, status.HTTP_401_UNAUTHORIZED)


class UserAlreadyExistsError(JankyardException):
    """Raised when attempting to create a user that already exists"""
    def __init__(self, username: str):
        super().__init__(f"User '{username}' already exists", status.HTTP_400_BAD_REQUEST)


class UserNotFoundError(JankyardException):
    """Raised when a user is not found"""
    def __init__(self, username: str):
        super().__init__(f"User '{username}' not found", status.HTTP_404_NOT_FOUND)


class InvalidCredentialsError(AuthenticationError):
    """Raised when login credentials are invalid"""
    def __init__(self):
        super().__init__("Incorrect username or password")


class UserInactiveError(JankyardException):
    """Raised when attempting to authenticate an inactive user"""
    def __init__(self):
        super().__init__("User account is disabled", status.HTTP_403_FORBIDDEN)


class RateLimitExceededError(JankyardException):
    """Raised when rate limit is exceeded"""
    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(message, status.HTTP_429_TOO_MANY_REQUESTS)


class ChallengeNotFoundError(JankyardException):
    """Raised when a challenge is not found"""
    def __init__(self, challenge_name: str):
        super().__init__(f"Challenge '{challenge_name}' not found", status.HTTP_404_NOT_FOUND)


class SubmissionError(JankyardException):
    """Raised when submission processing fails"""
    def __init__(self, message: str):
        super().__init__(f"Submission error: {message}", status.HTTP_400_BAD_REQUEST)


class SandboxError(JankyardException):
    """Raised when sandbox execution fails"""
    def __init__(self, message: str):
        super().__init__(f"Sandbox error: {message}", status.HTTP_500_INTERNAL_SERVER_ERROR)


def janky_exception_handler(request, exc: JankyardException):
    """Convert JankyardException to HTTPException"""
    return HTTPException(
        status_code=exc.status_code,
        detail=exc.message
    )
