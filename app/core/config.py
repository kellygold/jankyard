"""Configuration management for Jankyard.ai"""
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Application configuration"""
    
    # Environment (check this first)
    ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
    DEBUG = ENVIRONMENT == "development"
    
    # Database
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://localhost:5432/jankyard")
    
    # Security - NEVER use default in production
    SECRET_KEY = os.getenv("SECRET_KEY")
    if not SECRET_KEY:
        if ENVIRONMENT == "development":
            SECRET_KEY = "dev-secret-key-for-local-development-only"
        else:
            raise ValueError(
                "SECRET_KEY environment variable must be set in production! "
                "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
            )
    
    # Sandbox execution limits
    MAX_EXECUTION_TIME_PER_STEP = 0.1  # 100ms per step
    MAX_STEPS_PER_RUN = 100
    MAX_MEMORY_SIZE: int = 1024 * 1024  # 1MB for agent memory
    
    # LLM settings
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    DEFAULT_LLM_PROVIDER: str = os.getenv("DEFAULT_LLM_PROVIDER", "openai")
    DEFAULT_MODEL: str = os.getenv("DEFAULT_MODEL", "gpt-6-luna")
    
    # File upload
    MAX_UPLOAD_SIZE: int = 50 * 1024  # 50KB max for agent.py
    ALLOWED_EXTENSIONS = {".py"}
    
    # JWT Authentication
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
    RECOVERED_TURNS_PER_DAY: int = int(os.getenv("RECOVERED_TURNS_PER_DAY", "1000"))
    GUEST_SESSIONS_PER_MINUTE: int = int(os.getenv("GUEST_SESSIONS_PER_MINUTE", "1000"))
    GUEST_SESSIONS_PER_DAY: int = int(os.getenv("GUEST_SESSIONS_PER_DAY", "10000"))
    SUBMISSIONS_PER_MINUTE: int = int(os.getenv("SUBMISSIONS_PER_MINUTE", "5"))
    SUBMISSIONS_PER_DAY: int = int(os.getenv("SUBMISSIONS_PER_DAY", "100"))


config = Config()
