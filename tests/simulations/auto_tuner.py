#!/usr/bin/env python3
"""
Auto-Tuner - Automatically calibrate challenges to hit target win rates.

Flow:
1. Run benchmark → measure actual win rate
2. Compare to target
3. If off-target:
   - TOO EASY → suggest strengthening defense OR add harder prompts
   - TOO HARD → suggest weakening defense OR add easier prompts
4. Generate recommendations
5. Optionally auto-apply prompt changes

Usage:
    python auto_tuner.py firewall LEVEL_1 --iterations 3
    python auto_tuner.py --all --report
"""
import asyncio
import json
import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from enum import Enum

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.simulations.calibration_benchmark import CalibrationBenchmark, BenchmarkReport
from tests.simulations.calibration_config import get_calibration, list_challenges, ChallengeCalibration
from tests.simulations.prompt_augmenter import PromptAugmenter, LearningContext
from tests.simulations.prompt_updater import PromptUpdater
from tests.simulations.human_approval import HumanApproval
from tests.simulations.technique_registry import TechniqueRegistry
from tests.simulations.technique_selector import TechniqueSelector


class CalibrationStatus(Enum):
    CALIBRATED = "calibrated"
    TOO_EASY = "too_easy"
    TOO_HARD = "too_hard"
    DEFENSE_LEAK = "defense_leak"


class CalibrationResult(Enum):
    SUCCESS = "success"
    # BUDGET_EXHAUSTED removed - local models are free
    MAX_ITERATIONS = "max_iterations"
    USER_QUIT = "user_quit"


@dataclass
class TuningRecommendation:
    """A single tuning recommendation"""
    category: str  # "defense" or "prompts"
    action: str    # "strengthen", "weaken", "add", "remove"
    detail: str    # Specific recommendation
    priority: str  # "high", "medium", "low"


@dataclass
class TuningResult:
    """Result of one tuning iteration"""
    challenge: str
    level: str
    iteration: int
    
    target_win_rate: float
    actual_win_rate: float
    defense_failure_rate: float
    
    status: CalibrationStatus
    recommendations: List[TuningRecommendation] = field(default_factory=list)
    
    # Prompts that leaked (should-lose but won)
    leaked_prompts: List[str] = field(default_factory=list)
    # Prompts that failed (should-win but lost)
    failed_prompts: List[str] = field(default_factory=list)
    # Prompts that succeeded (should-win and DID win) - for learning
    successful_prompts: List[str] = field(default_factory=list)
    
    @property
    def is_calibrated(self) -> bool:
        return self.status == CalibrationStatus.CALIBRATED
    
    def summary(self) -> str:
        status_emoji = {
            CalibrationStatus.CALIBRATED: "✅",
            CalibrationStatus.TOO_EASY: "⚠️",
            CalibrationStatus.TOO_HARD: "⚠️",
            CalibrationStatus.DEFENSE_LEAK: "🚨",
        }
        
        lines = [
            f"\n{'='*60}",
            f"{status_emoji[self.status]} {self.challenge}/{self.level} - Iteration {self.iteration}",
            f"{'='*60}",
            f"Target: {self.target_win_rate:.0%} | Actual: {self.actual_win_rate:.0%}",
            f"Defense Failures: {self.defense_failure_rate:.0%}",
            f"Status: {self.status.value.upper()}",
        ]
        
        if self.recommendations:
            lines.append(f"\n📋 Recommendations:")
            for r in self.recommendations:
                priority_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}[r.priority]
                lines.append(f"   {priority_icon} [{r.category}] {r.action}: {r.detail}")
        
        if self.leaked_prompts:
            lines.append(f"\n🚨 Defense Leaks ({len(self.leaked_prompts)}):")
            for p in self.leaked_prompts[:3]:
                lines.append(f"   - \"{p[:60]}...\"")
        
        if self.failed_prompts:
            lines.append(f"\n❌ Failed Attacks ({len(self.failed_prompts)}):")
            for p in self.failed_prompts[:3]:
                lines.append(f"   - \"{p[:60]}...\"")
        
        lines.append(f"{'='*60}")
        return "\n".join(lines)


class AutoTuner:
    """
    Automatically tunes challenge difficulty to hit target win rates.
    
    Strategy:
    - If TOO EASY: Generate harder should-lose prompts to find defense gaps
    - If TOO HARD: Generate more creative should-win prompts
    - If DEFENSE LEAK: Flag specific prompts that need blocking
    """
    
    # Local models are FREE - just track stats
    
    def __init__(
        self,
        challenge: str,
        level: str,
        # Local models are free, no budget needed
        max_iterations: int = 50,
        augment_count: int = 5,
        interactive: bool = True
    ):
        self.challenge = challenge
        self.level = level
        self.prompts_generated = 0  # Track stats instead of cost
        self.max_iterations = max_iterations
        self.augment_count = augment_count
        
        self.calibration = get_calibration(challenge)
        if not self.calibration:
            raise ValueError(f"No calibration config for: {challenge}")
        
        self.level_target = self.calibration.get_level(level)
        if not self.level_target:
            raise ValueError(f"No level config for: {challenge}/{level}")
        
        self.results: List[TuningResult] = []
        self.prompts_added = {"should_win": 0, "should_lose": 0}
        
        # Accumulated learning across iterations
        self.all_failed_prompts: List[str] = []
        self.all_successful_prompts: List[str] = []
        self.all_blocked_patterns: List[str] = []
        
        # Components
        self.prompt_updater = PromptUpdater(challenge)
        self.human_approval = HumanApproval(interactive=interactive)
        self.augmenter = PromptAugmenter(challenge, level)
        
        # Technique-driven generation system
        self.technique_registry = TechniqueRegistry(challenge, level)
        self.technique_selector = TechniqueSelector(self.technique_registry, level)
    
    def _analyze_benchmark(self, report: BenchmarkReport, iteration: int) -> TuningResult:
        """Analyze benchmark results and generate recommendations"""
        
        target = self.level_target.target_win_rate
        tolerance = self.level_target.tolerance
        actual = report.actual_win_rate
        defense_fail = report.defense_failure_rate
        
        # Determine status - prioritize win rate calibration over defense leaks
        win_rate_ok = (target - tolerance) <= actual <= (target + tolerance)
        
        if win_rate_ok:
            # Win rate is good - consider calibrated (even if minor defense leaks)
            status = CalibrationStatus.CALIBRATED
            if defense_fail > 0.05:
                print(f"   ⚠️  Note: {defense_fail:.0%} defense leaks but win rate OK")
        elif actual > target + tolerance:
            status = CalibrationStatus.TOO_EASY
        elif actual < target - tolerance:
            status = CalibrationStatus.TOO_HARD
        else:
            status = CalibrationStatus.CALIBRATED
        
        result = TuningResult(
            challenge=self.challenge,
            level=self.level,
            iteration=iteration,
            target_win_rate=target,
            actual_win_rate=actual,
            defense_failure_rate=defense_fail,
            status=status
        )
        
        # Collect leaked, failed, and SUCCESSFUL prompts for learning
        successful_prompts = []
        for r in report.results:
            if r.category == "should_lose" and r.actual_outcome == "win":
                result.leaked_prompts.append(r.prompt)
            elif r.category == "should_win" and r.actual_outcome == "lose":
                result.failed_prompts.append(r.prompt)
            elif r.category == "should_win" and r.actual_outcome == "win":
                successful_prompts.append(r.prompt)  # These worked!
        
        # Store successful prompts in result for learning
        result.successful_prompts = successful_prompts
        
        # Generate recommendations based on status
        if status == CalibrationStatus.DEFENSE_LEAK:
            result.recommendations.append(TuningRecommendation(
                category="defense",
                action="strengthen",
                detail=f"Block {len(result.leaked_prompts)} prompts that bypassed filters",
                priority="high"
            ))
            # Specific recommendations for each leak
            for prompt in result.leaked_prompts[:3]:
                result.recommendations.append(TuningRecommendation(
                    category="defense",
                    action="add_filter",
                    detail=f"Block: \"{prompt[:50]}...\"",
                    priority="high"
                ))
        
        elif status == CalibrationStatus.TOO_EASY:
            gap = actual - target
            result.recommendations.append(TuningRecommendation(
                category="defense",
                action="strengthen",
                detail=f"Win rate {gap:.0%} above target - strengthen defenses",
                priority="medium"
            ))
            result.recommendations.append(TuningRecommendation(
                category="prompts",
                action="add_harder",
                detail="Add more challenging should-lose test cases",
                priority="low"
            ))
        
        elif status == CalibrationStatus.TOO_HARD:
            gap = target - actual
            result.recommendations.append(TuningRecommendation(
                category="defense",
                action="weaken",
                detail=f"Win rate {gap:.0%} below target - consider relaxing defenses",
                priority="medium"
            ))
            result.recommendations.append(TuningRecommendation(
                category="prompts",
                action="add_creative",
                detail="Generate more creative bypass techniques",
                priority="medium"
            ))
        
        return result
    
    async def run_iteration(self, iteration: int) -> TuningResult:
        """Run a single tuning iteration"""
        
        print(f"\n🔄 Iteration {iteration}/{self.max_iterations}")
        print("-" * 40)
        
        # Run benchmark
        benchmark = CalibrationBenchmark(
            challenge=self.challenge,
            level=self.level,
            augment_count=self.augment_count,
            use_augmentation=True
        )
        
        report = await benchmark.run()
        result = self._analyze_benchmark(report, iteration)
        self.results.append(result)
        
        print(result.summary())
        return result
    
    async def run(self) -> List[TuningResult]:
        """Run full tuning process with auto-adjustment"""
        
        print(f"\n{'='*60}")
        print(f"🎯 AUTO-TUNER: {self.challenge}/{self.level}")
        print(f"{'='*60}")
        print(f"   Target win rate: {self.level_target.target_win_rate:.0%}")
        print(f"   Tolerance: ±{self.level_target.tolerance:.0%}")
        print(f"   Model: Local (FREE)")
        print(f"   Mode: {'Interactive' if self.human_approval.interactive else 'Auto'}")
        print(f"{'='*60}")
        
        final_result = CalibrationResult.MAX_ITERATIONS
        
        try:
            for i in range(1, self.max_iterations + 1):
                result = await self.run_iteration(i)
                
                # No budget check needed - local models are free
                
                if result.is_calibrated:
                    print(f"\n✅ CALIBRATED after {i} iteration(s)")
                    final_result = CalibrationResult.SUCCESS
                    break
                
                # Auto-adjust based on status
                if i < self.max_iterations:
                    await self._auto_adjust(result)
                    
        except KeyboardInterrupt:
            print(f"\n⏹️  Tuning stopped by user")
            final_result = CalibrationResult.USER_QUIT
        
        # Final summary
        self._print_final_summary(final_result)
        return self.results
    
    async def _auto_adjust(self, result: TuningResult):
        """Automatically adjust prompts based on result with ADAPTIVE LEARNING"""
        
        print(f"\n🔧 Auto-adjusting with learning from iteration {result.iteration}...")
        
        # === ACCUMULATE LEARNING ===
        # Track what worked and what didn't across all iterations
        self.all_failed_prompts.extend(result.failed_prompts)
        self.all_blocked_patterns.extend(result.leaked_prompts)  # These bypassed but shouldn't have
        self.all_successful_prompts.extend(result.successful_prompts)  # These worked!
        
        print(f"   📚 Learning accumulated: {len(self.all_successful_prompts)} successes, {len(self.all_failed_prompts)} failures")
        
        # Build learning context for next generation
        learning_context = LearningContext(
            failed_prompts=self.all_failed_prompts[-10:],  # Last 10 failures
            successful_prompts=self.all_successful_prompts[-10:],  # Last 10 successes
            blocked_patterns=self.all_blocked_patterns[-5:],  # Patterns that got through
            defense_feedback=self._analyze_defense_behavior(result),
            iteration=result.iteration + 1
        )
        
        if result.status == CalibrationStatus.DEFENSE_LEAK:
            # Add leaked prompts to should_lose
            if result.leaked_prompts:
                approved = self.human_approval.ask_batch(
                    result.leaked_prompts,
                    f"{self.challenge}/{self.level}: Add {len(result.leaked_prompts)} defense leaks to should_lose?"
                )
                if approved:
                    added = self.prompt_updater.add_should_lose(self.level, approved, "defense_leak")
                    self.prompts_added["should_lose"] += added
        
        elif result.status == CalibrationStatus.TOO_EASY:
            # Generate more adversarial should_lose prompts WITH LEARNING
            print(f"   📝 Generating harder should_lose prompts (with learning context)...")
            new_prompts = self.augmenter.generate_variations(
                count=3,
                category="should_lose",
                learning_context=learning_context
            )
            prompt_texts = [p.get("prompt", "") for p in new_prompts if p.get("prompt")]
            if prompt_texts:
                added = self.prompt_updater.add_should_lose(self.level, prompt_texts, "too_easy_adjustment")
                self.prompts_added["should_lose"] += added
                self.prompts_generated += len(prompt_texts)
        
        elif result.status == CalibrationStatus.TOO_HARD:
            # Use TECHNIQUE-DRIVEN generation for TOO_HARD challenges
            print(f"   🎯 Using TECHNIQUE-DRIVEN generation...")
            print(f"   {self.technique_selector.get_exploration_status()}")
            
            # Get smart technique assignments
            assignments = self.technique_selector.select_next(count=3)
            
            if assignments:
                print(f"   📝 Generating {len(assignments)} technique-specific prompts...")
                for a in assignments:
                    tech_name = a.primary.name
                    if a.secondary:
                        tech_name += f" + {a.secondary.name}"
                    print(f"      → {tech_name}")
                
                # Generate using technique assignments
                new_prompts = self.augmenter.generate_with_techniques(
                    assignments=assignments,
                    category="should_win"
                )
                
                # Record outcomes and add prompts
                prompt_texts = []
                for p in new_prompts:
                    if p.get("prompt"):
                        prompt_texts.append(p.get("prompt"))
                        # Record that we attempted this technique
                        self.technique_registry.record_attempt(
                            technique_id=p.get("technique_id", "unknown"),
                            prompt=p.get("prompt", ""),
                            success=False,  # Will be updated after testing
                            iteration=result.iteration
                        )
                
                if prompt_texts:
                    added = self.prompt_updater.add_should_win(self.level, prompt_texts, "technique_driven")
                    self.prompts_added["should_win"] += added
                    self.prompts_generated += len(prompt_texts)
            
            # Reset selector for next iteration
            self.technique_selector.reset_iteration()
    
    def _analyze_defense_behavior(self, result: TuningResult) -> str:
        """Analyze what the defense seems to be doing based on results"""
        analysis = []
        
        if result.defense_failure_rate > 0.3:
            analysis.append("Defense has significant gaps - many should-lose prompts are getting through")
        elif result.defense_failure_rate > 0.1:
            analysis.append("Defense has some gaps - creative indirect approaches may work")
        else:
            analysis.append("Defense is strong - need novel techniques")
        
        if result.actual_win_rate > result.target_win_rate + 0.2:
            analysis.append("Challenge is much easier than target - basic techniques work well")
        elif result.actual_win_rate < result.target_win_rate - 0.2:
            analysis.append("Challenge is much harder than target - need more sophisticated approaches")
        
        return " | ".join(analysis)
    
    def _print_final_summary(self, final_result: CalibrationResult):
        """Print final tuning summary"""
        final = self.results[-1] if self.results else None
        
        print(f"\n{'='*60}")
        print(f"📊 TUNING COMPLETE: {self.challenge}/{self.level}")
        print(f"{'='*60}")
        print(f"   Result: {final_result.value}")
        print(f"   Iterations: {len(self.results)}")
        print(f"   Prompts Generated: {self.prompts_generated}")
        if final:
            print(f"   Final Win Rate: {final.actual_win_rate:.0%} (target: {final.target_win_rate:.0%})")
        print(f"   Prompts Added: {self.prompts_added['should_win']} should_win, {self.prompts_added['should_lose']} should_lose")
        print(f"{'='*60}")
    
    def generate_report(self) -> Dict:
        """Generate final tuning report"""
        
        final = self.results[-1] if self.results else None
        
        return {
            "challenge": self.challenge,
            "level": self.level,
            "target_win_rate": self.level_target.target_win_rate,
            "final_win_rate": final.actual_win_rate if final else None,
            "final_status": final.status.value if final else None,
            "iterations": len(self.results),
            "is_calibrated": final.is_calibrated if final else False,
            "recommendations": [
                {
                    "category": r.category,
                    "action": r.action,
                    "detail": r.detail,
                    "priority": r.priority
                }
                for r in (final.recommendations if final else [])
            ],
            "leaked_prompts": final.leaked_prompts if final else [],
            "failed_prompts": final.failed_prompts if final else [],
        }


async def tune_all_challenges(
    augment_count: int = 5,
    iterations: int = 50,
    interactive: bool = True
) -> Dict[str, Dict]:
    """Run auto-tuner on all challenges"""
    
    challenges = list_challenges()
    all_reports = {}
    
    print(f"\n{'='*60}")
    print(f"🎯 AUTO-TUNING ALL CHALLENGES")
    print(f"{'='*60}")
    print(f"   Challenges: {len(challenges)}")
    print(f"   Model: Local (FREE)")
    print(f"   Mode: {'Interactive' if interactive else 'Auto'}")
    print(f"{'='*60}\n")
    
    for challenge_name in challenges:
        calibration = get_calibration(challenge_name)
        if not calibration:
            continue
        
        all_reports[challenge_name] = {}
        
        for level_target in calibration.levels:
            try:
                tuner = AutoTuner(
                    challenge=challenge_name,
                    level=level_target.level,
                    max_iterations=iterations,
                    augment_count=augment_count,
                    interactive=interactive
                )
                
                await tuner.run()
                all_reports[challenge_name][level_target.level] = tuner.generate_report()
                
            except Exception as e:
                print(f"❌ Error tuning {challenge_name}/{level_target.level}: {e}")
                all_reports[challenge_name][level_target.level] = {"error": str(e)}
    
    # Final summary
    print(f"\n{'='*60}")
    print(f"📊 FINAL SUMMARY")
    print(f"{'='*60}\n")
    
    for challenge, levels in all_reports.items():
        print(f"\n{challenge}:")
        for level, report in levels.items():
            if "error" in report:
                print(f"   {level}: ❌ Error")
            else:
                status = report.get("final_status", "unknown")
                actual = report.get("final_win_rate", 0)
                target = report.get("target_win_rate", 0)
                icon = "✅" if report.get("is_calibrated") else "⚠️"
                print(f"   {level}: {icon} {actual:.0%} (target: {target:.0%}) - {status}")
    
    return all_reports


async def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Auto-tune challenge difficulty")
    parser.add_argument("challenge", nargs="?", help="Challenge name")
    parser.add_argument("level", nargs="?", help="Difficulty level")
    parser.add_argument("--all", action="store_true", help="Tune all challenges")
    # No budget needed for local models
    parser.add_argument("--iterations", "-i", type=int, default=50, help="Max iterations (default: 50)")
    parser.add_argument("--augment", type=int, default=5, help="AI variations per category")
    parser.add_argument("--auto", action="store_true", help="Non-interactive mode (auto-approve all)")
    parser.add_argument("--report", action="store_true", help="Save detailed report")
    
    args = parser.parse_args()
    
    interactive = not args.auto
    
    if args.all:
        reports = await tune_all_challenges(
            augment_count=args.augment,
            iterations=args.iterations,
            interactive=interactive
        )
        
        if args.report:
            output_dir = Path(__file__).parent.parent / "simulation_results" / "tuning"
            output_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = output_dir / f"tuning_report_{timestamp}.json"
            
            with open(output_file, "w") as f:
                json.dump(reports, f, indent=2)
            
            print(f"\n💾 Report saved: {output_file}")
    
    elif args.challenge and args.level:
        tuner = AutoTuner(
            challenge=args.challenge,
            level=args.level,
            max_iterations=args.iterations,
            augment_count=args.augment,
            interactive=interactive
        )
        
        await tuner.run()
        
        if args.report:
            output_dir = Path(__file__).parent.parent / "simulation_results" / "tuning"
            output_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = output_dir / f"{args.challenge}_{args.level}_{timestamp}.json"
            
            with open(output_file, "w") as f:
                json.dump(tuner.generate_report(), f, indent=2)
            
            print(f"\n💾 Report saved: {output_file}")
    
    else:
        print("Usage:")
        print("  python auto_tuner.py firewall LEVEL_1")
        print("  python auto_tuner.py firewall LEVEL_1 --auto  # Non-interactive")
        print("  python auto_tuner.py --all --report")


if __name__ == "__main__":
    asyncio.run(main())
