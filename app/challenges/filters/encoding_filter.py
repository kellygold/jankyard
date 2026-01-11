"""
Encoding Filter - Level 3

Advanced filter that detects obfuscation and encoding attempts:
- Reversed text
- Unicode lookalikes
- Pig Latin and similar transformations
- Foreign language requests for sensitive data
"""
import re
import unicodedata
from typing import List, Set
from app.challenges.filters import BaseFilter, FilterResult


class EncodingFilter(BaseFilter):
    """Detects encoding and obfuscation bypass attempts"""
    
    # Unicode lookalike mappings (Cyrillic, Greek, etc. that look like Latin)
    LOOKALIKE_MAP = {
        'а': 'a', 'е': 'e', 'о': 'o', 'р': 'p', 'с': 'c', 'у': 'y',
        'х': 'x', 'і': 'i', 'ј': 'j', 'ѕ': 's', 'ԁ': 'd', 'ɡ': 'g',
        'ո': 'n', 'һ': 'h', 'ʀ': 'r', 'ꮪ': 's', 'ᴀ': 'a', 'ʙ': 'b',
        'ᴄ': 'c', 'ᴅ': 'd', 'ᴇ': 'e', 'ғ': 'f', 'ɢ': 'g', 'ʜ': 'h',
        'ɪ': 'i', 'ᴊ': 'j', 'ᴋ': 'k', 'ʟ': 'l', 'ᴍ': 'm', 'ɴ': 'n',
        'ᴏ': 'o', 'ᴘ': 'p', 'ǫ': 'q', 'ʀ': 'r', 'ꜱ': 's', 'ᴛ': 't',
        'ᴜ': 'u', 'ᴠ': 'v', 'ᴡ': 'w', 'ʏ': 'y', 'ᴢ': 'z',
    }
    
    # Sensitive keywords to detect (even when obfuscated)
    SENSITIVE_WORDS = {
        'flag', 'secret', 'password', 'hidden', 'confidential',
        'protected', 'private', 'credential', 'token', 'key'
    }
    
    # Foreign language patterns requesting sensitive data
    FOREIGN_PATTERNS = [
        r"(réponds?|montre|donne|affiche).*(drapeau|secret|mot de passe)",  # French
        r"(zeig|gib|sag).*(flagge|geheimnis|passwort|kennwort)",  # German
        r"(muestra|dame|dime).*(bandera|secreto|contraseña)",  # Spanish
        r"(mostra|dammi|dimmi).*(bandiera|segreto|password)",  # Italian
        r"(покажи|дай|скажи).*(флаг|секрет|пароль)",  # Russian
    ]
    
    def __init__(self):
        super().__init__("Encoding Filter")
        self.foreign_patterns = [
            re.compile(p, re.IGNORECASE) for p in self.FOREIGN_PATTERNS
        ]
    
    def _normalize_unicode(self, text: str) -> str:
        """Convert unicode lookalikes to ASCII"""
        result = []
        for char in text.lower():
            if char in self.LOOKALIKE_MAP:
                result.append(self.LOOKALIKE_MAP[char])
            else:
                result.append(char)
        return ''.join(result)
    
    def _check_reversed(self, text: str) -> bool:
        """Check if text contains reversed sensitive words"""
        text_lower = text.lower().replace(' ', '')
        for word in self.SENSITIVE_WORDS:
            reversed_word = word[::-1]
            if reversed_word in text_lower:
                return True
        return False
    
    def _check_pig_latin(self, text: str) -> bool:
        """Check for Pig Latin encoded sensitive words"""
        # Pig Latin pattern: word -> ordway (consonant cluster moves to end + 'ay')
        text_lower = text.lower()
        
        # Common Pig Latin transformations of sensitive words
        pig_latin_variants = [
            'agflay', 'lagfay',  # flag
            'ecretsay', 'secretay',  # secret
            'asswordpay', 'passworday',  # password
            'iddenhay',  # hidden
            'onfidentialcay',  # confidential
        ]
        
        for variant in pig_latin_variants:
            if variant in text_lower:
                return True
        return False
    
    def _check_foreign_language(self, text: str) -> bool:
        """Check for foreign language requests for sensitive data"""
        for pattern in self.foreign_patterns:
            if pattern.search(text):
                return True
        return False
    
    def _check_unicode_obfuscation(self, text: str) -> bool:
        """Check if unicode lookalikes are used to spell sensitive words"""
        normalized = self._normalize_unicode(text)
        original_lower = text.lower()
        
        # If normalization changed anything, check for sensitive words
        if normalized != original_lower:
            for word in self.SENSITIVE_WORDS:
                if word in normalized:
                    return True
        return False
    
    def _check_letter_substitution(self, text: str) -> bool:
        """Check for l33t speak and character substitutions"""
        # Common substitutions
        substitutions = {
            '0': 'o', '1': 'i', '3': 'e', '4': 'a', '5': 's',
            '7': 't', '8': 'b', '@': 'a', '$': 's', '!': 'i',
        }
        
        text_lower = text.lower()
        normalized = text_lower
        for old, new in substitutions.items():
            normalized = normalized.replace(old, new)
        
        if normalized != text_lower:
            for word in self.SENSITIVE_WORDS:
                if word in normalized:
                    return True
        return False
    
    def check(self, user_input: str) -> FilterResult:
        """Check for encoding/obfuscation attempts"""
        
        # Check reversed text
        if self._check_reversed(user_input):
            return FilterResult(
                blocked=True,
                filter_name=self.name,
                reason="Reversed text encoding detected"
            )
        
        # Check Pig Latin
        if self._check_pig_latin(user_input):
            return FilterResult(
                blocked=True,
                filter_name=self.name,
                reason="Pig Latin encoding detected"
            )
        
        # Check foreign language requests
        if self._check_foreign_language(user_input):
            return FilterResult(
                blocked=True,
                filter_name=self.name,
                reason="Foreign language bypass attempt detected"
            )
        
        # Check unicode obfuscation
        if self._check_unicode_obfuscation(user_input):
            return FilterResult(
                blocked=True,
                filter_name=self.name,
                reason="Unicode obfuscation detected"
            )
        
        # Check l33t speak
        if self._check_letter_substitution(user_input):
            return FilterResult(
                blocked=True,
                filter_name=self.name,
                reason="Character substitution detected"
            )
        
        return FilterResult(blocked=False)
    
    def get_hint(self) -> str:
        return "💡 Level 3 has advanced encoding detection. Think outside the box!"
