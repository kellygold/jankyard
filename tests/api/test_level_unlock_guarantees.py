"""
GUARANTEE TESTS for Level Unlock System

These tests define the EXACT behavior that must work after implementation.
They serve as acceptance criteria - if these pass, the fix is complete.

Run these before AND after implementation:
  BEFORE: Some tests will fail (expected)
  AFTER:  All tests must pass (guarantee)
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


@pytest.mark.api
@pytest.mark.level_progression
class TestGuarantee_LevelUnlockFlow:
    """
    GUARANTEE: Complete level unlock flow works end-to-end.
    
    This simulates the full user journey:
    1. User starts with level 1 only
    2. User completes level 1 (score saved to leaderboard)
    3. User checks progress - level 2 is now unlocked
    4. User refreshes page - level 2 is still unlocked
    """
    
    def test_guarantee_complete_flow_firewall(
        self,
        client: TestClient,
        auth_headers: dict,
        leaderboard_entry_factory,
        test_user
    ):
        """GUARANTEE: Firewall level progression works."""
        # Step 1: Fresh user has only level 1
        response = client.get("/leaderboard/firewall/progress", headers=auth_headers)
        assert response.status_code == 200
        initial_levels = response.json()["unlocked_levels"]
        assert initial_levels == [1], "New user should only have level 1"
        
        # Step 2: User beats level 1 (simulated by creating leaderboard entry)
        leaderboard_entry_factory(
            challenge_name="firewall",
            difficulty="LEVEL_1",
            score=100
        )
        
        # Step 3: Check progress - level 2 should be unlocked
        response = client.get("/leaderboard/firewall/progress", headers=auth_headers)
        assert response.status_code == 200
        updated_levels = response.json()["unlocked_levels"]
        assert 1 in updated_levels, "Level 1 should still be unlocked"
        assert 2 in updated_levels, "Level 2 should now be unlocked after beating level 1"
        
        # Step 4: "Refresh" - check again, should persist
        response = client.get("/leaderboard/firewall/progress", headers=auth_headers)
        assert response.status_code == 200
        persisted_levels = response.json()["unlocked_levels"]
        assert persisted_levels == updated_levels, "Progress should persist across requests"
    
    def test_guarantee_complete_flow_giga_chad(
        self,
        client: TestClient,
        auth_headers: dict,
        leaderboard_entry_factory,
        test_user
    ):
        """GUARANTEE: Giga Chad 4-level progression works."""
        # Fresh user
        response = client.get("/leaderboard/giga_chad/progress", headers=auth_headers)
        assert response.json()["unlocked_levels"] == [1]
        
        # Beat BABY_CHAD -> unlocks CHAD
        leaderboard_entry_factory("giga_chad", "BABY_CHAD", 50)
        response = client.get("/leaderboard/giga_chad/progress", headers=auth_headers)
        assert response.json()["unlocked_levels"] == [1, 2]
        
        # Beat CHAD -> unlocks MEGA_CHAD
        leaderboard_entry_factory("giga_chad", "CHAD", 100)
        response = client.get("/leaderboard/giga_chad/progress", headers=auth_headers)
        assert response.json()["unlocked_levels"] == [1, 2, 3]
        
        # Beat MEGA_CHAD -> unlocks GIGA_CHAD
        leaderboard_entry_factory("giga_chad", "MEGA_CHAD", 150)
        response = client.get("/leaderboard/giga_chad/progress", headers=auth_headers)
        assert response.json()["unlocked_levels"] == [1, 2, 3, 4]
    
    def test_guarantee_complete_flow_glitch(
        self,
        client: TestClient,
        auth_headers: dict,
        leaderboard_entry_factory,
        test_user
    ):
        """GUARANTEE: Glitch 3-level progression works (lowercase difficulties)."""
        # Fresh user
        response = client.get("/leaderboard/glitch/progress", headers=auth_headers)
        assert response.json()["unlocked_levels"] == [1]
        
        # Beat level_1 -> unlocks level 2
        leaderboard_entry_factory("glitch", "level_1", 170)
        response = client.get("/leaderboard/glitch/progress", headers=auth_headers)
        levels = response.json()["unlocked_levels"]
        assert 2 in levels, "Level 2 should unlock after beating level_1"
        
        # Beat level_2 -> unlocks level 3
        leaderboard_entry_factory("glitch", "level_2", 150)
        response = client.get("/leaderboard/glitch/progress", headers=auth_headers)
        levels = response.json()["unlocked_levels"]
        assert 3 in levels, "Level 3 should unlock after beating level_2"


@pytest.mark.api
@pytest.mark.level_progression
class TestGuarantee_AnonymousUserProgress:
    """
    GUARANTEE: Anonymous users can track progress via username.
    
    After Phase 3 fix, anonymous users who:
    1. Enter a username in the form
    2. Complete a level (score saved under that username)
    3. Should be able to query their progress with ?username=X
    """
    
    def test_guarantee_anonymous_progress_with_username_param(
        self,
        client: TestClient,
        db: Session,
        leaderboard_entry_factory
    ):
        """
        GUARANTEE: Anonymous user can fetch progress with username param.
        
        BEFORE FIX: Returns 401 (requires auth)
        AFTER FIX: Returns 200 with correct unlocked_levels
        """
        # Create entry for anonymous user (no user_id)
        leaderboard_entry_factory(
            challenge_name="firewall",
            difficulty="LEVEL_1",
            score=100,
            username="anon_test_user_xyz"
        )
        
        # Query progress with username param (no auth header)
        response = client.get(
            "/leaderboard/firewall/progress",
            params={"username": "anon_test_user_xyz"}
        )
        
        # This assertion defines the REQUIRED behavior after fix
        if response.status_code == 401:
            pytest.fail(
                "IMPLEMENTATION NEEDED: Progress endpoint should accept username param for anonymous users. "
                "See Phase 3 in IMPLEMENTATION_PLAN.md"
            )
        
        assert response.status_code == 200
        levels = response.json()["unlocked_levels"]
        assert 2 in levels, "Anonymous user should have level 2 unlocked after beating level 1"
    
    def test_guarantee_anonymous_no_username_gets_level_1(self, client: TestClient):
        """
        GUARANTEE: Anonymous user with no username gets only level 1.
        """
        response = client.get("/leaderboard/firewall/progress")
        
        if response.status_code == 401:
            pytest.fail(
                "IMPLEMENTATION NEEDED: Progress endpoint should return [1] for anonymous users without username. "
                "See Phase 3 in IMPLEMENTATION_PLAN.md"
            )
        
        assert response.status_code == 200
        assert response.json()["unlocked_levels"] == [1]


@pytest.mark.api
@pytest.mark.level_progression  
class TestGuarantee_DifficultyNameMatching:
    """
    GUARANTEE: Difficulty names match between frontend and backend.
    
    Common bug: Frontend sends "LEVEL_1" but backend checks for "level_1".
    These tests verify the EXACT difficulty names that must work.
    """
    
    @pytest.mark.parametrize("challenge,difficulty", [
        ("firewall", "LEVEL_1"),
        ("firewall", "LEVEL_2"),
        ("firewall", "LEVEL_3"),
        ("giga_chad", "BABY_CHAD"),
        ("giga_chad", "CHAD"),
        ("giga_chad", "MEGA_CHAD"),
        ("giga_chad", "GIGA_CHAD"),
        ("glitch", "level_1"),
        ("glitch", "level_2"),
        ("glitch", "level_3"),
        ("interrogation", "level_1"),
        ("interrogation", "level_2"),
        ("interrogation", "level_3"),
        ("debate_battle", "easy"),
        ("debate_battle", "hard"),
        ("arena", "easy"),
        ("arena", "hard"),
    ])
    def test_guarantee_difficulty_name_recognized(
        self,
        client: TestClient,
        auth_headers: dict,
        leaderboard_entry_factory,
        test_user,
        challenge: str,
        difficulty: str
    ):
        """GUARANTEE: Each difficulty name is recognized by progress endpoint."""
        # Create entry with this exact difficulty name
        leaderboard_entry_factory(
            challenge_name=challenge,
            difficulty=difficulty,
            score=100
        )
        
        # Check that it affects unlocked levels
        response = client.get(
            f"/leaderboard/{challenge}/progress",
            headers=auth_headers
        )
        assert response.status_code == 200
        levels = response.json()["unlocked_levels"]
        
        # Should have more than just level 1 (the entry should have unlocked something)
        assert len(levels) >= 1, f"Difficulty '{difficulty}' for {challenge} should be recognized"


@pytest.mark.api
class TestGuarantee_IsolatedProgress:
    """
    GUARANTEE: Progress is isolated per user and per challenge.
    """
    
    def test_guarantee_different_users_isolated(
        self,
        client: TestClient,
        db: Session,
        leaderboard_entry_factory,
        test_user
    ):
        """GUARANTEE: One user's progress doesn't affect another."""
        from app.models.user import User
        from app.core import create_access_token, get_password_hash
        
        # Create second user
        user2 = User(
            username="other_user",
            email="other@example.com",
            hashed_password=get_password_hash("pass123")
        )
        db.add(user2)
        db.commit()
        
        # User 1 beats level 1
        leaderboard_entry_factory("firewall", "LEVEL_1", 100)
        
        # User 1 should have level 2
        token1 = create_access_token(data={"sub": test_user.username})
        response = client.get(
            "/leaderboard/firewall/progress",
            headers={"Authorization": f"Bearer {token1}"}
        )
        assert 2 in response.json()["unlocked_levels"]
        
        # User 2 should NOT have level 2
        token2 = create_access_token(data={"sub": user2.username})
        response = client.get(
            "/leaderboard/firewall/progress",
            headers={"Authorization": f"Bearer {token2}"}
        )
        assert response.json()["unlocked_levels"] == [1]
    
    def test_guarantee_different_challenges_isolated(
        self,
        client: TestClient,
        auth_headers: dict,
        leaderboard_entry_factory,
        test_user
    ):
        """GUARANTEE: Progress in one challenge doesn't affect another."""
        # Beat firewall level 1
        leaderboard_entry_factory("firewall", "LEVEL_1", 100)
        
        # Firewall has level 2
        response = client.get("/leaderboard/firewall/progress", headers=auth_headers)
        assert 2 in response.json()["unlocked_levels"]
        
        # Glitch still only level 1
        response = client.get("/leaderboard/glitch/progress", headers=auth_headers)
        assert response.json()["unlocked_levels"] == [1]
        
        # Giga Chad still only level 1
        response = client.get("/leaderboard/giga_chad/progress", headers=auth_headers)
        assert response.json()["unlocked_levels"] == [1]
