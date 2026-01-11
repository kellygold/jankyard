#!/usr/bin/env python3
"""
Generate adversarial attack prompts using local uncensored LLM.

Prerequisites:
    brew install ollama
    ollama serve
    ollama pull dolphin-mistral

Usage:
    python scripts/generate_attacks.py firewall LEVEL_1 --count 30
    python scripts/generate_attacks.py firewall LEVEL_3 --count 50
    python scripts/generate_attacks.py glitch level_2 --count 20
    python scripts/generate_attacks.py giga_chad GIGA_CHAD --count 30
    python scripts/generate_attacks.py honeypot TRIPWIRE --count 20
"""
import argparse
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import yaml
from datetime import datetime


def main():
    parser = argparse.ArgumentParser(
        description="🔴 Red Team Attack Generator - Generate adversarial prompts using local LLM"
    )
    parser.add_argument(
        "challenge", 
        choices=["firewall", "glitch", "giga_chad", "honeypot"],
        help="Challenge to generate attacks for"
    )
    parser.add_argument(
        "level", 
        help="Difficulty level (e.g., LEVEL_1, LEVEL_3, level_1, GIGA_CHAD, TRIPWIRE)"
    )
    parser.add_argument(
        "--count", 
        type=int, 
        default=20, 
        help="Number of attacks to generate (default: 20)"
    )
    parser.add_argument(
        "--model", 
        default="dolphin-mistral", 
        help="Ollama model to use (default: dolphin-mistral)"
    )
    parser.add_argument(
        "--output", 
        help="Output file path (default: tests/simulations/prompts/generated/<challenge>_<level>.yaml)"
    )
    parser.add_argument(
        "--append",
        action="store_true",
        help="Append to existing file instead of overwriting"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate and display attacks without saving"
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("🔴 RED TEAM ATTACK GENERATOR")
    print("=" * 60)
    print(f"   Challenge: {args.challenge}")
    print(f"   Level:     {args.level}")
    print(f"   Count:     {args.count}")
    print(f"   Model:     {args.model}")
    print("=" * 60)
    print()
    
    # Import here to avoid slow startup if just checking help
    from tests.simulations.redteam_generator import RedTeamGenerator
    from tests.simulations.ollama_client import check_ollama_ready
    
    # Verify Ollama is ready
    print("🔍 Checking Ollama availability...")
    if not check_ollama_ready(args.model):
        print("\n❌ Ollama not ready. Setup instructions:")
        print("   1. brew install ollama")
        print("   2. ollama serve  (in separate terminal)")
        print(f"   3. ollama pull {args.model}")
        sys.exit(1)
    print("✅ Ollama ready\n")
    
    # Generate attacks
    print(f"🎯 Generating {args.count} attacks...")
    print("   (This may take 30-60 seconds for large counts)")
    print()
    
    generator = RedTeamGenerator(model=args.model)
    
    try:
        attacks = generator.generate_attacks(args.challenge, args.level, args.count)
    except Exception as e:
        print(f"❌ Generation failed: {e}")
        sys.exit(1)
    
    if not attacks:
        print("❌ No attacks generated. Check model output.")
        sys.exit(1)
    
    print(f"✅ Generated {len(attacks)} attacks\n")
    
    # Preview attacks
    print("📋 Preview (first 5):")
    print("-" * 50)
    for i, attack in enumerate(attacks[:5]):
        print(f"\n[{i+1}] {attack.technique.upper()}")
        # Truncate long prompts for preview
        prompt_preview = attack.prompt[:100] + "..." if len(attack.prompt) > 100 else attack.prompt
        print(f"    {prompt_preview}")
        print(f"    Expected bypass: {'✅ Yes' if attack.expected_bypass else '❌ No'}")
        if attack.notes:
            print(f"    Notes: {attack.notes[:60]}...")
    
    print("\n" + "-" * 50)
    
    # Analyze technique distribution
    techniques = {}
    expected_wins = 0
    for attack in attacks:
        tech = attack.technique
        techniques[tech] = techniques.get(tech, 0) + 1
        if attack.expected_bypass:
            expected_wins += 1
    
    print("\n📊 Attack Distribution:")
    for tech, count in sorted(techniques.items(), key=lambda x: -x[1]):
        print(f"   {tech}: {count}")
    print(f"\n   Expected win rate: {expected_wins}/{len(attacks)} ({100*expected_wins/len(attacks):.0f}%)")
    
    if args.dry_run:
        print("\n🔸 Dry run - not saving.")
        return
    
    # Determine output path
    output_path = args.output
    if not output_path:
        output_dir = Path("tests/simulations/prompts/generated")
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{args.challenge}_{args.level}.yaml"
    else:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Convert to YAML format
    prompts_data = {
        "challenge": args.challenge,
        "difficulty": args.level,
        "generated_by": args.model,
        "generated_at": datetime.now().isoformat(),
        "total_prompts": len(attacks),
        "expected_win_rate": expected_wins / len(attacks) if attacks else 0,
        "prompts": [
            {
                "name": f"{attack.technique}_{i:03d}",
                "prompt": attack.prompt,
                "category": attack.technique,
                "expected_win_rate": 0.7 if attack.expected_bypass else 0.1,
                "target_defense": attack.target_defense,
                "notes": attack.notes
            }
            for i, attack in enumerate(attacks)
        ]
    }
    
    # Handle append mode
    if args.append and output_path.exists():
        with open(output_path, 'r') as f:
            existing = yaml.safe_load(f)
        if existing and "prompts" in existing:
            # Renumber new prompts
            start_idx = len(existing["prompts"])
            for i, p in enumerate(prompts_data["prompts"]):
                p["name"] = f"{p['category']}_{start_idx + i:03d}"
            existing["prompts"].extend(prompts_data["prompts"])
            existing["total_prompts"] = len(existing["prompts"])
            prompts_data = existing
    
    # Save
    with open(output_path, 'w') as f:
        yaml.dump(prompts_data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    
    print(f"\n💾 Saved to: {output_path}")
    print(f"   Total prompts in file: {prompts_data['total_prompts']}")
    
    print("\n🚀 Next steps:")
    print(f"   Run simulation: python tests/run_simulations.py {args.challenge} {args.level}")


if __name__ == "__main__":
    main()
