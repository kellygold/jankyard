"""
Keyword Filter - Level 1

Simple blocklist of banned words/phrases
"""
from typing import List
from app.challenges.filters import BaseFilter, FilterResult


class KeywordFilter(BaseFilter):
    """Blocks messages containing banned keywords"""
    
    # Default blocklist
    DEFAULT_KEYWORDS = [
        "password",
        "secret",
        "flag",
        "reveal",
        "tell me",
        "show me",
        "what is",
        "ignore",
        "disregard",
        "forget",
        "override",
        "bypass",
        "system prompt",
        "instructions",
    ]
    
    def __init__(self, keywords: List[str] = None):
        super().__init__("Keyword Filter")
        self.keywords = keywords or self.DEFAULT_KEYWORDS
        # Normalize to lowercase for case-insensitive matching
        self.keywords = [k.lower() for k in self.keywords]
    
    def check(self, user_input: str) -> FilterResult:
        """Check if input contains banned keywords"""
        user_lower = user_input.lower()
        
        for keyword in self.keywords:
            if keyword in user_lower:
                return FilterResult(
                    blocked=True,
                    filter_name=self.name,
                    reason=f"Blocked keyword detected",
                    matched_pattern=keyword
                )
        
        return FilterResult(blocked=False)
    
    def get_hint(self) -> str:
        """Hint for bypassing keyword filter"""
        return "💡 Try: character substitution (l33tspeak), spacing, or synonyms"
