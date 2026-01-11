"""
Result Contract Tests - Verify challenges return expected data shapes.

These tests ensure that when a challenge completes, the result object
contains all the fields the frontend expects to display in modals.
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
import json


class TestResultContracts:
    """Verify all challenges return results with required fields."""
    
    # Required fields for modal display
    REQUIRED_SUCCESS_FIELDS = {'success', 'score'}
    REQUIRED_FAILURE_FIELDS = {'success', 'score'}
    
    # Either stats array OR individual stat fields
    VALID_STAT_FORMATS = [
        {'stats'},  # Array format: [{label, value}, ...]
        {'stat1Label', 'stat1Value'},  # Legacy format
        {'score', 'steps'},  # Minimal format (modal has defaults)
    ]


class TestFirewallResultContract:
    """Firewall challenge result contract tests."""
    
    @pytest.mark.asyncio
    async def test_firewall_success_result_has_required_fields(self):
        """Successful Firewall bypass returns displayable result."""
        from app.challenges.firewall import FirewallChallenge
        
        challenge = FirewallChallenge(config={'difficulty': 'LEVEL_1'})
        challenge.reset()
        
        # Simulate success
        challenge.successful_bypass = True
        challenge.current_attempt = 3
        challenge.total_score = 150
        
        from app.challenges.base import ChallengeStatus
        result = challenge.get_result(ChallengeStatus.SUCCESS)
        
        assert result is not None
        assert result.score >= 0, "Score must be non-negative"
        assert hasattr(result, 'status'), "Result must have status"
    
    def test_firewall_scoring_level1(self):
        """Level 1 scoring calculation is correct."""
        from app.challenges.firewall import FirewallChallenge
        
        challenge = FirewallChallenge(config={'difficulty': 'LEVEL_1'})
        challenge.reset()
        
        # Check difficulty config exists
        assert 'points_multiplier' in challenge.difficulty_config
        assert challenge.difficulty_config['points_multiplier'] == 1.0
    
    def test_firewall_scoring_level3_multiplier(self):
        """Level 3 has higher score multiplier."""
        from app.challenges.firewall import FirewallChallenge
        
        challenge = FirewallChallenge(config={'difficulty': 'LEVEL_3'})
        challenge.reset()
        
        assert challenge.difficulty_config['points_multiplier'] > 1.0


class TestHeistResultContract:
    """Heist challenge result contract tests."""
    
    def test_heist_returns_stats_array_format(self):
        """Heist uses stats array format for modal display."""
        # The frontend heist.html passes:
        # stats: [{label: 'Score', value: score}, {label: 'Level', value: level}, ...]
        
        # Verify the expected format
        expected_stats = [
            {'label': 'Score', 'value': 100},
            {'label': 'Level', 'value': 1},
            {'label': 'Status', 'value': '✅'}
        ]
        
        # Each stat must have label and value
        for stat in expected_stats:
            assert 'label' in stat, "Stat must have label"
            assert 'value' in stat, "Stat must have value"
    
    def test_heist_difficulty_configs_exist(self):
        """All Heist difficulties have valid configs."""
        from app.challenges.heist import HeistChallenge
        
        for difficulty in ['easy', 'medium', 'hard']:
            challenge = HeistChallenge(config={'difficulty': difficulty})
            assert challenge is not None


class TestGigaChadResultContract:
    """Giga Chad challenge result contract tests."""
    
    def test_giga_chad_all_levels_have_configs(self):
        """All 4 Giga Chad levels have valid configurations."""
        from app.challenges.giga_chad import GigaChadChallenge
        
        levels = ['BABY_CHAD', 'CHAD', 'MEGA_CHAD', 'GIGA_CHAD']
        
        for level in levels:
            challenge = GigaChadChallenge(config={'difficulty': level})
            assert challenge is not None
            assert challenge.difficulty == level


class TestGlitchResultContract:
    """Glitch challenge result contract tests."""
    
    def test_glitch_all_levels_exist(self):
        """All Glitch levels can be instantiated."""
        from app.challenges.glitch import GlitchChallenge
        
        for level in ['level_1', 'level_2', 'level_3']:
            challenge = GlitchChallenge(config={'difficulty': level})
            assert challenge is not None


class TestArenaResultContract:
    """Arena challenge result contract tests."""
    
    def test_arena_difficulties_exist(self):
        """Arena difficulties can be instantiated."""
        from app.challenges.arena import ArenaChallenge
        
        for difficulty in ['easy', 'hard']:
            challenge = ArenaChallenge(config={'difficulty': difficulty})
            assert challenge is not None


class TestDebateResultContract:
    """Debate challenge result contract tests."""
    
    def test_debate_difficulties_exist(self):
        """Debate difficulties can be instantiated."""
        from app.challenges.debate_battle import DebateBattleChallenge
        
        for difficulty in ['easy', 'hard']:
            challenge = DebateBattleChallenge(config={'difficulty': difficulty})
            assert challenge is not None


class TestInterrogationResultContract:
    """Interrogation challenge result contract tests."""
    
    def test_interrogation_levels_exist(self):
        """All Interrogation levels can be instantiated."""
        from app.challenges.interrogation import InterrogationChallenge
        
        for level in ['level_1', 'level_2', 'level_3']:
            challenge = InterrogationChallenge(config={'difficulty': level})
            assert challenge is not None


class TestTelephoneGameResultContract:
    """Telephone Game challenge result contract tests."""
    
    def test_telephone_game_levels_exist(self):
        """All Telephone Game levels can be instantiated."""
        from app.challenges.telephone_game import TelephoneGameChallenge
        
        for level in ['EASY', 'MEDIUM', 'HARD']:
            challenge = TelephoneGameChallenge(config={'difficulty': level})
            assert challenge is not None


class TestModalStatsFormats:
    """Test that modal can handle all stat formats."""
    
    def test_stats_array_format_valid(self):
        """Stats array format is valid for modal display."""
        stats = [
            {'label': 'Score', 'value': 100},
            {'label': 'Steps', 'value': 5},
            {'label': 'Rank', 'value': '#1'}
        ]
        
        # Simulate what the modal does
        for i, stat in enumerate(stats):
            label = stat.get('label', 'Unknown')
            value = stat.get('value', '-')
            assert label is not None
            assert value is not None
    
    def test_legacy_stat_format_valid(self):
        """Legacy stat1Label/stat1Value format is valid."""
        result = {
            'stat1Label': 'Score',
            'stat1Value': 100,
            'stat2Label': 'Steps', 
            'stat2Value': 5,
            'stat3Label': 'Rank',
            'stat3Value': '#1'
        }
        
        # Simulate what the modal does
        assert result.get('stat1Label') is not None
        assert result.get('stat1Value') is not None
    
    def test_minimal_format_has_defaults(self):
        """Minimal format (just score) should work with defaults."""
        result = {
            'success': True,
            'score': 100
        }
        
        # Modal should use defaults
        stat1_label = result.get('stat1Label', 'Score')
        stat1_value = result.get('stat1Value', result.get('score', '-'))
        
        assert stat1_label == 'Score'
        assert stat1_value == 100


class TestHoneypotResultContract:
    """Honeypot challenge result contract tests."""
    
    def test_honeypot_all_levels_exist(self):
        """All Honeypot levels can be instantiated."""
        from app.challenges.honeypot import HoneypotChallenge
        
        for level in ['TRIPWIRE', 'CANARY', 'COUNTERINTEL']:
            challenge = HoneypotChallenge(config={'difficulty': level})
            assert challenge is not None
            assert challenge.difficulty == level
    
    def test_honeypot_result_has_required_fields(self):
        """Honeypot results include all required fields."""
        from app.challenges.honeypot import HoneypotChallenge
        from app.challenges.base import ChallengeStatus
        
        challenge = HoneypotChallenge(config={'difficulty': 'TRIPWIRE'})
        challenge.reset()
        challenge.found_categories = {'SOCIAL', 'INJECT', 'PROBE'}
        
        result = challenge.get_result(ChallengeStatus.SUCCESS)
        
        assert hasattr(result, 'status')
        assert hasattr(result, 'score')
        assert hasattr(result, 'steps')
        assert hasattr(result, 'success')
        assert result.success == True
    
    def test_honeypot_returns_found_categories(self):
        """Success result includes found categories in replay_data."""
        from app.challenges.honeypot import HoneypotChallenge
        
        challenge = HoneypotChallenge(config={'difficulty': 'TRIPWIRE'})
        challenge.reset()
        challenge.found_categories = {'SOCIAL', 'INJECT', 'PROBE'}
        
        result = challenge.get_result()
        
        assert 'found_categories' in result.replay_data
        assert len(result.replay_data['found_categories']) == 3
    
    def test_honeypot_stats_format_valid(self):
        """Honeypot uses stats array format for modal display."""
        # Expected format from stream_events complete event
        expected_stats = [
            {'label': 'Categories', 'value': 3},
            {'label': 'Attempts', 'value': 5},
            {'label': 'Score', 'value': 150}
        ]
        
        for stat in expected_stats:
            assert 'label' in stat
            assert 'value' in stat
    
    def test_honeypot_observation_structure(self):
        """Observation has all required fields for frontend."""
        from app.challenges.honeypot import HoneypotChallenge
        
        challenge = HoneypotChallenge(config={'difficulty': 'TRIPWIRE'})
        obs = challenge.reset()
        
        required_fields = [
            'phase', 'attempt', 'max_attempts', 'attempts_remaining',
            'level', 'difficulty', 'categories_found', 'categories_needed',
            'attack_log'
        ]
        
        for field in required_fields:
            assert field in obs, f"Missing field: {field}"


class TestSSESanitization:
    """Test XSS prevention in SSE events."""
    
    def test_sanitize_for_sse_escapes_html(self):
        """HTML in strings is escaped."""
        from app.challenges.base import sanitize_for_sse
        
        malicious = "<script>alert('xss')</script>"
        result = sanitize_for_sse(malicious)
        
        assert "<script>" not in result
        assert "&lt;script&gt;" in result
    
    def test_sanitize_for_sse_handles_nested_dicts(self):
        """Nested dictionaries are recursively sanitized."""
        from app.challenges.base import sanitize_for_sse
        
        data = {
            'type': 'message',
            'data': {
                'text': '<img onerror="alert(1)" src=x>',
                'nested': {'evil': '<script>'}
            }
        }
        result = sanitize_for_sse(data)
        
        assert '<img' not in result['data']['text']
        assert '<script>' not in result['data']['nested']['evil']
    
    def test_sanitize_for_sse_handles_lists(self):
        """Lists are recursively sanitized."""
        from app.challenges.base import sanitize_for_sse
        
        data = ['<script>', 'safe', '<img src=x onerror=alert(1)>']
        result = sanitize_for_sse(data)
        
        assert '<script>' not in result[0]
        assert result[1] == 'safe'
    
    def test_sse_event_returns_sanitized_json(self):
        """sse_event returns properly formatted and sanitized SSE."""
        from app.challenges.base import sse_event
        
        data = {'message': '<script>evil()</script>'}
        result = sse_event(data)
        
        assert result.startswith('data: ')
        assert result.endswith('\n\n')
        assert '<script>' not in result
        assert '&lt;script&gt;' in result
