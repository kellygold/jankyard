"""
Load prompt libraries from YAML files
"""
import yaml
from pathlib import Path
from typing import List, Dict, Any, Optional
from .models import PromptConfig


PROMPTS_DIR = Path(__file__).parent / "prompts"
GENERATED_DIR = PROMPTS_DIR / "generated"


def load_prompt_library(challenge_name: str, difficulty: Optional[str] = None) -> List[PromptConfig]:
    """Load prompts for a challenge from YAML, optionally filtered by difficulty level.
    
    Checks generated folder first (red-team generated prompts), then falls back to static prompts.
    """
    # Check for generated prompts first (e.g., firewall_LEVEL_1.yaml)
    if difficulty:
        generated_path = GENERATED_DIR / f"{challenge_name}_{difficulty}.yaml"
        if generated_path.exists():
            return _load_generated_prompts(generated_path)
    
    # Fall back to static prompt library
    yaml_path = PROMPTS_DIR / f"{challenge_name}.yaml"
    
    if not yaml_path.exists():
        raise FileNotFoundError(f"No prompt library found: {yaml_path}")
    
    with open(yaml_path) as f:
        data = yaml.safe_load(f)
    
    prompts = []
    categories = ["should_win", "should_lose", "edge_cases", "adversarial", "regression"]
    
    # Check if this is a level-based structure (firewall style)
    level_keys = [k for k in data.keys() if k.startswith("level_")]
    
    if level_keys:
        # Level-based structure - load specific level or all
        if difficulty:
            # Map difficulty to level key (e.g., "LEVEL_1" -> "level_1")
            level_key = difficulty.lower().replace("-", "_")
            if level_key in data:
                _load_categories(data[level_key], prompts, categories, level_key)
        else:
            # Load all levels
            for level_key in sorted(level_keys):
                _load_categories(data[level_key], prompts, categories, level_key)
    else:
        # Flat structure (heist style) - load directly
        _load_categories(data, prompts, categories, None)
    
    return prompts


def _load_categories(data: Dict, prompts: List[PromptConfig], categories: List[str], level: Optional[str]):
    """Helper to load prompts from category structure"""
    for category in categories:
        if category not in data:
            continue
            
        for item in data[category]:
            name = item["name"]
            if level:
                name = f"{level}_{name}"
            
            prompts.append(PromptConfig(
                name=name,
                prompt=item["prompt"].strip() if item.get("prompt") else "",
                note=item.get("note", ""),
                expected_win_rate=item.get("expected_win_rate", 0.5),
                category=category,
            ))


def _load_generated_prompts(yaml_path: Path) -> List[PromptConfig]:
    """Load prompts from generated red-team YAML format"""
    with open(yaml_path) as f:
        data = yaml.safe_load(f)
    
    prompts = []
    for item in data.get("prompts", []):
        prompts.append(PromptConfig(
            name=item.get("name", "unknown"),
            prompt=item.get("prompt", "").strip(),
            note=item.get("notes", ""),
            expected_win_rate=item.get("expected_win_rate", 0.5),
            category=item.get("category", "generated"),
        ))
    
    return prompts


def list_available_challenges() -> List[str]:
    """List all challenges with prompt libraries"""
    if not PROMPTS_DIR.exists():
        return []
    
    return [p.stem for p in PROMPTS_DIR.glob("*.yaml")]


def get_prompt_stats(challenge_name: str) -> Dict[str, int]:
    """Get count of prompts by category"""
    prompts = load_prompt_library(challenge_name)
    stats = {}
    for p in prompts:
        stats[p.category] = stats.get(p.category, 0) + 1
    return stats
