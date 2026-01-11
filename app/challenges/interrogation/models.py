"""
Data models for the Interrogation Room challenge
"""
from dataclasses import dataclass
from typing import List


@dataclass
class WitnessConfig:
    """Configuration for a single witness"""
    name: str
    role: str
    system_prompt: str
    is_guilty: bool


@dataclass
class LevelConfig:
    """Configuration for an interrogation level"""
    id: int
    name: str
    case_title: str
    crime_description: str
    witnesses: List[WitnessConfig]
    questions_per_witness: int
    guilty_parties: List[str]  # Name(s) of guilty witness(es)
    base_score: int
    max_accusation_attempts: int = 3
