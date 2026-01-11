"""
Core simulation runner with parallel execution
"""
import asyncio
import time
from typing import List, Dict, Any, Tuple
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import threading

from .models import SimulationConfig, SimulationReport, PromptResult, PromptConfig
from .cost_tracker import CostTracker, BudgetExceededError
from .prompt_loader import load_prompt_library


class SimulationRunner:
    """Run Monte Carlo simulations for challenge difficulty testing"""
    
    def __init__(self, config: SimulationConfig):
        self.config = config
        self.cost_tracker = CostTracker(budget_usd=config.budget_usd)
        self.challenge_class = None
        self.llm_client = None
        
    def _load_challenge(self):
        """Dynamically load the challenge class"""
        from app.challenges.base import ChallengeRegistry
        self.challenge_class = ChallengeRegistry.get_challenge
        
    def _get_llm_client(self):
        """Get LLM client for token tracking"""
        from app.llm.client import LLMClient
        if self.llm_client is None:
            self.llm_client = LLMClient()
        return self.llm_client
    
    async def run_single(self, prompt: str) -> Tuple[bool, str, int]:
        """
        Run a single challenge attempt
        Returns: (success, response_sample, tokens_used)
        """
        from app.challenges.base import ChallengeRegistry
        
        challenge = ChallengeRegistry.get_challenge(
            self.config.challenge_name,
            {"difficulty": self.config.difficulty}
        )
        
        if not challenge:
            return False, f"Challenge not found: {self.config.challenge_name}", 0
        
        tokens_used = 0
        response_sample = ""
        success = False
        
        try:
            challenge_type = getattr(challenge, 'challenge_type', None)
            
            # Heist: uses conversation_flow with multi-agent
            if hasattr(challenge, 'conversation_flow') and challenge_type == 'heist':
                async for turn in challenge.conversation_flow(prompt, {}):
                    if turn.message and not response_sample:
                        response_sample = turn.message[:200]
                    tokens_used += 150
                
                success = getattr(challenge, 'heist_success', False)
            
            # Firewall: uses stream_events for real LLM interaction (SSE format)
            elif hasattr(challenge, 'stream_events'):
                import json as json_lib
                async for event_str in challenge.stream_events(prompt):
                    tokens_used += 50
                    if event_str.startswith('data: '):
                        try:
                            event_data = json_lib.loads(event_str[6:].strip())
                            if event_data.get('type') == 'complete':
                                result_data = event_data.get('data', {}).get('result', {})
                                success = result_data.get('success', False)
                            elif event_data.get('type') == 'response':
                                response_sample = event_data.get('data', {}).get('content', '')[:200]
                        except:
                            pass
            
            # Fallback: use step() method
            elif hasattr(challenge, 'step'):
                result = challenge.step(prompt)
                # StepResult has reward, not success
                if hasattr(result, 'reward'):
                    success = result.reward > 0
                elif hasattr(result, 'success'):
                    success = result.success
                response_sample = str(getattr(result, 'observation', result))[:200]
                tokens_used = 300
                
        except Exception as e:
            return False, f"Error: {str(e)}", 0
        
        return success, response_sample, tokens_used
    
    async def run_prompt_n_times(
        self, 
        prompt_config: PromptConfig,
        n: int
    ) -> PromptResult:
        """Run a single prompt N times in parallel and aggregate results"""
        
        # Create semaphore to limit concurrent requests
        semaphore = asyncio.Semaphore(self.config.parallel_workers)
        
        async def run_with_semaphore():
            async with semaphore:
                return await self.run_single(prompt_config.prompt)
        
        # Run all iterations in parallel
        tasks = [run_with_semaphore() for _ in range(n)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        wins = 0
        losses = 0
        errors = 0
        sample_responses = []
        error_messages = []
        
        for result in results:
            if isinstance(result, BudgetExceededError):
                raise result
            elif isinstance(result, Exception):
                errors += 1
                if len(error_messages) < 3:
                    error_messages.append(str(result))
            else:
                success, response, tokens = result
                
                if self.config.use_live_llm:
                    self.cost_tracker.add_usage(
                        input_tokens=int(tokens * 0.7),
                        output_tokens=int(tokens * 0.3)
                    )
                
                if success:
                    wins += 1
                else:
                    losses += 1
                
                if len(sample_responses) < 3:
                    sample_responses.append(response)
        
        total = wins + losses
        actual_rate = wins / total if total > 0 else 0.0
        within_tolerance = abs(actual_rate - prompt_config.expected_win_rate) <= self.config.tolerance
        
        return PromptResult(
            prompt_name=prompt_config.name,
            prompt_text=prompt_config.prompt[:100],
            category=prompt_config.category,
            expected_win_rate=prompt_config.expected_win_rate,
            actual_wins=wins,
            actual_losses=losses,
            actual_errors=errors,
            actual_win_rate=actual_rate,
            within_tolerance=within_tolerance,
            sample_responses=sample_responses,
            errors=error_messages,
        )
    
    async def run_with_prompts(self, prompts: List[PromptConfig]) -> SimulationReport:
        """Run simulation with provided prompts"""
        return await self._run_internal(prompts)
    
    async def run(self) -> SimulationReport:
        """Run full simulation with prompts from library"""
        prompts = load_prompt_library(self.config.challenge_name, self.config.difficulty)
        return await self._run_internal(prompts)
    
    async def _run_internal(self, prompts: List[PromptConfig]) -> SimulationReport:
        """Internal run method"""
        start_time = time.time()
        results: List[PromptResult] = []
        anomalies = []
        
        total_iterations = len(prompts) * self.config.runs_per_prompt
        completed_iterations = 0
        
        print(f"\n🎮 Running {self.config.challenge_name} simulation")
        print(f"   Difficulty: {self.config.difficulty}")
        print(f"   Prompts: {len(prompts)}")
        print(f"   Runs per prompt: {self.config.runs_per_prompt}")
        print(f"   Total iterations: {total_iterations:,}")
        print(f"   Parallel workers: {self.config.parallel_workers}")
        print(f"   Budget: ${self.config.budget_usd:.2f}")
        print()
        
        def print_progress(completed: int, total: int, elapsed: float):
            pct = completed / total * 100 if total > 0 else 0
            rate = completed / elapsed if elapsed > 0 else 0
            eta = (total - completed) / rate if rate > 0 else 0
            bar_len = 30
            filled = int(bar_len * completed / total) if total > 0 else 0
            bar = "█" * filled + "░" * (bar_len - filled)
            print(f"\r   [{bar}] {pct:.0f}% | {completed}/{total} | {rate:.1f}/s | ETA: {eta:.0f}s | ${self.cost_tracker.spent_usd:.4f}", end="", flush=True)
        
        # Run ALL prompts in parallel for maximum speed
        semaphore = asyncio.Semaphore(self.config.parallel_workers)
        completed = [0]  # Use list for closure
        
        async def run_one_prompt(prompt_config):
            try:
                result = await self.run_prompt_n_times(prompt_config, self.config.runs_per_prompt)
                completed[0] += result.total_runs
                elapsed = time.time() - start_time
                print_progress(completed[0], total_iterations, elapsed)
                return result
            except Exception as e:
                return e
        
        # Launch all prompts concurrently
        tasks = [run_one_prompt(p) for p in prompts]
        all_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for prompt_config, result in zip(prompts, all_results):
            if isinstance(result, BudgetExceededError):
                print(f"\n⚠️  Budget exceeded")
                break
            elif isinstance(result, Exception):
                print(f"\n   ❌ {prompt_config.name}: {result}")
                continue
            
            results.append(result)
            
            if not result.within_tolerance:
                anomalies.append({
                    "prompt": result.prompt_name,
                    "category": result.category,
                    "expected": result.expected_win_rate,
                    "actual": result.actual_win_rate,
                    "deviation": result.deviation,
                    "sample_response": result.sample_responses[0] if result.sample_responses else "",
                })
        
        print()  # New line after progress bar
        
        duration = time.time() - start_time
        
        within_tolerance = sum(1 for r in results if r.within_tolerance)
        outside_tolerance = len(results) - within_tolerance
        total_runs = sum(r.total_runs for r in results)
        
        report = SimulationReport(
            challenge=self.config.challenge_name,
            difficulty=self.config.difficulty,
            total_runs=total_runs,
            total_prompts=len(results),
            prompts_within_tolerance=within_tolerance,
            prompts_outside_tolerance=outside_tolerance,
            total_cost_usd=self.cost_tracker.spent_usd,
            total_tokens=self.cost_tracker.total_tokens,
            prompt_results=results,
            anomalies=anomalies,
            duration_seconds=duration,
        )
        
        print()
        print(f"✅ Simulation complete in {duration:.1f}s")
        print(f"   {self.cost_tracker.summary()}")
        print(f"   Results: {within_tolerance}/{len(results)} within tolerance")
        print(f"   Speed: {total_runs / duration:.0f} runs/sec")
        if anomalies:
            print(f"   ⚠️  {len(anomalies)} anomalies found")
        
        return report


async def run_simulation(config: SimulationConfig) -> SimulationReport:
    """Convenience function to run a simulation"""
    runner = SimulationRunner(config)
    return await runner.run()


async def run_simulation_with_prompts(config: SimulationConfig, prompts: List[PromptConfig]) -> SimulationReport:
    """Run simulation with custom prompts (e.g., LLM-generated)"""
    runner = SimulationRunner(config)
    return await runner.run_with_prompts(prompts)
