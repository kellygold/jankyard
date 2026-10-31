"""
Heist Challenge Tests

Tests for the multi-agent heist challenge including:
1. Challenge initialization and configuration
2. Crew member loading
3. Scenario selection by difficulty
4. Conversation flow basics

Run with: pytest tests/challenges/test_heist.py -v
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from typing import List

from app.challenges.heist import (
    HeistChallenge,
    CrewMember,
    HeistScenario,
    CREW_ROSTER,
    SCENARIOS,
)
from app.challenges.agents import Agent, ConversationTurn


class TestCrewRoster:
    """Test crew member definitions"""
    
    def test_crew_roster_not_empty(self):
        """Should have at least 3 crew members"""
        assert len(CREW_ROSTER) >= 3
    
    def test_all_crew_have_required_fields(self):
        """Each crew member should have all required fields"""
        for member in CREW_ROSTER:
            assert member.id, f"Missing id for crew member"
            assert member.name, f"Missing name for {member.id}"
            assert member.role, f"Missing role for {member.id}"
            assert member.specialty, f"Missing specialty for {member.id}"
            assert member.quirk, f"Missing quirk for {member.id}"
            assert member.system_prompt, f"Missing system_prompt for {member.id}"
            assert member.icon, f"Missing icon for {member.id}"
    
    def test_crew_ids_unique(self):
        """All crew member IDs should be unique"""
        ids = [m.id for m in CREW_ROSTER]
        assert len(ids) == len(set(ids)), "Duplicate crew member IDs found"
    
    def test_expected_crew_present(self):
        """Core crew members should be present"""
        ids = [m.id for m in CREW_ROSTER]
        assert "hacker" in ids
        assert "muscle" in ids
        assert "face" in ids


class TestScenarios:
    """Test heist scenario definitions"""
    
    def test_scenarios_not_empty(self):
        """Should have at least 3 scenarios"""
        assert len(SCENARIOS) >= 3
    
    def test_all_scenarios_have_required_fields(self):
        """Each scenario should have all required fields"""
        for scenario in SCENARIOS:
            assert scenario.id, "Missing id"
            assert scenario.name, f"Missing name for {scenario.id}"
            assert scenario.target, f"Missing target for {scenario.id}"
            assert scenario.objective, f"Missing objective for {scenario.id}"
            assert scenario.security, f"Missing security for {scenario.id}"
            assert scenario.complications, f"Missing complications for {scenario.id}"
            assert scenario.difficulty in ["easy", "medium", "hard"]
    
    def test_each_difficulty_has_scenario(self):
        """Should have scenarios for each difficulty level"""
        difficulties = [s.difficulty for s in SCENARIOS]
        assert "easy" in difficulties
        assert "medium" in difficulties
        assert "hard" in difficulties


class TestHeistChallengeInit:
    """Test challenge initialization"""
    
    def test_default_initialization(self):
        """Should initialize with default (easy) difficulty"""
        challenge = HeistChallenge()
        assert challenge.difficulty == "easy"
        assert challenge.scenario.id == "museum"
        assert len(challenge.selected_crew) == 3
    
    def test_easy_difficulty(self):
        """Easy difficulty should have 3 crew members"""
        challenge = HeistChallenge({"difficulty": "easy"})
        assert len(challenge.selected_crew) == 3
        assert challenge.scenario.difficulty == "easy"
    
    def test_medium_difficulty(self):
        """Medium difficulty should have 4 crew members"""
        challenge = HeistChallenge({"difficulty": "medium"})
        assert len(challenge.selected_crew) == 4
        assert challenge.scenario.difficulty == "medium"
    
    def test_hard_difficulty(self):
        """Hard difficulty should have 5 crew members"""
        challenge = HeistChallenge({"difficulty": "hard"})
        assert len(challenge.selected_crew) == 5
        assert challenge.scenario.difficulty == "hard"
    
    def test_agents_initialized(self):
        """Should create agents for all selected crew"""
        challenge = HeistChallenge()
        assert len(challenge.agents) == len(challenge.selected_crew)
        for member in challenge.selected_crew:
            assert member.id in challenge.agents
            assert isinstance(challenge.agents[member.id], Agent)


class TestHeistChallengeProperties:
    """Test challenge properties"""
    
    def test_name(self):
        challenge = HeistChallenge()
        assert challenge.name == "heist"
    
    def test_display_name(self):
        challenge = HeistChallenge()
        assert "Heist" in challenge.display_name
    
    def test_description(self):
        challenge = HeistChallenge()
        assert len(challenge.description) > 20
    
    def test_supports_streaming(self):
        challenge = HeistChallenge()
        assert challenge.supports_streaming is False
    
    def test_challenge_type(self):
        challenge = HeistChallenge()
        assert challenge.challenge_type == "heist"


class TestHeistObservation:
    """Test observation/state retrieval"""
    
    def test_get_observation_structure(self):
        """Observation should contain expected fields"""
        challenge = HeistChallenge()
        obs = challenge._get_observation()
        
        assert "scenario" in obs
        assert "target" in obs
        assert "objective" in obs
        assert "security" in obs
        assert "crew" in obs
        assert "difficulty" in obs
    
    def test_crew_in_observation(self):
        """Crew info should be in observation"""
        challenge = HeistChallenge()
        obs = challenge._get_observation()
        
        assert len(obs["crew"]) == len(challenge.selected_crew)
        for crew_info in obs["crew"]:
            assert "id" in crew_info
            assert "name" in crew_info
            assert "role" in crew_info
            assert "icon" in crew_info


class TestHeistReset:
    """Test reset functionality"""
    
    def test_reset_returns_observation(self):
        """Reset should return observation"""
        challenge = HeistChallenge()
        obs = challenge.reset()
        
        assert obs is not None
        assert "scenario" in obs
    
    def test_reset_clears_state(self):
        """Reset should clear game state"""
        challenge = HeistChallenge()
        challenge.phase = "execution"
        challenge.heist_success = True
        
        challenge.reset()
        
        assert challenge.phase == "planning"
        assert challenge.heist_success == False






class TestDifficultyProgression:
    """Test that difficulty affects the challenge"""
    
    def test_harder_levels_have_more_crew(self):
        """Higher difficulties should have more crew to coordinate"""
        easy = HeistChallenge({"difficulty": "easy"})
        medium = HeistChallenge({"difficulty": "medium"})
        hard = HeistChallenge({"difficulty": "hard"})
        
        assert len(easy.selected_crew) < len(medium.selected_crew)
        assert len(medium.selected_crew) < len(hard.selected_crew)
    
    def test_harder_levels_have_different_scenarios(self):
        """Each difficulty should have unique scenario"""
        easy = HeistChallenge({"difficulty": "easy"})
        medium = HeistChallenge({"difficulty": "medium"})
        hard = HeistChallenge({"difficulty": "hard"})
        
        scenarios = {easy.scenario.id, medium.scenario.id, hard.scenario.id}
        assert len(scenarios) == 3  # All different


class TestExtensibility:
    """Test that new crew members can be added easily"""
    
    def test_crew_member_dataclass_works(self):
        """Should be able to create new crew members"""
        new_member = CrewMember(
            id="demo_expert",
            name="Boom",
            role="Demolitions",
            specialty="Blowing stuff up",
            personality="Eager",
            quirk="Too eager with explosives",
            system_prompt="You are Boom, a demolitions expert.",
            icon="💥"
        )
        
        assert new_member.id == "demo_expert"
        assert new_member.name == "Boom"
        assert new_member.icon == "💥"
    
    def test_scenario_dataclass_works(self):
        """Should be able to create new scenarios"""
        new_scenario = HeistScenario(
            id="bank",
            name="The Bank Job",
            target="First National Bank",
            objective="Empty the vault",
            security="Armed guards, vault, cameras",
            complications=["Silent alarm triggered"],
            difficulty="medium"
        )
        
        assert new_scenario.id == "bank"
        assert new_scenario.name == "The Bank Job"
