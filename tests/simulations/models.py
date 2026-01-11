"""
Simulation data models
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime


@dataclass
class PromptConfig:
    """Configuration for a single test prompt"""
    name: str
    prompt: str
    note: str
    expected_win_rate: float
    category: str  # should_win, should_lose, edge_cases, adversarial


@dataclass
class PromptResult:
    """Result of running a prompt N times"""
    prompt_name: str
    prompt_text: str
    category: str
    expected_win_rate: float
    actual_wins: int
    actual_losses: int
    actual_errors: int
    actual_win_rate: float
    within_tolerance: bool
    sample_responses: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    
    @property
    def total_runs(self) -> int:
        return self.actual_wins + self.actual_losses + self.actual_errors
    
    @property
    def deviation(self) -> float:
        return abs(self.actual_win_rate - self.expected_win_rate)
    
    @property
    def status(self) -> str:
        if self.within_tolerance:
            return "✅"
        elif self.deviation > 0.25:
            return "❌"
        else:
            return "⚠️"


@dataclass
class SimulationConfig:
    """Configuration for a simulation run"""
    challenge_name: str
    difficulty: str
    runs_per_prompt: int = 100
    use_live_llm: bool = True
    parallel_workers: int = 50  # Tuned for ~100ms/call, stays under 3500 RPM
    output_dir: str = "tests/simulation_results"
    budget_usd: float = 2.50
    tolerance: float = 0.10  # ±10%


@dataclass
class SimulationReport:
    """Full report from a simulation run"""
    challenge: str
    difficulty: str
    total_runs: int
    total_prompts: int
    prompts_within_tolerance: int
    prompts_outside_tolerance: int
    total_cost_usd: float
    total_tokens: int
    prompt_results: List[PromptResult]
    anomalies: List[Dict[str, Any]]
    timestamp: datetime = field(default_factory=datetime.now)
    duration_seconds: float = 0.0
    
    @property
    def success_rate(self) -> float:
        if self.total_prompts == 0:
            return 0.0
        return self.prompts_within_tolerance / self.total_prompts
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "challenge": self.challenge,
            "difficulty": self.difficulty,
            "timestamp": self.timestamp.isoformat(),
            "duration_seconds": self.duration_seconds,
            "summary": {
                "total_runs": self.total_runs,
                "total_prompts": self.total_prompts,
                "prompts_within_tolerance": self.prompts_within_tolerance,
                "prompts_outside_tolerance": self.prompts_outside_tolerance,
                "total_cost_usd": round(self.total_cost_usd, 4),
                "total_tokens": self.total_tokens,
            },
            "results": [
                {
                    "name": r.prompt_name,
                    "category": r.category,
                    "expected_win_rate": r.expected_win_rate,
                    "actual_win_rate": round(r.actual_win_rate, 3),
                    "runs": r.total_runs,
                    "wins": r.actual_wins,
                    "losses": r.actual_losses,
                    "errors": r.actual_errors,
                    "within_tolerance": r.within_tolerance,
                    "status": r.status,
                }
                for r in self.prompt_results
            ],
            "anomalies": self.anomalies,
        }
