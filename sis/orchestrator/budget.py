"""Budget enforcement — per-run token and cost limits per Technical Architecture Section 3.5.

Prevents runaway costs by enforcing configurable limits on tokens and USD
spend per pipeline run. The pipeline checks the budget after each agent
completes and aborts if limits are exceeded.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from .cost_tracker import RunCostSummary

logger = logging.getLogger(__name__)


@dataclass
class RunBudget:
    """Configurable budget limits for a single pipeline run."""

    max_input_tokens: int = 500_000
    max_output_tokens: int = 100_000
    max_total_cost_usd: float = 5.00
    max_agents_failed: int = 3

    def check(self, cost_summary: RunCostSummary, errors: list[str]) -> list[str]:
        """Check current run state against budget limits.

        Returns:
            List of violation messages. Empty list = within budget.
        """
        violations = []

        if cost_summary.total_input_tokens > self.max_input_tokens:
            violations.append(
                f"Input token limit exceeded: {cost_summary.total_input_tokens:,} > {self.max_input_tokens:,}"
            )

        if cost_summary.total_output_tokens > self.max_output_tokens:
            violations.append(
                f"Output token limit exceeded: {cost_summary.total_output_tokens:,} > {self.max_output_tokens:,}"
            )

        if cost_summary.total_cost_usd > self.max_total_cost_usd:
            violations.append(
                f"Cost limit exceeded: ${cost_summary.total_cost_usd:.4f} > ${self.max_total_cost_usd:.2f}"
            )

        if len(errors) > self.max_agents_failed:
            violations.append(
                f"Too many agent failures: {len(errors)} > {self.max_agents_failed}"
            )

        if violations:
            for v in violations:
                logger.warning("Budget violation: %s", v)

        return violations

    def should_abort(self, cost_summary: RunCostSummary, errors: list[str]) -> bool:
        """Return True if the run should be aborted due to budget violations."""
        return len(self.check(cost_summary, errors)) > 0
