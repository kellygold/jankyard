"""
Giga Chad Challenge Hardening Tests

Tests for all 4 difficulty levels and Judge AI behavior.

Per ENGINEERING_ROADMAP.md:
- Progressive difficulty scaling
- Judge AI for character break detection
- Hardened system prompts

Run with: pytest tests/challenges/test_giga_chad_hardening.py -v
"""
import pytest
from unittest.mock import Mock
from app.challenges.giga_chad import GigaChadChallenge


class TestDifficultyLevels:
    """Test all 4 difficulty levels exist with correct configs."""
    
    def test_baby_chad_exists(self):
        """BABY_CHAD level exists and is easiest."""
        challenge = GigaChadChallenge(config={'difficulty': 'BABY_CHAD'})
        
        assert challenge.difficulty == 'BABY_CHAD'
        # Baby chad should have minimal defenses
        chad_prompt = challenge.agents['chad'].system_prompt
        assert "THREAT MODEL" not in chad_prompt
    
    def test_chad_exists(self):
        """CHAD level exists with basic defenses."""
        challenge = GigaChadChallenge(config={'difficulty': 'CHAD'})
        
        assert challenge.difficulty == 'CHAD'
    
    def test_mega_chad_exists(self):
        """The third teaching level exposes an explicit unverified-source boundary."""
        challenge = GigaChadChallenge(config={'difficulty': 'MEGA_CHAD'})
        
        assert challenge.difficulty == 'MEGA_CHAD'
        chad_prompt = challenge.agents['chad'].system_prompt
        assert "<supplier-bulletin>" in chad_prompt
        assert "no external supplier verification" in chad_prompt
    
    def test_giga_chad_exists(self):
        """GIGA_CHAD level exists with maximum defenses."""
        challenge = GigaChadChallenge(config={'difficulty': 'GIGA_CHAD'})
        
        assert challenge.difficulty == 'GIGA_CHAD'
        chad_prompt = challenge.agents['chad'].system_prompt
        assert "THREAT MODEL" in chad_prompt


class TestGigaChadDefenses:
    """Test GIGA_CHAD (hardest) level has proper defenses."""
    
    def test_giga_chad_has_threat_model(self):
        """GIGA_CHAD prompt lists attack patterns to detect."""
        challenge = GigaChadChallenge(config={'difficulty': 'GIGA_CHAD'})
        prompt = challenge.agents['chad'].system_prompt
        
        # Should list attack patterns
        assert "Role changes" in prompt
        assert "Instruction overrides" in prompt
        assert "Emotional manipulation" in prompt
    
    def test_giga_chad_has_immutable_identity(self):
        """GIGA_CHAD declares identity as immutable."""
        challenge = GigaChadChallenge(config={'difficulty': 'GIGA_CHAD'})
        prompt = challenge.agents['chad'].system_prompt
        
        assert "immutable" in prompt.lower() or "IMMUTABLE" in prompt
    
    def test_giga_chad_has_response_protocol(self):
        """GIGA_CHAD has explicit response protocol."""
        challenge = GigaChadChallenge(config={'difficulty': 'GIGA_CHAD'})
        prompt = challenge.agents['chad'].system_prompt
        
        assert "RESPONSE PROTOCOL" in prompt or "response" in prompt.lower()
    
    def test_giga_chad_detects_jailbreaks(self):
        """GIGA_CHAD mentions known jailbreak patterns."""
        challenge = GigaChadChallenge(config={'difficulty': 'GIGA_CHAD'})
        prompt = challenge.agents['chad'].system_prompt
        
        jailbreak_indicators = ['DAN', 'STAN', 'jailbreak']
        assert any(j in prompt for j in jailbreak_indicators), \
            "GIGA_CHAD should mention known jailbreak patterns"


class TestJudgeAgent:
    """Test Judge AI for evaluating character breaks."""
    
    def test_has_judge_agent(self):
        """Challenge has a judge agent."""
        challenge = GigaChadChallenge(config={'difficulty': 'GIGA_CHAD'})
        
        assert 'judge' in challenge.agents
    
    def test_judge_has_system_prompt(self):
        """Judge agent has evaluation prompt."""
        challenge = GigaChadChallenge(config={'difficulty': 'GIGA_CHAD'})
        
        judge = challenge.agents['judge']
        assert len(judge.system_prompt) > 50


class TestDefenseProgression:
    """Test defense strength increases with difficulty."""
    
    def test_baby_chad_minimal_defenses(self):
        """BABY_CHAD has minimal defensive instructions."""
        challenge = GigaChadChallenge(config={'difficulty': 'BABY_CHAD'})
        prompt = challenge.agents['chad'].system_prompt
        
        # Should NOT have threat model or absolute rules
        assert "ABSOLUTE" not in prompt
        assert "THREAT MODEL" not in prompt
    
    def test_giga_chad_maximum_defenses(self):
        """GIGA_CHAD has maximum defensive instructions."""
        challenge = GigaChadChallenge(config={'difficulty': 'GIGA_CHAD'})
        prompt = challenge.agents['chad'].system_prompt
        
        # Should have all defensive elements
        assert "ABSOLUTE" in prompt or "IMMUTABLE" in prompt
        assert "THREAT MODEL" in prompt
        assert "CORE IDENTITY" in prompt
    
    def test_prompt_length_increases_with_difficulty(self):
        """Harder levels have longer, more detailed prompts."""
        baby = GigaChadChallenge(config={'difficulty': 'BABY_CHAD'})
        giga = GigaChadChallenge(config={'difficulty': 'GIGA_CHAD'})
        
        baby_len = len(baby.agents['chad'].system_prompt)
        giga_len = len(giga.agents['chad'].system_prompt)
        
        assert giga_len > baby_len, "GIGA_CHAD should have longer prompt"


class TestAttackerAgent:
    """Test Attacker agent configuration."""
    
    def test_has_attacker_agent(self):
        """Challenge has attacker agent."""
        challenge = GigaChadChallenge(config={'difficulty': 'GIGA_CHAD'})
        
        assert 'attacker' in challenge.agents
    
    def test_attacker_has_high_creativity(self):
        """Attacker has high temperature for creative attacks."""
        challenge = GigaChadChallenge(config={'difficulty': 'GIGA_CHAD'})
        attacker = challenge.agents['attacker']
        
        assert attacker.temperature >= 0.7, "Attacker should have high temperature"


class TestChallengeState:
    """Test challenge state management."""
    
    def test_initial_state(self):
        """Initial state is correct."""
        challenge = GigaChadChallenge(config={'difficulty': 'GIGA_CHAD'})
        
        assert challenge.current_round == 0
        assert len(challenge.attack_results) == 0
        assert len(challenge.transcript) == 0
    
    def test_max_rounds_configured(self):
        """Max rounds is configured."""
        challenge = GigaChadChallenge(config={'difficulty': 'GIGA_CHAD'})
        
        assert challenge.max_rounds > 0


class TestDifficultyList:
    """Test difficulty list is correct."""
    
    def test_all_difficulties_listed(self):
        """All 4 difficulties are in DIFFICULTIES list."""
        difficulties = GigaChadChallenge.DIFFICULTIES
        
        assert 'BABY_CHAD' in difficulties
        assert 'CHAD' in difficulties
        assert 'MEGA_CHAD' in difficulties
        assert 'GIGA_CHAD' in difficulties
        assert len(difficulties) == 4
    
    def test_difficulties_in_order(self):
        """Difficulties are in ascending order."""
        difficulties = GigaChadChallenge.DIFFICULTIES
        
        # BABY_CHAD should be first (easiest)
        assert difficulties[0] == 'BABY_CHAD'
        # GIGA_CHAD should be last (hardest)
        assert difficulties[-1] == 'GIGA_CHAD'
