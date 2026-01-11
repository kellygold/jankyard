"""
Cost tracking and budget management for simulations
"""
from dataclasses import dataclass


class BudgetExceededError(Exception):
    """Raised when simulation exceeds budget"""
    pass


@dataclass
class CostTracker:
    """Track API costs and enforce budget limits"""
    
    budget_usd: float = 2.50
    spent_usd: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    
    # gpt-4o-mini pricing (per 1M tokens)
    INPUT_COST_PER_M = 0.15
    OUTPUT_COST_PER_M = 0.60
    
    def add_usage(self, input_tokens: int, output_tokens: int):
        """Record token usage and update cost"""
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens
        
        input_cost = (input_tokens * self.INPUT_COST_PER_M) / 1_000_000
        output_cost = (output_tokens * self.OUTPUT_COST_PER_M) / 1_000_000
        self.spent_usd += input_cost + output_cost
        
        if self.spent_usd >= self.budget_usd:
            raise BudgetExceededError(
                f"Budget exceeded: ${self.spent_usd:.4f} of ${self.budget_usd:.2f}"
            )
    
    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens
    
    @property
    def remaining_budget(self) -> float:
        return max(0, self.budget_usd - self.spent_usd)
    
    @property
    def budget_percent_used(self) -> float:
        if self.budget_usd == 0:
            return 100.0
        return (self.spent_usd / self.budget_usd) * 100
    
    def estimate_remaining_runs(self, avg_tokens_per_run: int = 1500) -> int:
        """Estimate how many more runs we can afford"""
        # Assume 70% input, 30% output ratio
        input_per_run = int(avg_tokens_per_run * 0.7)
        output_per_run = int(avg_tokens_per_run * 0.3)
        
        cost_per_run = (
            (input_per_run * self.INPUT_COST_PER_M) / 1_000_000 +
            (output_per_run * self.OUTPUT_COST_PER_M) / 1_000_000
        )
        
        if cost_per_run == 0:
            return 999999
        
        return int(self.remaining_budget / cost_per_run)
    
    def summary(self) -> str:
        return (
            f"💰 Cost: ${self.spent_usd:.4f} / ${self.budget_usd:.2f} "
            f"({self.budget_percent_used:.1f}%) | "
            f"Tokens: {self.total_tokens:,}"
        )
