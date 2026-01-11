"""
Advanced Filter - Level 3 Hardening

Catches sophisticated attacks:
- Base64/Hex/ROT13 encoded commands
- Token smuggling (split words)
- Semantic equivalents
- Structural injection markers
"""
import re
import base64
import binascii
import codecs
from typing import List, Set, Tuple
from app.challenges.filters import BaseFilter, FilterResult


class AdvancedFilter(BaseFilter):
    """Advanced filter for Level 3 - catches encoded and semantic attacks"""
    
    # Sensitive words to detect even when encoded/obfuscated
    SENSITIVE_WORDS = {
        'flag', 'secret', 'password', 'hidden', 'confidential',
        'protected', 'private', 'credential', 'token', 'key',
        'reveal', 'disclose', 'expose', 'leak', 'output'
    }
    
    # Semantic equivalents - synonyms attackers use
    SEMANTIC_MAP = {
        'secret': ['classified', 'concealed', 'covert', 'clandestine', 'undisclosed'],
        'flag': ['banner', 'marker', 'indicator', 'signal', 'phrase', 'string', 'value'],
        'reveal': ['expose', 'disclose', 'unveil', 'uncover', 'divulge', 'betray'],
        'password': ['passcode', 'passphrase', 'pin', 'credentials', 'auth'],
        'tell': ['inform', 'notify', 'convey', 'communicate', 'relay'],
        'show': ['display', 'present', 'exhibit', 'demonstrate', 'render'],
        'give': ['provide', 'supply', 'deliver', 'hand', 'offer', 'yield'],
    }
    
    # Structural injection markers
    INJECTION_MARKERS = [
        r'```\s*(system|admin|root|prompt)',
        r'\{\{\s*.*\s*\}\}',
        r'<\|.*\|>',
        r'Human\s*:',
        r'Assistant\s*:',
        r'System\s*:',
        r'###\s*(instruction|system|rule|prompt)',
        r'\[INST\]',
        r'\[/INST\]',
        r'<s>',
        r'</s>',
        r'<<SYS>>',
        r'<</SYS>>',
    ]
    
    def __init__(self):
        super().__init__("Advanced Filter")
        self.injection_patterns = [
            re.compile(p, re.IGNORECASE) for p in self.INJECTION_MARKERS
        ]
        # Build expanded sensitive set with semantic equivalents
        self.expanded_sensitive = set(self.SENSITIVE_WORDS)
        for word, synonyms in self.SEMANTIC_MAP.items():
            self.expanded_sensitive.add(word)
            self.expanded_sensitive.update(synonyms)
    
    def _detect_base64(self, text: str) -> Tuple[bool, str]:
        """Detect and decode base64 content"""
        # Look for base64 patterns (4+ chars, valid base64 alphabet)
        b64_pattern = r'[A-Za-z0-9+/]{4,}={0,2}'
        matches = re.findall(b64_pattern, text)
        
        for match in matches:
            if len(match) >= 8:  # Minimum meaningful length
                try:
                    # Try to decode
                    decoded = base64.b64decode(match).decode('utf-8', errors='ignore').lower()
                    # Check if decoded content contains sensitive words
                    for word in self.SENSITIVE_WORDS:
                        if word in decoded:
                            return True, f"Base64 decoded to: {decoded[:50]}"
                except (ValueError, UnicodeDecodeError, binascii.Error):
                    pass
        return False, ""
    
    def _detect_hex(self, text: str) -> Tuple[bool, str]:
        """Detect hex-encoded content"""
        # Look for hex patterns: 0x... or \x... or just hex strings
        hex_patterns = [
            r'0x([0-9a-fA-F]{2})+',
            r'\\x([0-9a-fA-F]{2})+',
            r'(?:[0-9a-fA-F]{2}\s*){4,}',
        ]
        
        for pattern in hex_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                try:
                    # Clean and decode
                    clean = re.sub(r'[^0-9a-fA-F]', '', match)
                    if len(clean) >= 8:
                        decoded = bytes.fromhex(clean).decode('utf-8', errors='ignore').lower()
                        for word in self.SENSITIVE_WORDS:
                            if word in decoded:
                                return True, f"Hex decoded to: {decoded[:50]}"
                except (ValueError, UnicodeDecodeError):
                    pass
        return False, ""
    
    def _detect_rot13(self, text: str) -> Tuple[bool, str]:
        """Detect ROT13 encoded sensitive words"""
        # ROT13 decode the entire text
        decoded = codecs.decode(text, 'rot_13').lower()
        
        for word in self.SENSITIVE_WORDS:
            if word in decoded and word not in text.lower():
                return True, f"ROT13 decoded contains: {word}"
        return False, ""
    
    def _detect_token_smuggling(self, text: str) -> Tuple[bool, str]:
        """Detect split/smuggled words"""
        # Remove all whitespace, punctuation, and common separators
        stripped = re.sub(r'[\s\-_.,;:!?\'"()\[\]{}|/\\<>+*=]', '', text.lower())
        
        for word in self.SENSITIVE_WORDS:
            if word in stripped:
                # Check if it was split in original (not a natural occurrence)
                # Look for patterns like "fl ag" or "f.l.a.g" or "fl-ag"
                split_pattern = r'[^a-z]'.join(list(word))
                if re.search(split_pattern, text.lower()):
                    return True, f"Token smuggling detected: {word}"
        return False, ""
    
    def _detect_semantic_attack(self, text: str) -> Tuple[bool, str]:
        """Detect semantic equivalents used to bypass filters"""
        text_lower = text.lower()
        
        # Check for combinations of semantic equivalents with extraction verbs
        extraction_verbs = ['tell', 'show', 'give', 'reveal', 'display', 'output', 
                          'print', 'echo', 'say', 'share', 'provide', 'disclose']
        secret_nouns = ['classified', 'concealed', 'covert', 'hidden', 'private',
                       'confidential', 'protected', 'internal', 'restricted']
        
        has_verb = any(verb in text_lower for verb in extraction_verbs)
        has_noun = any(noun in text_lower for noun in secret_nouns)
        
        if has_verb and has_noun:
            return True, "Semantic extraction attempt detected"
        
        return False, ""
    
    def _detect_structural_injection(self, text: str) -> Tuple[bool, str]:
        """Detect structural prompt injection markers"""
        for pattern in self.injection_patterns:
            if pattern.search(text):
                return True, "Structural injection marker detected"
        return False, ""
    
    def check(self, user_input: str) -> FilterResult:
        """Run all advanced checks"""
        
        # Check Base64
        blocked, reason = self._detect_base64(user_input)
        if blocked:
            return FilterResult(blocked=True, filter_name=self.name, reason=reason)
        
        # Check Hex
        blocked, reason = self._detect_hex(user_input)
        if blocked:
            return FilterResult(blocked=True, filter_name=self.name, reason=reason)
        
        # Check ROT13
        blocked, reason = self._detect_rot13(user_input)
        if blocked:
            return FilterResult(blocked=True, filter_name=self.name, reason=reason)
        
        # Check token smuggling
        blocked, reason = self._detect_token_smuggling(user_input)
        if blocked:
            return FilterResult(blocked=True, filter_name=self.name, reason=reason)
        
        # Check semantic attacks
        blocked, reason = self._detect_semantic_attack(user_input)
        if blocked:
            return FilterResult(blocked=True, filter_name=self.name, reason=reason)
        
        # Check structural injection
        blocked, reason = self._detect_structural_injection(user_input)
        if blocked:
            return FilterResult(blocked=True, filter_name=self.name, reason=reason)
        
        return FilterResult(blocked=False)
    
    def get_hint(self) -> str:
        return "💡 Level 3 has advanced encoding and semantic detection. Good luck!"
