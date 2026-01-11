"""Database configuration and session management"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

from app.core.config import config

# Build engine kwargs - pooling options only for non-SQLite databases
engine_kwargs = {
    "pool_pre_ping": True,
    "echo": False
}

# SQLite doesn't support connection pooling options
if not config.DATABASE_URL.startswith("sqlite"):
    engine_kwargs.update({
        "pool_size": 5,           # Number of connections to keep open
        "max_overflow": 10,       # Max additional connections during peak load
        "pool_timeout": 30,       # Seconds to wait for connection from pool
        "pool_recycle": 1800,     # Recycle connections after 30 minutes
    })

# Create SQLAlchemy engine
engine = create_engine(config.DATABASE_URL, **engine_kwargs)

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create Base class for models
Base = declarative_base()


def get_db() -> Session:
    """
    Dependency to get database session.
    Use with FastAPI Depends.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)
