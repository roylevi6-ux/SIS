"""Test orchestrator — budget, cost_tracker, retry, pipeline with mocks."""

import asyncio
import pytest

from sis.orchestrator.cost_tracker import RunCostSummary, calculate_cost, MODEL_PRICING
from sis.orchestrator.budget import RunBudget
from sis.orchestrator.retry import (
    RetryConfig, get_retry_config, is_retryable, compute_delay, TIER_CONFIGS,
)


class TestCostTracker:
    def test_calculate_cost_haiku(self):
        cost = calculate_cost("anthropic/claude-haiku-4-5-20251001", 10000, 2000)
        expected = 10000 * 0.80 / 1_000_000 + 2000 * 4.00 / 1_000_000
        assert abs(cost - expected) < 0.0001

    def test_calculate_cost_sonnet(self):
        cost = calculate_cost("anthropic/claude-sonnet-4-20250514", 10000, 2000)
        expected = 10000 * 3.00 / 1_000_000 + 2000 * 15.00 / 1_000_000
        assert abs(cost - expected) < 0.0001

    def test_calculate_cost_opus(self):
        cost = calculate_cost("anthropic/claude-opus-4-20250514", 10000, 2000)
        expected = 10000 * 15.00 / 1_000_000 + 2000 * 75.00 / 1_000_000
        assert abs(cost - expected) < 0.0001

    def test_calculate_cost_unknown_model(self):
        cost = calculate_cost("unknown-model", 10000, 2000)
        # Should use default pricing (sonnet-level)
        expected = 10000 * 3.00 / 1_000_000 + 2000 * 15.00 / 1_000_000
        assert abs(cost - expected) < 0.0001

    def test_run_cost_summary(self):
        summary = RunCostSummary()
        summary.add("agent_1", "anthropic/claude-haiku-4-5-20251001", 5000, 1000, 2.5)
        summary.add("agent_2", "anthropic/claude-sonnet-4-20250514", 8000, 2000, 4.0)

        assert summary.total_input_tokens == 13000
        assert summary.total_output_tokens == 3000
        assert summary.total_cost_usd > 0
        assert summary.total_elapsed_seconds == 6.5
        assert len(summary.agent_costs) == 2

    def test_run_cost_summary_to_dict(self):
        summary = RunCostSummary()
        summary.add("agent_1", "anthropic/claude-haiku-4-5-20251001", 5000, 1000, 2.5)
        d = summary.to_dict()
        assert "total_input_tokens" in d
        assert "agents" in d
        assert len(d["agents"]) == 1

    def test_model_pricing_has_all_tiers(self):
        has_haiku = any("haiku" in k for k in MODEL_PRICING)
        has_sonnet = any("sonnet" in k for k in MODEL_PRICING)
        has_opus = any("opus" in k for k in MODEL_PRICING)
        assert has_haiku and has_sonnet and has_opus


class TestBudget:
    def test_within_budget(self):
        budget = RunBudget()
        summary = RunCostSummary()
        summary.add("agent_1", "anthropic/claude-haiku-4-5-20251001", 5000, 1000, 2.0)
        violations = budget.check(summary, [])
        assert len(violations) == 0
        assert not budget.should_abort(summary, [])

    def test_input_token_exceeded(self):
        budget = RunBudget(max_input_tokens=1000)
        summary = RunCostSummary()
        summary.add("agent_1", "anthropic/claude-haiku-4-5-20251001", 5000, 100, 1.0)
        violations = budget.check(summary, [])
        assert any("Input token" in v for v in violations)
        assert budget.should_abort(summary, [])

    def test_cost_exceeded(self):
        budget = RunBudget(max_total_cost_usd=0.001)
        summary = RunCostSummary()
        summary.add("agent_1", "anthropic/claude-opus-4-20250514", 50000, 10000, 5.0)
        assert budget.should_abort(summary, [])

    def test_too_many_failures(self):
        budget = RunBudget(max_agents_failed=2)
        summary = RunCostSummary()
        errors = ["err1", "err2", "err3"]
        violations = budget.check(summary, errors)
        assert any("failures" in v for v in violations)


class TestRetry:
    def test_get_retry_config_haiku(self):
        config = get_retry_config("anthropic/claude-haiku-4-5-20251001")
        assert config.max_retries == 3

    def test_get_retry_config_sonnet(self):
        config = get_retry_config("anthropic/claude-sonnet-4-20250514")
        assert config.max_retries == 2

    def test_get_retry_config_opus(self):
        config = get_retry_config("anthropic/claude-opus-4-20250514")
        assert config.max_retries == 1

    def test_is_retryable_rate_limit(self):
        assert is_retryable(Exception("rate_limit_error"))

    def test_is_retryable_timeout(self):
        assert is_retryable(Exception("timeout occurred"))

    def test_not_retryable_auth(self):
        assert not is_retryable(Exception("invalid_api_key"))

    def test_not_retryable_permission(self):
        assert not is_retryable(Exception("permission denied"))

    def test_compute_delay(self):
        config = RetryConfig(base_delay_seconds=1.0, backoff_factor=2.0, jitter=False)
        assert compute_delay(0, config) == 1.0
        assert compute_delay(1, config) == 2.0
        assert compute_delay(2, config) == 4.0

    def test_compute_delay_max_cap(self):
        config = RetryConfig(
            base_delay_seconds=1.0, backoff_factor=2.0,
            max_delay_seconds=5.0, jitter=False,
        )
        assert compute_delay(10, config) == 5.0

    def test_tier_configs_exist(self):
        assert "haiku" in TIER_CONFIGS
        assert "sonnet" in TIER_CONFIGS
        assert "opus" in TIER_CONFIGS
