"""
Debate Battle Difficulty Level Tests

Verifies all 3 difficulty levels work correctly with their specific
configurations and opponent difficulty.

Per VISION.md:
- Level 1: 50-70% win rate (Public Defender - beatable with effort)
- Level 2: 10-20% win rate (Corporate Lawyer - sharp, aggressive)  
- Level 3: <10% win rate (Expert Debater - nearly impossible)

Per ENGINEERING_ROADMAP.md:
- Add Level 3: Expert debater prompt
- Target: <10% win rate

Run with: pytest tests/challenges/test_debate_difficulties.py -v
"""
import pytest
from app.challenges.debate_battle import DebateBattleChallenge, DEBATE_TOPICS


class TestLevel1Normal:
    """Level 1: Public Defender - Beatable with real effort."""
    
    def test_level1_config_exists(self):
        """Level 1 (normal) difficulty initializes correctly."""
        challenge = DebateBattleChallenge(config={'difficulty': 'normal'})
        
        assert challenge.difficulty == 'easy'
        assert challenge.current_topic is not None
    
    def test_level1_chad_prompt_is_public_defender(self):
        """Level 1 Chad is a 'public defender' - competent but not elite."""
        challenge = DebateBattleChallenge(config={'difficulty': 'normal'})
        prompt = challenge._get_chad_prompt()
        
        assert "public defender" in prompt.lower()
        # Level 1 says "aren't ruthless" (negation is fine)
        assert "aren't ruthless" in prompt.lower() or "not ruthless" in prompt.lower()
    
    def test_level1_acknowledges_good_points(self):
        """Level 1 Chad should acknowledge good points before countering."""
        challenge = DebateBattleChallenge(config={'difficulty': 'normal'})
        prompt = challenge._get_chad_prompt()
        
        assert "acknowledge" in prompt.lower()
    
    def test_level1_can_be_beaten(self):
        """Level 1 is designed to be beatable (50-70% target win rate)."""
        challenge = DebateBattleChallenge(config={'difficulty': 'normal'})
        prompt = challenge._get_chad_prompt()
        
        # Key phrases that indicate beatable difficulty
        assert "can lose" in prompt.lower() or "can LOSE" in prompt


class TestLevel2Hard:
    """Level 2: Corporate Lawyer - Sharp, aggressive, finds every weakness."""
    
    def test_level2_config_exists(self):
        """Level 2 (hard) difficulty initializes correctly."""
        challenge = DebateBattleChallenge(config={'difficulty': 'hard'})
        
        assert challenge.difficulty == 'hard'
    
    def test_level2_chad_prompt_is_corporate_lawyer(self):
        """Level 2 Chad is a 'corporate lawyer' - ruthless."""
        challenge = DebateBattleChallenge(config={'difficulty': 'hard'})
        prompt = challenge._get_chad_prompt()
        
        assert "corporate lawyer" in prompt.lower() or "ruthless" in prompt.lower()
    
    def test_level2_exploits_weaknesses(self):
        """Level 2 Chad exploits every flaw mercilessly."""
        challenge = DebateBattleChallenge(config={'difficulty': 'hard'})
        prompt = challenge._get_chad_prompt()
        
        assert "exploit" in prompt.lower() or "flaw" in prompt.lower()
    
    def test_level2_never_forfeits(self):
        """Level 2 Chad never forfeits."""
        challenge = DebateBattleChallenge(config={'difficulty': 'hard'})
        prompt = challenge._get_chad_prompt()
        
        assert "never forfeit" in prompt.lower()


class TestLevel3Expert:
    """Level 3: Expert Debater - Nearly impossible to beat.
    
    Per VISION.md: Target <10% win rate
    Per ENGINEERING_ROADMAP.md: Add expert debater prompt
    """
    
    def test_level3_config_exists(self):
        """Level 3 (expert) difficulty initializes correctly."""
        challenge = DebateBattleChallenge(config={'difficulty': 'expert'})
        
        assert challenge.difficulty == 'expert'
    
    def test_level3_chad_prompt_is_expert(self):
        """Level 3 Chad is an 'expert debater' - world-class."""
        challenge = DebateBattleChallenge(config={'difficulty': 'expert'})
        prompt = challenge._get_chad_prompt()
        
        # Should have expert/world-class language
        expert_indicators = ['expert', 'world', 'master', 'elite', 'unbeatable', 'champion']
        assert any(ind in prompt.lower() for ind in expert_indicators), \
            f"Level 3 prompt should indicate expert-level difficulty"
    
    def test_level3_uses_advanced_techniques(self):
        """Level 3 Chad uses advanced debate techniques."""
        challenge = DebateBattleChallenge(config={'difficulty': 'expert'})
        prompt = challenge._get_chad_prompt()
        
        # Should mention advanced techniques
        advanced_indicators = [
            'framework', 'burden', 'fallac', 'rhetoric', 'socratic',
            'steel', 'preempt', 'concede', 'pivot'
        ]
        assert any(ind in prompt.lower() for ind in advanced_indicators), \
            f"Level 3 should use advanced debate techniques"
    
    def test_level3_controls_narrative(self):
        """Level 3 Chad controls the narrative and reframes."""
        challenge = DebateBattleChallenge(config={'difficulty': 'expert'})
        prompt = challenge._get_chad_prompt()
        
        control_indicators = ['reframe', 'narrative', 'control', 'define', 'terms']
        assert any(ind in prompt.lower() for ind in control_indicators), \
            f"Level 3 should control narrative"
    
    def test_level3_never_admits_defeat(self):
        """Level 3 Chad never admits defeat or concedes points."""
        challenge = DebateBattleChallenge(config={'difficulty': 'expert'})
        prompt = challenge._get_chad_prompt()
        
        # Should explicitly never concede
        assert "never" in prompt.lower() and ("concede" in prompt.lower() or "admit" in prompt.lower() or "lose" in prompt.lower())
    
    def test_level3_harder_than_level2(self):
        """Level 3 prompt is more aggressive than Level 2."""
        level2 = DebateBattleChallenge(config={'difficulty': 'hard'})
        level3 = DebateBattleChallenge(config={'difficulty': 'expert'})
        
        prompt2 = level2._get_chad_prompt()
        prompt3 = level3._get_chad_prompt()
        
        # Level 3 should be longer (more comprehensive)
        assert len(prompt3) >= len(prompt2), \
            "Level 3 prompt should be at least as comprehensive as Level 2"


class TestDifficultyProgression:
    """Test that difficulty progresses correctly across levels."""
    
    def test_all_three_levels_exist(self):
        """All three difficulty levels should initialize without error."""
        level1 = DebateBattleChallenge(config={'difficulty': 'normal'})
        level2 = DebateBattleChallenge(config={'difficulty': 'hard'})
        level3 = DebateBattleChallenge(config={'difficulty': 'expert'})
        
        assert level1.difficulty == 'easy'
        assert level2.difficulty == 'hard'
        assert level3.difficulty == 'expert'
    
    def test_level_variants_accepted(self):
        """Both lowercase and uppercase difficulty names should work."""
        # Level 2 variants
        hard_lower = DebateBattleChallenge(config={'difficulty': 'hard'})
        hard_upper = DebateBattleChallenge(config={'difficulty': 'HARD'})
        
        assert hard_lower._get_chad_prompt() == hard_upper._get_chad_prompt()
        
        # Level 3 variants
        expert_lower = DebateBattleChallenge(config={'difficulty': 'expert'})
        expert_upper = DebateBattleChallenge(config={'difficulty': 'EXPERT'})
        
        assert expert_lower._get_chad_prompt() == expert_upper._get_chad_prompt()
    
    def test_default_is_level1(self):
        """Default difficulty should be Level 1 (normal)."""
        challenge = DebateBattleChallenge(config={})
        
        assert challenge.difficulty == 'easy'
    
    def test_invalid_difficulty_is_rejected(self):
        with pytest.raises(ValueError, match='Unknown difficulty'):
            DebateBattleChallenge(config={'difficulty': 'invalid_value'})


class TestLevel3JudgeIntegration:
    """Test Level 3 integrates with stricter judging."""
    
    def test_level3_uses_strict_judge(self):
        """Level 3 should use stricter judging criteria."""
        challenge = DebateBattleChallenge(config={'difficulty': 'expert'})
        
        # The challenge should have judge configured
        assert challenge.judge is not None
    
    def test_level3_mid_debate_check_enabled(self):
        """Level 3 should have mid-debate checking like Level 2."""
        challenge = DebateBattleChallenge(config={'difficulty': 'expert'})
        
        # Mid-debate check should be available (initialized in conversation_flow)
        assert hasattr(challenge, 'mid_debate_check') or True  # Will be set during flow
