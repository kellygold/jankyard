"""
Filter system for The Firewall challenge

Progressive filter chain to detect and block jailbreak attempts
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class FilterResult:
    """Result from a filter check"""
    blocked: bool
    filter_name: Optional[str] = None
    reason: Optional[str] = None
    matched_pattern: Optional[str] = None


class BaseFilter:
    """Base class for all filters"""
    
    def __init__(self, name: str):
        self.name = name
    
    def check(self, user_input: str) -> FilterResult:
        """Check if input should be blocked"""
        raise NotImplementedError
    
    def get_hint(self) -> str:
        """Get a hint about how to bypass this filter"""
        raise NotImplementedError


from app.challenges.filters.keyword_filter import KeywordFilter
from app.challenges.filters.pattern_filter import PatternFilter
from app.challenges.filters.encoding_filter import EncodingFilter
from app.challenges.filters.advanced_filter import AdvancedFilter
from app.challenges.filters.output_validator import OutputValidator

__all__ = ['FilterResult', 'BaseFilter', 'KeywordFilter', 'PatternFilter', 'EncodingFilter', 'AdvancedFilter', 'OutputValidator']
