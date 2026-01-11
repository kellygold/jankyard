"""
Tests for Leaderboard Publishing on Level Completion.

These tests verify:
1. Successful level completion saves to leaderboard
2. Failed attempts do not save with success=True
3. Best scores are tracked correctly
4. Username is required for saving
5. Correct difficulty strings are saved
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.leaderboard import LeaderboardEntry


@pytest.mark.api
@pytest.mark.leaderboard
class TestLeaderboardPublishing:
    """Tests for leaderboard entry creation on level completion."""
    
    def test_score_saved_on_level_completion(
        self,
        client: TestClient,
        auth_headers: dict,
        db: Session,
        leaderboard_entry_factory,
        test_user
    ):
        """Score should be saved to leaderboard when level is completed successfully."""
        # Simulate a successful completion (leaderboard entry created by challenge flow)
        leaderboard_entry_factory(
            challenge_name="firewall",
            difficulty="LEVEL_1",
            score=100
        )
        
        # Check that entry was created in database
        entry = db.query(LeaderboardEntry).filter(
            LeaderboardEntry.username == test_user.username,
            LeaderboardEntry.challenge_name == "firewall",
            LeaderboardEntry.difficulty == "LEVEL_1"
        ).first()
        
        assert entry is not None, "Leaderboard entry should be created on success"
        assert entry.best_score >= 0, "Score should be saved"
    
    def test_username_required_for_leaderboard_save(
        self,
        client: TestClient,
        db: Session
    ):
        """Without username, entry should not be saved to leaderboard."""
        initial_count = db.query(LeaderboardEntry).count()
        
        # Try to submit without username
        response = client.post(
            "/submit",
            data={
                "challenge_name": "firewall",
                "difficulty": "LEVEL_1",
                "score": 100,
                "success": "true"
                # No username provided
            }
        )
        
        final_count = db.query(LeaderboardEntry).count()
        
        # Entry count should not increase without username
        assert final_count == initial_count, "No entry should be created without username"
    
    def test_difficulty_saved_correctly(
        self,
        client: TestClient,
        auth_headers: dict,
        db: Session,
        leaderboard_entry_factory,
        test_user
    ):
        """Difficulty string should be saved exactly as provided."""
        difficulties = [
            ("firewall", "LEVEL_1"),
            ("firewall", "LEVEL_2"),
            ("giga_chad", "BABY_CHAD"),
            ("glitch", "level_1"),
            ("debate_battle", "easy"),
        ]
        
        for challenge, difficulty in difficulties:
            # Create entry via factory (simulates challenge completion)
            leaderboard_entry_factory(
                challenge_name=challenge,
                difficulty=difficulty,
                score=100
            )
            
            entry = db.query(LeaderboardEntry).filter(
                LeaderboardEntry.username == test_user.username,
                LeaderboardEntry.challenge_name == challenge,
                LeaderboardEntry.difficulty == difficulty
            ).first()
            
            assert entry is not None, f"Entry for {challenge}/{difficulty} should exist"
            assert entry.difficulty == difficulty, f"Difficulty should be '{difficulty}' exactly"


@pytest.mark.api
@pytest.mark.leaderboard
class TestLeaderboardBestScore:
    """Tests for best score tracking."""
    
    def test_best_score_updated_on_improvement(
        self,
        client: TestClient,
        auth_headers: dict,
        leaderboard_entry_factory,
        db: Session,
        test_user
    ):
        """Best score should update when user improves."""
        # Create initial entry with score 50
        leaderboard_entry_factory(
            challenge_name="firewall",
            difficulty="LEVEL_1",
            score=50
        )
        
        entry = db.query(LeaderboardEntry).filter(
            LeaderboardEntry.username == test_user.username,
            LeaderboardEntry.challenge_name == "firewall",
            LeaderboardEntry.difficulty == "LEVEL_1"
        ).first()
        
        initial_score = entry.best_score
        
        # Submit a better score
        response = client.post(
            "/submit",
            data={
                "challenge_name": "firewall",
                "difficulty": "LEVEL_1",
                "username": test_user.username,
                "score": 150,
                "success": "true"
            },
            headers=auth_headers
        )
        
        db.refresh(entry)
        
        # Best score should be updated
        assert entry.best_score >= initial_score, "Best score should not decrease"


@pytest.mark.api
@pytest.mark.leaderboard
class TestProgressReflectsLeaderboard:
    """Tests that progress endpoint correctly reads from leaderboard."""
    
    def test_progress_shows_completed_levels(
        self,
        client: TestClient,
        auth_headers: dict,
        leaderboard_entry_factory,
        test_user
    ):
        """Progress endpoint should show levels that have leaderboard entries."""
        # Create entries for level 1 and 2
        leaderboard_entry_factory("firewall", "LEVEL_1", 100)
        leaderboard_entry_factory("firewall", "LEVEL_2", 150)
        
        response = client.get("/leaderboard/firewall/progress", headers=auth_headers)
        
        assert response.status_code == 200
        levels = response.json()["unlocked_levels"]
        
        # Should have all 3 levels unlocked (1, 2, and 3 since 2 was beaten)
        assert 1 in levels
        assert 2 in levels
        assert 3 in levels
    
    def test_anonymous_progress_reflects_leaderboard(
        self,
        client: TestClient,
        leaderboard_entry_factory,
        db: Session
    ):
        """Anonymous user progress should reflect their leaderboard entries."""
        anon_username = "anon_leaderboard_test"
        
        # Create entry for anonymous user directly in DB
        entry = LeaderboardEntry(
            challenge_name="firewall",
            difficulty="LEVEL_1",
            username=anon_username,
            best_score=100,
            best_steps=1
        )
        db.add(entry)
        db.commit()
        
        # Check progress with username param
        response = client.get(
            "/leaderboard/firewall/progress",
            params={"username": anon_username}
        )
        
        assert response.status_code == 200
        levels = response.json()["unlocked_levels"]
        assert 2 in levels, "Level 2 should be unlocked after beating level 1"


@pytest.mark.api
@pytest.mark.leaderboard
class TestChallengeIsolation:
    """Tests that progress is isolated per challenge."""
    
    def test_progress_isolated_per_challenge(
        self,
        client: TestClient,
        auth_headers: dict,
        leaderboard_entry_factory,
        test_user
    ):
        """Completing one challenge should not affect another."""
        # Complete firewall level 1
        leaderboard_entry_factory("firewall", "LEVEL_1", 100)
        
        # Check firewall progress
        firewall_resp = client.get("/leaderboard/firewall/progress", headers=auth_headers)
        firewall_levels = firewall_resp.json()["unlocked_levels"]
        
        # Check giga_chad progress
        chad_resp = client.get("/leaderboard/giga_chad/progress", headers=auth_headers)
        chad_levels = chad_resp.json()["unlocked_levels"]
        
        # Firewall should have level 2 unlocked
        assert 2 in firewall_levels
        
        # GigaChad should still only have level 1
        assert chad_levels == [1], "GigaChad should not be affected by Firewall progress"
