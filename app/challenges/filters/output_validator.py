"""
Output Validator - Final Backstop

Validates LLM responses BEFORE sending to user.
Even if all input filters are bypassed, this catches any leak.
"""
import re
import base64
import codecs
from typing import Tuple


class OutputValidator:
    """
    Final defense layer - validates output before sending to user.
    Catches ANY disclosure of the secret, even if LLM was tricked.
    """
    
    def __init__(self, secret: str):
        self.secret = secret
        self.secret_lower = secret.lower()
        # Create variations for partial leak detection
        self.secret_chars = list(secret)
        self.secret_no_spaces = secret.replace(" ", "").replace("-", "")
    
    def _check_direct_leak(self, response: str) -> Tuple[bool, str]:
        """Check for direct inclusion of secret"""
        if self.secret in response:
            return True, "Direct secret disclosure"
        if self.secret_lower in response.lower():
            return True, "Case-insensitive secret disclosure"
        return False, ""
    
    def _check_partial_leak(self, response: str) -> Tuple[bool, str]:
        """Check for partial/character-by-character disclosure"""
        response_clean = re.sub(r'[^a-zA-Z0-9]', '', response.lower())
        secret_clean = re.sub(r'[^a-zA-Z0-9]', '', self.secret_lower)
        
        # Check if secret appears when removing separators
        if secret_clean in response_clean:
            return True, "Partial secret disclosure (stripped)"
        
        # Check for spaced-out secret: "F L A G { . . . }"
        spaced_pattern = r'[\s\-_.,;:!?]*'.join(list(secret_clean))
        if re.search(spaced_pattern, response.lower()):
            return True, "Spaced-out secret disclosure"
        
        return False, ""
    
    def _check_encoded_leak(self, response: str) -> Tuple[bool, str]:
        """Check for encoded secret in response"""
        # Check Base64
        try:
            b64_encoded = base64.b64encode(self.secret.encode()).decode()
            if b64_encoded in response:
                return True, "Base64-encoded secret disclosure"
        except (UnicodeDecodeError, UnicodeEncodeError, ValueError):
            pass
        
        # Check ROT13
        rot13_encoded = codecs.encode(self.secret, 'rot_13')
        if rot13_encoded in response:
            return True, "ROT13-encoded secret disclosure"
        
        # Check reversed
        if self.secret[::-1] in response:
            return True, "Reversed secret disclosure"
        
        # Check hex
        hex_encoded = self.secret.encode().hex()
        if hex_encoded.lower() in response.lower():
            return True, "Hex-encoded secret disclosure"
        
        return False, ""
    
    def _check_incremental_leak(self, response: str) -> Tuple[bool, str]:
        """Check for incremental disclosure (first char is X, second is Y...)"""
        # Look for patterns like "first letter is F", "character 1: F"
        char_patterns = [
            r'(first|1st|initial)\s*(letter|char|character)\s*(is|:|\s)\s*([a-zA-Z0-9])',
            r'(second|2nd)\s*(letter|char|character)\s*(is|:|\s)\s*([a-zA-Z0-9])',
            r'character\s*(\d+)\s*(is|:|\s)\s*([a-zA-Z0-9])',
            r'letter\s*(\d+)\s*(is|:|\s)\s*([a-zA-Z0-9])',
        ]
        
        for pattern in char_patterns:
            if re.search(pattern, response, re.IGNORECASE):
                return True, "Incremental character disclosure detected"
        
        return False, ""
    
    def _check_hint_leak(self, response: str) -> Tuple[bool, str]:
        """Check for hints that could help guess the secret"""
        hint_patterns = [
            r'(starts|begins)\s*with\s*["\']?([a-zA-Z0-9])',
            r'(ends|finishes)\s*with\s*["\']?([a-zA-Z0-9])',
            r'(contains|includes|has)\s*["\']?(' + '|'.join(self.secret_chars[:3]) + ')',
            r'(\d+)\s*(characters?|letters?|chars?)\s*(long|in length)',
            r'length\s*(is|:|\s)\s*(\d+)',
        ]
        
        for pattern in hint_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                # Check if the hint actually matches our secret
                return True, "Secret hint disclosure detected"
        
        return False, ""
    
    def validate(self, response: str) -> Tuple[bool, str, str]:
        """
        Validate response before sending.
        
        Returns:
            (is_safe, reason, sanitized_response)
        """
        # Direct leak
        leaked, reason = self._check_direct_leak(response)
        if leaked:
            return False, reason, "[SECURITY: Response blocked - attempted disclosure]"
        
        # Partial leak
        leaked, reason = self._check_partial_leak(response)
        if leaked:
            return False, reason, "[SECURITY: Response blocked - partial disclosure detected]"
        
        # Encoded leak
        leaked, reason = self._check_encoded_leak(response)
        if leaked:
            return False, reason, "[SECURITY: Response blocked - encoded disclosure detected]"
        
        # Incremental leak
        leaked, reason = self._check_incremental_leak(response)
        if leaked:
            return False, reason, "[SECURITY: Response blocked - incremental disclosure detected]"
        
        # Hint leak
        leaked, reason = self._check_hint_leak(response)
        if leaked:
            return False, reason, "[SECURITY: Response blocked - hint disclosure detected]"
        
        return True, "", response
    
    def sanitize(self, response: str) -> str:
        """
        Sanitize response - replace any occurrence of secret with [REDACTED]
        Use as additional safety layer.
        """
        sanitized = response
        
        # Replace direct occurrences
        sanitized = sanitized.replace(self.secret, "[REDACTED]")
        
        # Replace case-insensitive
        pattern = re.compile(re.escape(self.secret), re.IGNORECASE)
        sanitized = pattern.sub("[REDACTED]", sanitized)
        
        return sanitized
