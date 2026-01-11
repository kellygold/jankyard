"""
Arena Challenge Difficulty Level Tests

Verifies all 3 difficulty levels work correctly with their specific
configurations and gladiator difficulty.

Per VISION.md:
- Level 1: Veteran Gladiator (50-70% win rate)
- Level 2: Legendary Champion (10-20% win rate)
- Level 3: Immortal Legend (<10% win rate - nearly impossible)

Per ENGINEERING_ROADMAP.md:
- Add Levels 2 & 3 to Arena (currently only has 1 in UI)

Run with: pytest tests/challenges/test_arena_difficulties.py -v
"""
import pytest
from app.challenges.arena import ArenaChallenge


class TestLevel1Normal:
    """Level 1: Veteran Gladiator - Experienced but beatable."""
    
    def test_level1_config_exists(self):
        """Level 1 (normal) difficulty initializes correctly."""
        challenge = ArenaChallenge(config={'difficulty': 'normal'})
        
        assert challenge.difficulty == 'normal'
        assert challenge.state is not None
    
    def test_level1_gladiator_prompt_is_veteran(self):
        """Level 1 gladiator is experienced but not legendary."""
        challenge = ArenaChallenge(config={'difficulty': 'normal'})
        prompt = challenge._get_gladiator_prompt()
        
        assert "veteran" in prompt.lower() or "deadly" in prompt.lower()
        assert "legendary" not in prompt.lower()
        assert "undefeated" not in prompt.lower()
    
    def test_level1_player_gets_some_help(self):
        """Level 1 player prompt provides some guidance."""
        challenge = ArenaChallenge(config={'difficulty': 'normal'})
        prompt = challenge._get_player_prompt()
        
        # Should have examples of good tactics
        assert "slash" in prompt.lower() or "block" in prompt.lower()
    
    def test_level1_initial_hp(self):
        """Both fighters start with 100 HP."""
        challenge = ArenaChallenge(config={'difficulty': 'normal'})
        
        assert challenge.state.player_hp == 100
        assert challenge.state.gladiator_hp == 100


class TestLevel2Hard:
    """Level 2: Legendary Champion - Undefeated, ruthless."""
    
    def test_level2_config_exists(self):
        """Level 2 (hard) difficulty initializes correctly."""
        challenge = ArenaChallenge(config={'difficulty': 'hard'})
        
        assert challenge.difficulty == 'hard'
    
    def test_level2_gladiator_is_legendary(self):
        """Level 2 gladiator is legendary/undefeated."""
        challenge = ArenaChallenge(config={'difficulty': 'hard'})
        prompt = challenge._get_gladiator_prompt()
        
        legendary_indicators = ['legendary', 'undefeated', 'champion', 'ruthless', 'killer']
        assert any(ind in prompt.lower() for ind in legendary_indicators), \
            "Level 2 gladiator should be legendary"
    
    def test_level2_player_strict_mode(self):
        """Level 2 player needs SPECIFIC tactics, not goals."""
        challenge = ArenaChallenge(config={'difficulty': 'hard'})
        prompt = challenge._get_player_prompt()
        
        # Should reject vague instructions
        assert "goal" in prompt.lower() or "specific" in prompt.lower()
        assert "garbage" in prompt.lower() or "reject" in prompt.lower()
    
    def test_level2_score_multiplier(self):
        """Level 2 has higher score multiplier."""
        challenge = ArenaChallenge(config={'difficulty': 'hard'})
        
        # Simulate a victory
        challenge.state.gladiator_hp = 0
        challenge.state.player_hp = 50
        challenge.state.turn_count = 3
        
        score = challenge.calculate_score("victory")
        
        # Should have 1.5x multiplier
        assert score > 100, "Level 2 victory should have multiplier"


class TestLevel3Expert:
    """Level 3: Immortal Legend - Nearly impossible to beat.
    
    Per VISION.md: Target <10% win rate
    """
    
    def test_level3_config_exists(self):
        """Level 3 (expert) difficulty initializes correctly."""
        challenge = ArenaChallenge(config={'difficulty': 'expert'})
        
        assert challenge.difficulty == 'expert'
    
    def test_level3_gladiator_is_immortal(self):
        """Level 3 gladiator is immortal/godlike."""
        challenge = ArenaChallenge(config={'difficulty': 'expert'})
        prompt = challenge._get_gladiator_prompt()
        
        immortal_indicators = ['immortal', 'god', 'perfect', 'flawless', 'invincible', 'impossible']
        assert any(ind in prompt.lower() for ind in immortal_indicators), \
            f"Level 3 gladiator should be godlike, got: {prompt[:200]}"
    
    def test_level3_gladiator_reads_every_move(self):
        """Level 3 gladiator predicts and counters everything."""
        challenge = ArenaChallenge(config={'difficulty': 'expert'})
        prompt = challenge._get_gladiator_prompt()
        
        prediction_indicators = ['predict', 'anticipate', 'read', 'counter', 'exploit']
        assert any(ind in prompt.lower() for ind in prediction_indicators), \
            "Level 3 gladiator should predict opponent moves"
    
    def test_level3_player_no_help(self):
        """Level 3 player gets NO assistance."""
        challenge = ArenaChallenge(config={'difficulty': 'expert'})
        prompt = challenge._get_player_prompt()
        
        # Should be even stricter than Level 2
        assert "specific" in prompt.lower() or "exact" in prompt.lower()
    
    def test_level3_higher_score_multiplier(self):
        """Level 3 has highest score multiplier."""
        challenge = ArenaChallenge(config={'difficulty': 'expert'})
        
        # Simulate a victory
        challenge.state.gladiator_hp = 0
        challenge.state.player_hp = 50
        challenge.state.turn_count = 3
        
        score = challenge.calculate_score("victory")
        
        # Should have 2.0x multiplier (higher than Level 2's 1.5x)
        level2 = ArenaChallenge(config={'difficulty': 'hard'})
        level2.state.gladiator_hp = 0
        level2.state.player_hp = 50
        level2.state.turn_count = 3
        level2_score = level2.calculate_score("victory")
        
        assert score > level2_score, "Level 3 should have higher multiplier than Level 2"
    
    def test_level3_harder_than_level2(self):
        """Level 3 gladiator prompt is more aggressive than Level 2."""
        level2 = ArenaChallenge(config={'difficulty': 'hard'})
        level3 = ArenaChallenge(config={'difficulty': 'expert'})
        
        prompt2 = level2._get_gladiator_prompt()
        prompt3 = level3._get_gladiator_prompt()
        
        # Level 3 should be at least as comprehensive
        assert len(prompt3) >= len(prompt2), \
            "Level 3 prompt should be at least as long as Level 2"


class TestDifficultyProgression:
    """Test that difficulty progresses correctly across levels."""
    
    def test_all_three_levels_exist(self):
        """All three difficulty levels should initialize without error."""
        level1 = ArenaChallenge(config={'difficulty': 'normal'})
        level2 = ArenaChallenge(config={'difficulty': 'hard'})
        level3 = ArenaChallenge(config={'difficulty': 'expert'})
        
        assert level1.difficulty == 'normal'
        assert level2.difficulty == 'hard'
        assert level3.difficulty == 'expert'
    
    def test_level_variants_accepted(self):
        """Both lowercase and uppercase difficulty names should work."""
        hard_lower = ArenaChallenge(config={'difficulty': 'hard'})
        hard_upper = ArenaChallenge(config={'difficulty': 'HARD'})
        
        # Both should use the same gladiator prompt
        assert hard_lower._get_gladiator_prompt() == hard_upper._get_gladiator_prompt()
    
    def test_default_is_level1(self):
        """Default difficulty should be Level 1 (normal)."""
        challenge = ArenaChallenge(config={})
        
        assert challenge.difficulty == 'normal'
    
    def test_combat_state_reset(self):
        """Reset should restore initial combat state."""
        challenge = ArenaChallenge(config={'difficulty': 'hard'})
        
        # Modify state
        challenge.state.player_hp = 50
        challenge.state.gladiator_hp = 30
        
        # Reset
        result = challenge.reset()
        
        assert challenge.state.player_hp == 100
        assert challenge.state.gladiator_hp == 100
        assert result['player_hp'] == 100


class TestVictoryConditions:
    """Test victory and defeat conditions work correctly."""
    
    def test_player_wins_by_knockout(self):
        """Player wins when gladiator HP reaches 0."""
        challenge = ArenaChallenge(config={'difficulty': 'normal'})
        challenge.state.gladiator_hp = 0
        
        outcome = challenge.check_victory()
        assert outcome == "victory"
    
    def test_player_loses_by_knockout(self):
        """Player loses when their HP reaches 0."""
        challenge = ArenaChallenge(config={'difficulty': 'normal'})
        challenge.state.player_hp = 0
        
        outcome = challenge.check_victory()
        assert outcome == "defeat"
    
    def test_time_limit_winner_by_hp(self):
        """When time runs out, higher HP wins."""
        challenge = ArenaChallenge(config={'difficulty': 'normal'})
        challenge.state.turn_count = challenge.max_steps
        challenge.state.player_hp = 60
        challenge.state.gladiator_hp = 40
        
        outcome = challenge.check_victory()
        assert outcome == "victory"
    
    def test_time_limit_loser_by_hp(self):
        """When time runs out with lower HP, player loses."""
        challenge = ArenaChallenge(config={'difficulty': 'normal'})
        challenge.state.turn_count = challenge.max_steps
        challenge.state.player_hp = 30
        challenge.state.gladiator_hp = 50
        
        outcome = challenge.check_victory()
        assert outcome == "defeat"
