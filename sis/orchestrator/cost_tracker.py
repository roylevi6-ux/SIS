"""Cost tracking — per-run token and cost aggregation.

Per Technical Architecture Section 3.4-3.5:
- Tracks tokens + cost per agent per run
- Haiku/Sonnet/Opus pricing from Anthropic (Feb 2026)
"""

from __future__ import annotations

from dataclasses import dataclass, field


# Pricing per 1M tokens (Anthropic, Feb 2026)
MODEL_PRICING = {
    # Haiku
    "anthropic/claude-haiku-4-5-20251001": {"input": 0.80, "output": 4.00},
    "claude-haiku-4-5-20251001": {"input": 0.80, "output": 4.00},
    # Sonnet
    "anthropic/claude-sonnet-4-20250514": {"input": 3.00, "output": 15.00},
    "claude-sonnet-4-20250514": {"input": 3.00, "output": 15.00},
    # Opus
    "anthropic/claude-opus-4-20250514": {"input": 15.00, "output": 75.00},
    "claude-opus-4-20250514": {"input": 15.00, "output": 75.00},
}

# Fallback pricing if model not recognized
DEFAULT_PRICING = {"input": 3.00, "output": 15.00}


@dataclass
class AgentCost:
    """Cost record for a single agent execution."""

    agent_id: str
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    elapsed_seconds: float
    retries: int


@dataclass
class RunCostSummary:
    """Aggregated cost summary for an entire pipeline run."""

    agent_costs: list[AgentCost] = field(default_factory=list)

    @property
    def total_input_tokens(self) -> int:
        return sum(c.input_tokens for c in self.agent_costs)

    @property
    def total_output_tokens(self) -> int:
        return sum(c.output_tokens for c in self.agent_costs)

    @property
    def total_cost_usd(self) -> float:
        return sum(c.cost_usd for c in self.agent_costs)

    @property
    def total_elapsed_seconds(self) -> float:
        return sum(c.elapsed_seconds for c in self.agent_costs)

    def add(self, agent_id: str, model: str, input_tokens: int,
            output_tokens: int, elapsed_seconds: float, retries: int = 0) -> None:
        """Record an agent's execution cost."""
        cost = calculate_cost(model, input_tokens, output_tokens)
        self.agent_costs.append(AgentCost(
            agent_id=agent_id,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost,
            elapsed_seconds=elapsed_seconds,
            retries=retries,
        ))

    def to_dict(self) -> dict:
        """Serialize for JSON storage in analysis_runs table."""
        return {
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_cost_usd": round(self.total_cost_usd, 4),
            "agents": [
                {
                    "agent_id": c.agent_id,
                    "model": c.model,
                    "input_tokens": c.input_tokens,
                    "output_tokens": c.output_tokens,
                    "cost_usd": round(c.cost_usd, 4),
                    "elapsed_seconds": round(c.elapsed_seconds, 1),
                    "retries": c.retries,
                }
                for c in self.agent_costs
            ],
        }


def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Calculate USD cost for a single LLM call."""
    pricing = MODEL_PRICING.get(model, DEFAULT_PRICING)
    return (
        input_tokens * pricing["input"] / 1_000_000
        + output_tokens * pricing["output"] / 1_000_000
    )
