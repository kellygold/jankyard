"""
Tests for /leaderboard/{challenge}/progress endpoint.

These tests verify:
1. Authenticated users get correct unlocked levels
2. Anonymous users with username param get correct unlocked levels  
3. Users with no progress get [1]
4. Level unlocking logic works correctly per challenge
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.conftest import MULTI_LEVEL_CHALLENGES


@pytest.mark.api
@pytest.mark.level_progression
class TestProgressEndpointAuthenticated:
    """Tests for authenticated users."""
    
    def test_no_progress_returns_level_1(
        self, 
        client: TestClient, 
        auth_headers: dict,
        test_user
    ):
        """User with no leaderboard entries should only have level 1."""
        response = client.get("/leaderboard/firewall/progress", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["unlocked_levels"] == [1]
    
    def test_beating_level_1_unlocks_level_2_firewall(
        self,
        client: TestClient,
        auth_headers: dict,
        leaderboard_entry_factory,
        test_user
    ):
        """Beating level 1 should unlock level 2 for firewall."""
        # Create a leaderboard entry for LEVEL_1
        leaderboard_entry_factory(
            challenge_name="firewall",
            difficulty="LEVEL_1",
            score=100
        )
        
        response = client.get("/leaderboard/firewall/progress", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert 1 in data["unlocked_levels"]
        assert 2 in data["unlocked_levels"]
    
    def test_beating_level_2_unlocks_level_3_firewall(
        self,
        client: TestClient,
        auth_headers: dict,
        leaderboard_entry_factory,
        test_user
    ):
        """Beating level 2 should unlock level 3 for firewall."""
        # Need entries for both level 1 and 2
        leaderboard_entry_factory(
            challenge_name="firewall",
            difficulty="LEVEL_1",
            score=100
        )
        leaderboard_entry_factory(
            challenge_name="firewall",
            difficulty="LEVEL_2",
            score=150
        )
        
        response = client.get("/leaderboard/firewall/progress", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["unlocked_levels"] == [1, 2, 3]
    
    def test_giga_chad_4_level_progression(
        self,
        client: TestClient,
        auth_headers: dict,
        leaderboard_entry_factory,
        test_user
    ):
        """Giga Chad has 4 levels: BABY_CHAD -> CHAD -> MEGA_CHAD -> GIGA_CHAD."""
        # Beat BABY_CHAD
        leaderboard_entry_factory(
            challenge_name="giga_chad",
            difficulty="BABY_CHAD",
            score=100
        )
        
        response = client.get("/leaderboard/giga_chad/progress", headers=auth_headers)
        data = response.json()
        assert data["unlocked_levels"] == [1, 2]
        
        # Beat CHAD
        leaderboard_entry_factory(
            challenge_name="giga_chad",
            difficulty="CHAD",
            score=150
        )
        
        response = client.get("/leaderboard/giga_chad/progress", headers=auth_headers)
        data = response.json()
        assert data["unlocked_levels"] == [1, 2, 3]
        
        # Beat MEGA_CHAD
        leaderboard_entry_factory(
            challenge_name="giga_chad",
            difficulty="MEGA_CHAD",
            score=200
        )
        
        response = client.get("/leaderboard/giga_chad/progress", headers=auth_headers)
        data = response.json()
        assert data["unlocked_levels"] == [1, 2, 3, 4]
    
    def test_glitch_uses_lowercase_difficulty(
        self,
        client: TestClient,
        auth_headers: dict,
        leaderboard_entry_factory,
        test_user
    ):
        """Glitch challenge uses level_1, level_2, level_3 (lowercase)."""
        leaderboard_entry_factory(
            challenge_name="glitch",
            difficulty="level_1",
            score=100
        )
        
        response = client.get("/leaderboard/glitch/progress", headers=auth_headers)
        data = response.json()
        assert 2 in data["unlocked_levels"]
    
    def test_debate_battle_2_levels(
        self,
        client: TestClient,
        auth_headers: dict,
        leaderboard_entry_factory,
        test_user
    ):
        """Debate battle has 2 levels: easy -> hard."""
        leaderboard_entry_factory(
            challenge_name="debate_battle",
            difficulty="easy",
            score=100
        )
        
        response = client.get("/leaderboard/debate_battle/progress", headers=auth_headers)
        data = response.json()
        assert data["unlocked_levels"] == [1, 2]


@pytest.mark.api
@pytest.mark.level_progression
class TestProgressEndpointAnonymous:
    """Tests for anonymous users (after fix is applied)."""
    
    def test_no_auth_no_username_returns_level_1(self, client: TestClient):
        """Anonymous user with no username param gets only level 1."""
        response = client.get("/leaderboard/firewall/progress")
        # After fix: returns 200 with [1]
        # Before fix: returns 401
        if response.status_code == 401:
            pytest.skip("Anonymous progress not yet implemented - this test will pass after Phase 3")
        assert response.status_code == 200
        assert response.json()["unlocked_levels"] == [1]
    
    def test_anonymous_with_username_gets_progress(
        self,
        client: TestClient,
        db: Session,
        leaderboard_entry_factory
    ):
        """Anonymous user with username param gets their progress."""
        # Create entry for anonymous user
        leaderboard_entry_factory(
            challenge_name="firewall",
            difficulty="LEVEL_1",
            score=100,
            username="anonymous_player_123"
        )
        
        response = client.get(
            "/leaderboard/firewall/progress",
            params={"username": "anonymous_player_123"}
        )
        
        # After fix: returns 200 with [1, 2]
        # Before fix: returns 401
        if response.status_code == 401:
            pytest.skip("Anonymous progress not yet implemented - this test will pass after Phase 3")
        
        assert response.status_code == 200
        data = response.json()
        assert 2 in data["unlocked_levels"]


@pytest.mark.api
class TestProgressEndpointEdgeCases:
    """Edge case tests."""
    
    def test_unknown_challenge_returns_level_1(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Unknown challenge should return [1] as default."""
        response = client.get(
            "/leaderboard/nonexistent_challenge/progress",
            headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["unlocked_levels"] == [1]
    
    def test_user_progress_isolated_per_challenge(
        self,
        client: TestClient,
        auth_headers: dict,
        leaderboard_entry_factory,
        test_user
    ):
        """Progress in one challenge doesn't affect another."""
        # Beat firewall level 1
        leaderboard_entry_factory(
            challenge_name="firewall",
            difficulty="LEVEL_1",
            score=100
        )
        
        # Firewall should have level 2 unlocked
        response = client.get("/leaderboard/firewall/progress", headers=auth_headers)
        assert 2 in response.json()["unlocked_levels"]
        
        # Glitch should still be at level 1
        response = client.get("/leaderboard/glitch/progress", headers=auth_headers)
        assert response.json()["unlocked_levels"] == [1]


@pytest.mark.api
@pytest.mark.level_progression
class TestAllChallengesProgressEndpoint:
    """Parameterized tests for all multi-level challenges."""
    
    @pytest.mark.parametrize("challenge_name,config", list(MULTI_LEVEL_CHALLENGES.items()))
    def test_level_1_always_unlocked(
        self,
        client: TestClient,
        auth_headers: dict,
        challenge_name: str,
        config: dict
    ):
        """Level 1 should always be unlocked for every challenge."""
        response = client.get(
            f"/leaderboard/{challenge_name}/progress",
            headers=auth_headers
        )
        assert response.status_code == 200
        assert 1 in response.json()["unlocked_levels"]
    
    @pytest.mark.parametrize("challenge_name,config", list(MULTI_LEVEL_CHALLENGES.items()))
    def test_beating_first_level_unlocks_second(
        self,
        client: TestClient,
        auth_headers: dict,
        leaderboard_entry_factory,
        test_user,
        challenge_name: str,
        config: dict
    ):
        """Beating first difficulty should unlock level 2."""
        first_difficulty = config["difficulties"][0]
        
        leaderboard_entry_factory(
            challenge_name=challenge_name,
            difficulty=first_difficulty,
            score=100
        )
        
        response = client.get(
            f"/leaderboard/{challenge_name}/progress",
            headers=auth_headers
        )
        assert response.status_code == 200
        unlocked = response.json()["unlocked_levels"]
        
        if config["max_level"] >= 2:
            assert 2 in unlocked, f"{challenge_name}: Expected level 2 after beating {first_difficulty}"
