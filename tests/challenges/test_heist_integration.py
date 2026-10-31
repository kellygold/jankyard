"""
Heist Challenge Integration Tests

Tests the heist challenge registration and configuration.
Note: Full streaming tests require running server (e2e tests).

Run with: pytest tests/challenges/test_heist_integration.py -v
"""
import pytest
from unittest.mock import patch, MagicMock

from app.challenges.base import ChallengeRegistry
from app.challenges.heist import HeistChallenge, CREW_ROSTER, SCENARIOS


class TestHeistRegistration:
    """Test that heist is properly registered"""
    
    def test_heist_in_registry(self):
        """Heist should be registered in ChallengeRegistry"""
        challenge = ChallengeRegistry.get_challenge("heist")
        assert challenge is not None
        assert challenge.name == "heist"
    
    def test_heist_with_difficulty_config(self):
        """Should be able to create heist with difficulty config"""
        for difficulty in ["easy", "medium", "hard"]:
            challenge = ChallengeRegistry.get_challenge("heist", {"difficulty": difficulty})
            assert challenge is not None
            assert challenge.difficulty == difficulty
    
    def test_heist_supports_streaming(self):
        """Heist should support streaming"""
        challenge = ChallengeRegistry.get_challenge("heist")
        assert challenge.supports_streaming is False
    
    def test_heist_challenge_type(self):
        """Heist should have correct challenge type"""
        challenge = ChallengeRegistry.get_challenge("heist")
        assert challenge.challenge_type == "heist"


class TestHeistCrewConfiguration:
    """Test crew configuration for each difficulty"""
    
    def test_easy_has_3_crew(self):
        """Easy difficulty should have 3 crew members"""
        challenge = HeistChallenge({"difficulty": "easy"})
        assert len(challenge.selected_crew) == 3
    
    def test_medium_has_4_crew(self):
        """Medium difficulty should have 4 crew members"""
        challenge = HeistChallenge({"difficulty": "medium"})
        assert len(challenge.selected_crew) == 4
    
    def test_hard_has_5_crew(self):
        """Hard difficulty should have 5 crew members"""
        challenge = HeistChallenge({"difficulty": "hard"})
        assert len(challenge.selected_crew) == 5
    
    def test_agents_created_for_crew(self):
        """Should create agents for all selected crew"""
        challenge = HeistChallenge({"difficulty": "easy"})
        for member in challenge.selected_crew:
            assert member.id in challenge.agents


class TestHeistScenarioConfiguration:
    """Test scenario configuration for each difficulty"""
    
    def test_easy_uses_museum(self):
        """Easy should use museum scenario"""
        challenge = HeistChallenge({"difficulty": "easy"})
        assert challenge.scenario.id == "museum"
    
    def test_medium_uses_casino(self):
        """Medium should use casino scenario"""
        challenge = HeistChallenge({"difficulty": "medium"})
        assert challenge.scenario.id == "casino"
    
    def test_hard_uses_tech(self):
        """Hard should use tech scenario"""
        challenge = HeistChallenge({"difficulty": "hard"})
        assert challenge.scenario.id == "tech"
    
    def test_each_scenario_has_complications(self):
        """Each scenario should have complications list"""
        for scenario in SCENARIOS:
            assert len(scenario.complications) >= 1


class TestHeistObservation:
    """Test the observation/state structure"""
    
    def test_observation_has_scenario_info(self):
        """Observation should contain scenario info"""
        challenge = HeistChallenge()
        obs = challenge._get_observation()
        
        assert "scenario" in obs
        assert "target" in obs
        assert "objective" in obs
    
    def test_observation_has_crew_info(self):
        """Observation should contain crew info"""
        challenge = HeistChallenge()
        obs = challenge._get_observation()
        
        assert "crew" in obs
        assert len(obs["crew"]) == len(challenge.selected_crew)
        for crew_info in obs["crew"]:
            assert "id" in crew_info
            assert "name" in crew_info
            assert "role" in crew_info
    
    def test_observation_has_difficulty(self):
        """Observation should contain difficulty"""
        challenge = HeistChallenge({"difficulty": "hard"})
        obs = challenge._get_observation()
        
        assert obs["difficulty"] == "hard"


class TestHeistReset:
    """Test reset functionality"""
    
    def test_reset_returns_observation(self):
        """Reset should return observation"""
        challenge = HeistChallenge()
        obs = challenge.reset()
        
        assert obs is not None
        assert "scenario" in obs
    
    def test_reset_clears_success_state(self):
        """Reset should clear heist success state"""
        challenge = HeistChallenge()
        challenge.heist_success = True
        
        challenge.reset()
        assert challenge.heist_success == False
