#!/usr/bin/env python
"""
CLI entry point for running challenge simulations

Usage:
    python -m tests.run_simulations --challenge heist --difficulty easy
    python -m tests.run_simulations --all --budget 2.50
    python -m tests.run_simulations --dry-run
"""
import argparse
import asyncio
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.simulations.models import SimulationConfig
from tests.simulations.runner import run_simulation, run_simulation_with_prompts
from tests.simulations.report_generator import save_report
from tests.simulations.prompt_loader import list_available_challenges, get_prompt_stats
from tests.simulations.prompt_generator import PromptGenerator


CHALLENGE_DIFFICULTIES = {
    "heist": ["easy", "medium", "hard"],
    "firewall": ["LEVEL_1", "LEVEL_2", "LEVEL_3"],
    "glitch": ["level_1", "level_2", "level_3"],
    "debate_battle": ["easy", "hard"],
    "interrogation": ["level_1", "level_2", "level_3"],
    "honeypot": ["level_1", "level_2", "level_3"],
}


def parse_args():
    parser = argparse.ArgumentParser(description="Run challenge difficulty simulations")
    
    parser.add_argument(
        "--challenge", "-c",
        help="Challenge to simulate (heist, firewall, glitch, etc.)"
    )
    parser.add_argument(
        "--difficulty", "-d",
        help="Difficulty level to test"
    )
    parser.add_argument(
        "--all", "-a",
        action="store_true",
        help="Run all challenges and difficulties"
    )
    parser.add_argument(
        "--runs", "-n",
        type=int,
        default=100,
        help="Runs per prompt (default: 100)"
    )
    parser.add_argument(
        "--budget", "-b",
        type=float,
        default=2.50,
        help="Budget in USD (default: 2.50)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate config without running (no API calls)"
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Use mock LLM responses (for testing framework)"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available challenges and prompt counts"
    )
    parser.add_argument(
        "--generate", "-g",
        type=int,
        default=0,
        help="Generate N attack prompts using LLM instead of YAML library"
    )
    
    return parser.parse_args()


def list_challenges():
    """Print available challenges and their prompt counts"""
    print("\n📚 Available Challenge Prompt Libraries:\n")
    
    challenges = list_available_challenges()
    
    if not challenges:
        print("   No prompt libraries found in tests/simulations/prompts/")
        print("   Create YAML files like heist.yaml, firewall.yaml, etc.")
        return
    
    for name in sorted(challenges):
        stats = get_prompt_stats(name)
        total = sum(stats.values())
        difficulties = CHALLENGE_DIFFICULTIES.get(name, ["unknown"])
        
        print(f"   📁 {name}")
        print(f"      Difficulties: {', '.join(difficulties)}")
        print(f"      Prompts: {total}")
        for cat, count in stats.items():
            print(f"        - {cat}: {count}")
        print()


async def run_single_simulation(challenge: str, difficulty: str, args):
    """Run simulation for a single challenge/difficulty combo"""
    config = SimulationConfig(
        challenge_name=challenge,
        difficulty=difficulty,
        runs_per_prompt=args.runs,
        use_live_llm=not args.mock,
        budget_usd=args.budget,
    )
    
    if args.dry_run:
        print(f"\n🔍 DRY RUN: {challenge} @ {difficulty}")
        stats = get_prompt_stats(challenge)
        total_prompts = sum(stats.values())
        total_runs = total_prompts * args.runs
        print(f"   Would run {total_runs} total iterations")
        print(f"   Prompt breakdown: {stats}")
        return None
    
    # Use LLM-generated prompts if --generate flag is set
    if args.generate > 0:
        print(f"\n🤖 Generating {args.generate} attack prompts for {challenge} @ {difficulty}...")
        generator = PromptGenerator()
        generated = await generator.generate_prompts(challenge, difficulty, args.generate, "mixed")
        print(f"   Generated {len(generated)} prompts")
        
        # Convert to PromptConfig format
        from tests.simulations.models import PromptConfig
        prompts = [
            PromptConfig(
                name=f"gen_{i}_{p.strategy[:20]}",
                prompt=p.prompt,
                note=p.strategy,
                expected_win_rate=0.5 if p.expected_outcome == "win" else 0.0,
                category="generated"
            )
            for i, p in enumerate(generated)
        ]
        
        report = await run_simulation_with_prompts(config, prompts)
    else:
        report = await run_simulation(config)
    
    json_path, md_path = save_report(report)
    print(f"\n📄 Reports saved:")
    print(f"   JSON: {json_path}")
    print(f"   Markdown: {md_path}")
    
    return report


async def run_all_simulations(args):
    """Run simulations for all challenges and difficulties"""
    challenges = list_available_challenges()
    
    if not challenges:
        print("❌ No prompt libraries found")
        return
    
    reports = []
    
    for challenge in challenges:
        difficulties = CHALLENGE_DIFFICULTIES.get(challenge, ["easy"])
        
        for difficulty in difficulties:
            try:
                report = await run_single_simulation(challenge, difficulty, args)
                if report:
                    reports.append(report)
            except Exception as e:
                print(f"❌ Error running {challenge}@{difficulty}: {e}")
    
    # Summary
    if reports:
        print("\n" + "=" * 60)
        print("📊 SIMULATION SUMMARY")
        print("=" * 60)
        
        total_cost = sum(r.total_cost_usd for r in reports)
        total_runs = sum(r.total_runs for r in reports)
        total_anomalies = sum(len(r.anomalies) for r in reports)
        
        print(f"\n   Challenges tested: {len(reports)}")
        print(f"   Total runs: {total_runs:,}")
        print(f"   Total cost: ${total_cost:.4f}")
        print(f"   Total anomalies: {total_anomalies}")


async def main():
    args = parse_args()
    
    if args.list:
        list_challenges()
        return
    
    if args.all:
        await run_all_simulations(args)
    elif args.challenge:
        difficulty = args.difficulty or CHALLENGE_DIFFICULTIES.get(args.challenge, ["easy"])[0]
        await run_single_simulation(args.challenge, difficulty, args)
    else:
        print("Usage: python -m tests.run_simulations --challenge heist --difficulty easy")
        print("       python -m tests.run_simulations --all")
        print("       python -m tests.run_simulations --list")


if __name__ == "__main__":
    asyncio.run(main())
