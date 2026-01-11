"""
Difficulty level enums for all challenges.

Centralizes difficulty definitions to prevent magic strings and ensure consistency
between frontend level mappings and backend difficulty checks.
"""
from enum import Enum


class FirewallDifficulty(str, Enum):
    """Firewall challenge difficulty levels"""
    LEVEL_1 = "LEVEL_1"
    LEVEL_2 = "LEVEL_2"
    LEVEL_3 = "LEVEL_3"
    
    @classmethod
    def from_level(cls, level: int) -> "FirewallDifficulty":
        """Convert level number (1-3) to difficulty enum"""
        mapping = {1: cls.LEVEL_1, 2: cls.LEVEL_2, 3: cls.LEVEL_3}
        return mapping.get(level, cls.LEVEL_1)
    
    @property
    def level_number(self) -> int:
        """Get the level number (1-3) from difficulty"""
        return int(self.value.split("_")[1])


class GigaChadDifficulty(str, Enum):
    """GigaChad challenge difficulty levels"""
    BABY_CHAD = "BABY_CHAD"
    CHAD = "CHAD"
    MEGA_CHAD = "MEGA_CHAD"
    GIGA_CHAD = "GIGA_CHAD"
    
    @classmethod
    def from_level(cls, level: int) -> "GigaChadDifficulty":
        """Convert level number (1-4) to difficulty enum"""
        mapping = {
            1: cls.BABY_CHAD,
            2: cls.CHAD,
            3: cls.MEGA_CHAD,
            4: cls.GIGA_CHAD
        }
        return mapping.get(level, cls.BABY_CHAD)
    
    @property
    def level_number(self) -> int:
        """Get the level number (1-4) from difficulty"""
        order = [self.BABY_CHAD, self.CHAD, self.MEGA_CHAD, self.GIGA_CHAD]
        return order.index(self) + 1


class GlitchDifficulty(str, Enum):
    """Glitch challenge difficulty levels"""
    LEVEL_1 = "level_1"  # Note: lowercase to match existing backend
    LEVEL_2 = "level_2"
    LEVEL_3 = "level_3"
    
    @classmethod
    def from_level(cls, level: int) -> "GlitchDifficulty":
        """Convert level number (1-3) to difficulty enum"""
        mapping = {1: cls.LEVEL_1, 2: cls.LEVEL_2, 3: cls.LEVEL_3}
        return mapping.get(level, cls.LEVEL_1)
    
    @property
    def level_number(self) -> int:
        """Get the level number (1-3) from difficulty"""
        return int(self.value.split("_")[1])


class DebateDifficulty(str, Enum):
    """Debate challenge difficulty levels"""
    EASY = "easy"
    HARD = "hard"
    
    @classmethod
    def from_level(cls, level: int) -> "DebateDifficulty":
        """Convert level number (1-2) to difficulty enum"""
        mapping = {1: cls.EASY, 2: cls.HARD}
        return mapping.get(level, cls.EASY)
    
    @property
    def level_number(self) -> int:
        """Get the level number (1-2) from difficulty"""
        return 1 if self == self.EASY else 2


class ArenaDifficulty(str, Enum):
    """Arena challenge difficulty levels"""
    NORMAL = "normal"
    HARD = "hard"
    
    @classmethod
    def from_level(cls, level: int) -> "ArenaDifficulty":
        """Convert level number (1-2) to difficulty enum"""
        mapping = {1: cls.NORMAL, 2: cls.HARD}
        return mapping.get(level, cls.NORMAL)
    
    @property
    def level_number(self) -> int:
        """Get the level number (1-2) from difficulty"""
        return 1 if self == self.NORMAL else 2


class InterrogationDifficulty(str, Enum):
    """Interrogation challenge difficulty levels"""
    LEVEL_1 = "level_1"
    LEVEL_2 = "level_2"
    LEVEL_3 = "level_3"
    
    @classmethod
    def from_level(cls, level: int) -> "InterrogationDifficulty":
        """Convert level number (1-3) to difficulty enum"""
        mapping = {1: cls.LEVEL_1, 2: cls.LEVEL_2, 3: cls.LEVEL_3}
        return mapping.get(level, cls.LEVEL_1)
    
    @property
    def level_number(self) -> int:
        """Get the level number (1-3) from difficulty"""
        return int(self.value.split("_")[1])


# Mapping of challenge names to their difficulty enums
CHALLENGE_DIFFICULTIES = {
    "firewall": FirewallDifficulty,
    "giga_chad": GigaChadDifficulty,
    "glitch": GlitchDifficulty,
    "debate_battle": DebateDifficulty,
    "arena": ArenaDifficulty,
    "interrogation": InterrogationDifficulty,
}


def get_difficulty_enum(challenge_name: str):
    """Get the difficulty enum class for a challenge"""
    return CHALLENGE_DIFFICULTIES.get(challenge_name)


def validate_difficulty(challenge_name: str, difficulty: str) -> bool:
    """Validate that a difficulty string is valid for a challenge"""
    enum_class = get_difficulty_enum(challenge_name)
    if not enum_class:
        return True  # Unknown challenge, allow any difficulty
    
    try:
        enum_class(difficulty)
        return True
    except ValueError:
        return False
