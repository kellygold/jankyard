"""
Pytest fixtures for Jankyard tests.
Provides test database, FastAPI test client, and authentication helpers.
"""
import os
import pytest
from typing import Generator, Optional
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

# Set test environment before importing app
os.environ["TESTING"] = "1"
TEST_DATABASE_URL = os.getenv("JANKYARD_TEST_DATABASE_URL", "sqlite:///:memory:")
if TEST_DATABASE_URL != "sqlite:///:memory:":
    from sqlalchemy.engine import make_url
    test_url = make_url(TEST_DATABASE_URL)
    if test_url.host not in {"127.0.0.1", "localhost"} or test_url.database != "jankyard_recovery_test":
        raise RuntimeError("Tests require a dedicated local jankyard_recovery_test database")
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
if os.getenv("RUN_LIVE_MODELS") != "1":
    os.environ["OPENAI_API_KEY"] = ""
    os.environ["ANTHROPIC_API_KEY"] = ""

from app.main import app
from app.core import get_db, create_access_token, get_password_hash
from app.core.database import Base
from app.models.user import User
from app.models.leaderboard import LeaderboardEntry


# Test database engine (in-memory SQLite)
engine = create_engine(TEST_DATABASE_URL, **({
    "connect_args": {"check_same_thread": False}, "poolclass": StaticPool,
} if TEST_DATABASE_URL.startswith("sqlite") else {}))
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override database dependency for tests."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="function")
def db() -> Generator[Session, None, None]:
    """Create a fresh database for each test."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db: Session) -> Generator[TestClient, None, None]:
    """FastAPI test client with test database."""
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def test_user(db: Session) -> User:
    """Create a test user."""
    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password=get_password_hash("testpass123")
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def auth_token(test_user: User) -> str:
    """Create an auth token for the test user."""
    return create_access_token(data={"sub": test_user.username})


@pytest.fixture
def auth_headers(auth_token: str) -> dict:
    """Authorization headers for authenticated requests."""
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture
def leaderboard_entry_factory(db: Session, test_user: User):
    """Factory to create leaderboard entries."""
    def _create(
        challenge_name: str,
        difficulty: str,
        score: int = 100,
        username: Optional[str] = None
    ) -> LeaderboardEntry:
        entry = LeaderboardEntry(
            challenge_name=challenge_name,
            difficulty=difficulty,
            best_score=score,
            best_steps=1,
            username=username or test_user.username,
            user_id=test_user.id if not username else None
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)
        return entry
    return _create


# Challenge configurations for testing
MULTI_LEVEL_CHALLENGES = {
    "firewall": {
        "max_level": 3,
        "difficulties": ["LEVEL_1", "LEVEL_2", "LEVEL_3"]
    },
    "glitch": {
        "max_level": 3,
        "difficulties": ["level_1", "level_2", "level_3"]
    },
    "interrogation": {
        "max_level": 3,
        "difficulties": ["level_1", "level_2", "level_3"]
    },
    "giga_chad": {
        "max_level": 4,
        "difficulties": ["BABY_CHAD", "CHAD", "MEGA_CHAD", "GIGA_CHAD"]
    },
    "debate_battle": {
        "max_level": 2,
        "difficulties": ["easy", "hard"]
    },
    "arena": {
        "max_level": 2,
        "difficulties": ["easy", "hard"]
    }
}


@pytest.fixture
def challenge_configs():
    """Get challenge configurations."""
    return MULTI_LEVEL_CHALLENGES
