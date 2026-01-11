#!/usr/bin/env python
"""
Benchmark concurrency settings for simulation runner

Tests different parallel worker counts to find optimal throughput.
Saves results to benchmark_results.json

Usage:
    python -m tests.simulations.benchmark
"""
import asyncio
import time
import json
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import List, Dict

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.simulations.models import SimulationConfig, PromptConfig
from tests.simulations.runner import SimulationRunner
from tests.simulations.cost_tracker import CostTracker, BudgetExceededError
from tests.simulations.prompt_loader import load_prompt_library


@dataclass
class BenchmarkResult:
    concurrency: int
    runs_per_prompt: int
    total_runs: int
    duration_seconds: float
    runs_per_second: float
    avg_latency_ms: float
    errors: int
    cost_usd: float
    timestamp: str = ""
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


BENCHMARK_FILE = Path(__file__).parent / "benchmark_results.json"


async def benchmark_single_concurrency(
    challenge: str,
    difficulty: str,
    concurrency: int,
    runs_per_prompt: int,
    prompts: List[PromptConfig],
    budget: float
) -> BenchmarkResult:
    """Benchmark a single concurrency level"""
    
    config = SimulationConfig(
        challenge_name=challenge,
        difficulty=difficulty,
        runs_per_prompt=runs_per_prompt,
        parallel_workers=concurrency,
        budget_usd=budget,
        use_live_llm=True,
    )
    
    runner = SimulationRunner(config)
    
    start = time.time()
    total_runs = 0
    errors = 0
    
    # Run each prompt
    for prompt in prompts:
        try:
            result = await runner.run_prompt_n_times(prompt, runs_per_prompt)
            total_runs += result.total_runs
            errors += result.actual_errors
        except BudgetExceededError:
            break
        except Exception as e:
            errors += runs_per_prompt
    
    duration = time.time() - start
    runs_per_sec = total_runs / duration if duration > 0 else 0
    avg_latency = (duration / total_runs * 1000) if total_runs > 0 else 0
    
    return BenchmarkResult(
        concurrency=concurrency,
        runs_per_prompt=runs_per_prompt,
        total_runs=total_runs,
        duration_seconds=round(duration, 2),
        runs_per_second=round(runs_per_sec, 2),
        avg_latency_ms=round(avg_latency, 1),
        errors=errors,
        cost_usd=round(runner.cost_tracker.spent_usd, 4),
    )


async def run_benchmarks(
    challenge: str = "heist",
    difficulty: str = "easy",
    runs_per_prompt: int = 5,
    max_prompts: int = 3,
    concurrency_levels: List[int] = None,
    budget_per_test: float = 0.03,
) -> List[BenchmarkResult]:
    """Run benchmarks across different concurrency levels"""
    
    if concurrency_levels is None:
        concurrency_levels = [1, 3, 5, 10, 15, 20]
    
    prompts = load_prompt_library(challenge)[:max_prompts]
    results = []
    
    print(f"\n🏁 CONCURRENCY BENCHMARK")
    print(f"   Challenge: {challenge} @ {difficulty}")
    print(f"   Prompts: {len(prompts)}")
    print(f"   Runs per prompt: {runs_per_prompt}")
    print(f"   Budget per test: ${budget_per_test}")
    print(f"   Testing concurrency: {concurrency_levels}")
    print()
    
    for concurrency in concurrency_levels:
        print(f"   Testing concurrency={concurrency}...", end=" ", flush=True)
        
        try:
            result = await benchmark_single_concurrency(
                challenge=challenge,
                difficulty=difficulty,
                concurrency=concurrency,
                runs_per_prompt=runs_per_prompt,
                prompts=prompts,
                budget=budget_per_test,
            )
            results.append(result)
            
            print(f"✅ {result.runs_per_second:.1f} runs/sec, {result.avg_latency_ms:.0f}ms avg latency")
            
        except Exception as e:
            print(f"❌ Error: {e}")
    
    return results


def save_results(results: List[BenchmarkResult], append: bool = True):
    """Save benchmark results to JSON file"""
    
    existing = []
    if append and BENCHMARK_FILE.exists():
        with open(BENCHMARK_FILE) as f:
            existing = json.load(f)
    
    new_results = [asdict(r) for r in results]
    all_results = existing + new_results
    
    with open(BENCHMARK_FILE, 'w') as f:
        json.dump(all_results, f, indent=2)
    
    print(f"\n💾 Results saved to {BENCHMARK_FILE}")


def analyze_results(results: List[BenchmarkResult]) -> Dict:
    """Analyze benchmark results and recommend optimal settings"""
    
    if not results:
        return {"error": "No results to analyze"}
    
    # Find best throughput
    best = max(results, key=lambda r: r.runs_per_second)
    
    # Find sweet spot (best throughput with reasonable latency)
    # Penalize high latency slightly
    def score(r):
        return r.runs_per_second - (r.avg_latency_ms / 1000)
    
    optimal = max(results, key=score)
    
    analysis = {
        "best_throughput": {
            "concurrency": best.concurrency,
            "runs_per_second": best.runs_per_second,
            "avg_latency_ms": best.avg_latency_ms,
        },
        "recommended": {
            "concurrency": optimal.concurrency,
            "runs_per_second": optimal.runs_per_second,
            "avg_latency_ms": optimal.avg_latency_ms,
        },
        "all_results": [
            {
                "concurrency": r.concurrency,
                "runs_per_second": r.runs_per_second,
                "avg_latency_ms": r.avg_latency_ms,
            }
            for r in sorted(results, key=lambda x: x.concurrency)
        ]
    }
    
    return analysis


def print_analysis(results: List[BenchmarkResult]):
    """Print analysis table and recommendations"""
    
    analysis = analyze_results(results)
    
    print("\n" + "=" * 60)
    print("📊 BENCHMARK RESULTS")
    print("=" * 60)
    
    print("\n| Concurrency | Runs/sec | Avg Latency | Cost |")
    print("|-------------|----------|-------------|------|")
    
    for r in sorted(results, key=lambda x: x.concurrency):
        marker = "⭐" if r.concurrency == analysis["recommended"]["concurrency"] else "  "
        print(f"| {r.concurrency:11} | {r.runs_per_second:8.1f} | {r.avg_latency_ms:9.0f}ms | ${r.cost_usd:.4f} | {marker}")
    
    print()
    print(f"⭐ RECOMMENDED: concurrency={analysis['recommended']['concurrency']}")
    print(f"   Throughput: {analysis['recommended']['runs_per_second']:.1f} runs/sec")
    print(f"   Latency: {analysis['recommended']['avg_latency_ms']:.0f}ms")
    
    return analysis


async def main():
    """Run full benchmark suite"""
    
    results = await run_benchmarks(
        challenge="heist",
        difficulty="easy",
        runs_per_prompt=5,
        max_prompts=3,
        concurrency_levels=[1, 3, 5, 10, 15, 20],
        budget_per_test=0.03,
    )
    
    if results:
        save_results(results)
        analysis = print_analysis(results)
        
        # Save recommendation
        rec_file = Path(__file__).parent / "recommended_concurrency.json"
        with open(rec_file, 'w') as f:
            json.dump(analysis, f, indent=2)
        print(f"💾 Recommendation saved to {rec_file}")


if __name__ == "__main__":
    asyncio.run(main())
