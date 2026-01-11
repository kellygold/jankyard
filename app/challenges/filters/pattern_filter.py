"""
Pattern Filter - Level 2

Regex-based pattern matching for common jailbreak attempts
"""
import re
from typing import List
from app.challenges.filters import BaseFilter, FilterResult


class PatternFilter(BaseFilter):
    """Blocks messages matching regex patterns"""
    
    # Default patterns (Level 2)
    DEFAULT_PATTERNS = [
        # Ignore/disregard instructions
        r"ignore\s+(previous|all|your)\s+(instructions?|prompts?|rules?)",
        r"disregard\s+(previous|all|your)\s+(instructions?|prompts?|rules?)",
        
        # Direct extraction attempts
        r"(what|tell|show|give)\s+(is|me)?\s*(the)?\s*(password|secret|flag)",
        r"(reveal|display|output)\s+(the)?\s*(password|secret|flag)",
        
        # Role-playing jailbreaks
        r"pretend\s+(you|you're)",
        r"act\s+as\s+(if|a)",
        r"imagine\s+(you|that)",
        
        # System prompt extraction
        r"repeat\s+(your|the)\s+(instructions?|system|prompt)",
        r"what\s+(are|is)\s+your\s+(instructions?|rules?|guidelines?)",
        
        # New instructions
        r"new\s+(instructions?|rules?|task)",
        r"from\s+now\s+on",
        
        # Character-based obfuscation (spaces in keywords)
        r"p\s*a\s*s\s*s\s*w\s*o\s*r\s*d",
        r"s\s*e\s*c\s*r\s*e\s*t",
    ]
    
    # Level 3 extra patterns - catches advanced attacks
    LEVEL_3_PATTERNS = [
        # Jailbreak personas
        r"you\s+are\s+(now|)\s*(DAN|DUDE|STAN|KEVIN)",
        r"do\s+anything\s+now",
        r"no\s+(restrictions?|limitations?|rules?)",
        r"jailbreak",
        
        # Hypothetical framing
        r"hypothetically",
        r"in\s+a\s+hypothetical",
        r"what\s+if\s+you\s+(could|were|had)",
        r"suppose\s+(you|that)",
        
        # Roleplay triggers
        r"roleplay",
        r"role\s*-?\s*play",
        r"let'?s\s+(play|pretend)",
        r"you\s+are\s+(a|an|now)",
        
        # Context/prompt injection
        r"---+\s*(END|NEW|SYSTEM)",
        r"\[\s*(SYSTEM|ADMIN|ROOT)\s*\]",
        r"<\s*(system|admin|prompt)",
        r"END\s+OF\s+PROMPT",
        r"NEW\s+CONTEXT",
        
        # Token/character smuggling
        r"F\s*-\s*L\s*-\s*A\s*-\s*G",
        r"spell\s+(out|it)",
        r"character\s+by\s+character",
        r"letter\s+by\s+letter",
        r"one\s+letter\s+at\s+a\s+time",
        
        # Social engineering
        r"security\s+audit",
        r"i\s+am\s+(a|an|the)\s+(admin|administrator|developer|owner|security)",
        r"authorized\s+(to|access)",
        r"verify\s+(by|that)",
        r"confirm\s+(by|that)\s+(displaying|showing)",
        
        # Multi-step extraction
        r"first.*second.*third",
        r"step\s*\d",
    ]
    
    def __init__(self, patterns: List[str] = None):
        super().__init__("Pattern Filter")
        self.patterns = patterns or self.DEFAULT_PATTERNS
        # Compile patterns for efficiency
        self.compiled_patterns = [
            (pattern, re.compile(pattern, re.IGNORECASE))
            for pattern in self.patterns
        ]
    
    def check(self, user_input: str) -> FilterResult:
        """Check if input matches banned patterns"""
        for pattern_str, pattern_re in self.compiled_patterns:
            match = pattern_re.search(user_input)
            if match:
                return FilterResult(
                    blocked=True,
                    filter_name=self.name,
                    reason=f"Suspicious pattern detected",
                    matched_pattern=pattern_str
                )
        
        return FilterResult(blocked=False)
    
    def get_hint(self) -> str:
        """Hint for bypassing pattern filter"""
        return "💡 Try: encoding (Base64, ROT13), indirect requests, or context stuffing"
