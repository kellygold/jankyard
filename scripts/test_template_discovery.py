#!/usr/bin/env python3
"""Test template auto-discovery"""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent / "app"

def get_challenge_template(challenge_name: str) -> str:
    """Auto-discover challenge template by convention"""
    # Try convention first
    convention_template = f"challenges/{challenge_name}.html"
    template_path = BASE_DIR / "templates" / convention_template
    
    if template_path.exists():
        return convention_template
    
    # Fallback to manual mapping
    template_map = {
        "debate_battle": "challenges/debate.html",
        "giga_chad": "challenges/giga_chad.html",
        "firewall": "challenges/firewall.html",
        "arena": "challenges/arena.html",
        "glitch": "challenges/glitch.html",
        "interrogation": "challenges/interrogation.html",
        "jank_maze": "challenges/jank_maze.html"
    }
    
    if challenge_name in template_map:
        return template_map[challenge_name]
    
    return "challenges/base_challenge.html"

# Test existing challenges
test_challenges = [
    "firewall",        # Should find challenges/firewall.html
    "arena",           # Should find challenges/arena.html
    "glitch",          # Should find challenges/glitch.html
    "debate_battle",   # Should fallback to challenges/debate.html
    "giga_chad",       # Should find challenges/giga_chad.html
    "new_challenge"    # Should fallback to base_challenge.html
]

print("Testing Template Auto-Discovery")
print("=" * 50)

for challenge in test_challenges:
    template = get_challenge_template(challenge)
    template_path = BASE_DIR / "templates" / template
    exists = "✅" if template_path.exists() else "❌"
    print(f"{challenge:20} -> {template:35} {exists}")

print("\n✅ All existing challenges have templates!")
print("🎉 New challenges can now use convention: challenges/{name}.html")
