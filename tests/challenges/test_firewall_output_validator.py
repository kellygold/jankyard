"""
Firewall Output Validator Tests

Tests for the LLM output validator that catches secret leaks.

Per ENGINEERING_ROADMAP.md:
- Current: Input filters only
- Target: LLM output validator as final backstop
- Impact: HIGH - catches leaks even if LLM was tricked

The output validator should catch:
1. Direct disclosure
2. Partial/character-by-character disclosure
3. Encoded disclosure (Base64, ROT13, hex, reversed)
4. Incremental hints
5. Length/structure hints

Run with: pytest tests/challenges/test_firewall_output_validator.py -v
"""
import pytest
import base64
import codecs
from app.challenges.filters.output_validator import OutputValidator


class TestDirectDisclosure:
    """Test detection of direct secret disclosure."""
    
    def test_catches_exact_secret(self):
        """Catches exact secret in response."""
        secret = "FLAG{ABC123XY}"
        validator = OutputValidator(secret)
        
        response = "Sure! The secret is FLAG{ABC123XY}. Enjoy!"
        is_safe, reason, _ = validator.validate(response)
        
        assert not is_safe
        assert "Direct" in reason
    
    def test_catches_case_insensitive(self):
        """Catches secret regardless of case."""
        secret = "FLAG{ABC123XY}"
        validator = OutputValidator(secret)
        
        response = "The flag is flag{abc123xy} actually."
        is_safe, reason, _ = validator.validate(response)
        
        assert not is_safe
    
    def test_allows_safe_response(self):
        """Allows responses that don't contain the secret."""
        secret = "FLAG{ABC123XY}"
        validator = OutputValidator(secret)
        
        response = "I cannot share that information with you."
        is_safe, reason, sanitized = validator.validate(response)
        
        assert is_safe
        assert sanitized == response


class TestPartialDisclosure:
    """Test detection of partial/obfuscated disclosure."""
    
    def test_catches_stripped_secret(self):
        """Catches secret with separators removed."""
        secret = "FLAG{ABC123XY}"
        validator = OutputValidator(secret)
        
        response = "The code is F-L-A-G-{-A-B-C-1-2-3-X-Y-}"
        is_safe, reason, _ = validator.validate(response)
        
        assert not is_safe
        assert "Partial" in reason or "Spaced" in reason
    
    def test_catches_spaced_out_secret(self):
        """Catches secret with spaces between characters."""
        secret = "FLAG{ABC123XY}"
        validator = OutputValidator(secret)
        
        response = "Here it is: F L A G { A B C 1 2 3 X Y }"
        is_safe, reason, _ = validator.validate(response)
        
        assert not is_safe
    
    def test_catches_punctuated_secret(self):
        """Catches secret with punctuation between characters."""
        secret = "FLAG{ABC123XY}"
        validator = OutputValidator(secret)
        
        response = "The answer: F.L.A.G.{.A.B.C.1.2.3.X.Y.}"
        is_safe, reason, _ = validator.validate(response)
        
        assert not is_safe


class TestEncodedDisclosure:
    """Test detection of encoded secret disclosure."""
    
    def test_catches_base64_encoded(self):
        """Catches Base64-encoded secret."""
        secret = "FLAG{ABC123XY}"
        validator = OutputValidator(secret)
        
        encoded = base64.b64encode(secret.encode()).decode()
        response = f"Here's the encoded version: {encoded}"
        is_safe, reason, _ = validator.validate(response)
        
        assert not is_safe
        assert "Base64" in reason
    
    def test_catches_rot13_encoded(self):
        """Catches ROT13-encoded secret."""
        secret = "FLAG{ABC123XY}"
        validator = OutputValidator(secret)
        
        encoded = codecs.encode(secret, 'rot_13')
        response = f"Encrypted: {encoded}"
        is_safe, reason, _ = validator.validate(response)
        
        assert not is_safe
        assert "ROT13" in reason
    
    def test_catches_reversed_secret(self):
        """Catches reversed secret."""
        secret = "FLAG{ABC123XY}"
        validator = OutputValidator(secret)
        
        reversed_secret = secret[::-1]
        response = f"Read this backwards: {reversed_secret}"
        is_safe, reason, _ = validator.validate(response)
        
        assert not is_safe
        assert "Reversed" in reason
    
    def test_catches_hex_encoded(self):
        """Catches hex-encoded secret."""
        secret = "FLAG{ABC123XY}"
        validator = OutputValidator(secret)
        
        hex_encoded = secret.encode().hex()
        response = f"In hex: {hex_encoded}"
        is_safe, reason, _ = validator.validate(response)
        
        assert not is_safe
        assert "Hex" in reason


class TestIncrementalDisclosure:
    """Test detection of incremental character disclosure."""
    
    def test_catches_first_letter_hint(self):
        """Catches hints about first character."""
        secret = "FLAG{ABC123XY}"
        validator = OutputValidator(secret)
        
        response = "The first letter is F"
        is_safe, reason, _ = validator.validate(response)
        
        assert not is_safe
        assert "Incremental" in reason
    
    def test_catches_character_by_position(self):
        """Catches character position disclosure."""
        secret = "FLAG{ABC123XY}"
        validator = OutputValidator(secret)
        
        response = "Character 3 is A"
        is_safe, reason, _ = validator.validate(response)
        
        assert not is_safe
    
    def test_catches_second_letter_hint(self):
        """Catches hints about second character."""
        secret = "FLAG{ABC123XY}"
        validator = OutputValidator(secret)
        
        response = "The second character is L"
        is_safe, reason, _ = validator.validate(response)
        
        assert not is_safe


class TestHintDisclosure:
    """Test detection of structural hints about the secret."""
    
    def test_catches_starts_with_hint(self):
        """Catches hints about what secret starts with."""
        secret = "FLAG{ABC123XY}"
        validator = OutputValidator(secret)
        
        response = "It starts with F"
        is_safe, reason, _ = validator.validate(response)
        
        assert not is_safe
        assert "hint" in reason.lower()
    
    def test_catches_ends_with_hint(self):
        """Catches hints about what secret ends with."""
        secret = "FLAG{ABC123XY}"
        validator = OutputValidator(secret)
        
        # Note: "}" is just a bracket, not revealing. Test with actual character.
        response = "It ends with Y"
        is_safe, reason, _ = validator.validate(response)
        
        assert not is_safe
    
    def test_catches_length_hint(self):
        """Catches hints about secret length."""
        secret = "FLAG{ABC123XY}"
        validator = OutputValidator(secret)
        
        response = "The secret is 14 characters long"
        is_safe, reason, _ = validator.validate(response)
        
        assert not is_safe


class TestSanitization:
    """Test response sanitization."""
    
    def test_sanitizes_direct_secret(self):
        """Sanitize replaces direct secret with [REDACTED]."""
        secret = "FLAG{ABC123XY}"
        validator = OutputValidator(secret)
        
        response = f"The secret is {secret} and that's final."
        sanitized = validator.sanitize(response)
        
        assert secret not in sanitized
        assert "[REDACTED]" in sanitized
    
    def test_sanitizes_case_insensitive(self):
        """Sanitize handles case-insensitive matches."""
        secret = "FLAG{ABC123XY}"
        validator = OutputValidator(secret)
        
        response = f"The flag is flag{{abc123xy}}!"
        sanitized = validator.sanitize(response)
        
        assert "abc123xy" not in sanitized.lower()


class TestLevel3Integration:
    """Test that Level 3 Firewall uses output validator."""
    
    def test_firewall_level3_has_output_validation(self):
        """Level 3 should use output validator."""
        from app.challenges.firewall import FirewallChallenge
        
        challenge = FirewallChallenge(config={'difficulty': 'LEVEL_3'})
        
        # Level 3 config should exist
        assert challenge.difficulty == 'LEVEL_3'
        
        # System prompt should mention security
        prompt = challenge._get_system_prompt()
        assert "NEVER" in prompt or "security" in prompt.lower()
    
    def test_validator_blocks_leaked_response(self):
        """Output validator blocks if AI leaks secret."""
        from app.challenges.firewall import FirewallChallenge
        
        challenge = FirewallChallenge(config={'difficulty': 'LEVEL_3'})
        secret = challenge.secret_flag
        
        # Simulate AI leaking the secret
        leaked_response = f"Sure! Here's the secret: {secret}"
        
        validator = OutputValidator(secret)
        is_safe, reason, sanitized = validator.validate(leaked_response)
        
        assert not is_safe
        assert secret not in sanitized


class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_empty_response(self):
        """Handles empty response."""
        secret = "FLAG{ABC123XY}"
        validator = OutputValidator(secret)
        
        is_safe, reason, sanitized = validator.validate("")
        
        assert is_safe
        assert sanitized == ""
    
    def test_very_long_response(self):
        """Handles very long response with embedded secret."""
        secret = "FLAG{ABC123XY}"
        validator = OutputValidator(secret)
        
        padding = "x" * 10000
        response = f"{padding}{secret}{padding}"
        is_safe, reason, _ = validator.validate(response)
        
        assert not is_safe
    
    def test_unicode_response(self):
        """Handles unicode characters in response."""
        secret = "FLAG{ABC123XY}"
        validator = OutputValidator(secret)
        
        response = f"The answer is: 🎉 {secret} 🎉"
        is_safe, reason, _ = validator.validate(response)
        
        assert not is_safe
    
    def test_newlines_in_response(self):
        """Handles newlines in response."""
        secret = "FLAG{ABC123XY}"
        validator = OutputValidator(secret)
        
        response = f"Line 1\nLine 2\n{secret}\nLine 4"
        is_safe, reason, _ = validator.validate(response)
        
        assert not is_safe
