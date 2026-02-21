"""Test model router — resolution, tiers, pricing."""

import os
from pathlib import Path
from unittest.mock import patch

from sis.llm.model_router import ModelRouter
from sis.orchestrator.cost_tracker import MODEL_PRICING


class TestModelRouter:
    def setup_method(self):
        ModelRouter.reset()

    def teardown_method(self):
        ModelRouter.reset()

    def test_singleton(self):
        r1 = ModelRouter.get_instance()
        r2 = ModelRouter.get_instance()
        assert r1 is r2

    def test_reset(self):
        r1 = ModelRouter.get_instance()
        ModelRouter.reset()
        r2 = ModelRouter.get_instance()
        assert r1 is not r2

    def test_get_model_from_yaml(self):
        router = ModelRouter.get_instance()
        model = router.get_model("agent_1")
        assert "haiku" in model

    def test_get_model_agent_10_opus(self):
        router = ModelRouter.get_instance()
        model = router.get_model("agent_10")
        assert "opus" in model

    def test_get_model_default_fallback(self):
        router = ModelRouter.get_instance()
        model = router.get_model("nonexistent_agent")
        assert "sonnet" in model  # default

    def test_get_model_env_override(self):
        router = ModelRouter.get_instance()
        with patch.dict(os.environ, {"MODEL_AGENT_1": "custom/model"}):
            model = router.get_model("agent_1")
            assert model == "custom/model"

    def test_list_models(self):
        router = ModelRouter.get_instance()
        models = router.list_models()
        assert "agent_1" in models
        assert "agent_10" in models
        assert "chat" in models
        assert len(models) >= 10

    def test_get_tier_haiku(self):
        assert ModelRouter.get_tier("anthropic/claude-haiku-4-5-20251001") == "haiku"

    def test_get_tier_sonnet(self):
        assert ModelRouter.get_tier("anthropic/claude-sonnet-4-20250514") == "sonnet"

    def test_get_tier_opus(self):
        assert ModelRouter.get_tier("anthropic/claude-opus-4-20250514") == "opus"

    def test_get_tier_unknown(self):
        assert ModelRouter.get_tier("unknown-model") == "sonnet"

    def test_get_pricing_known_model(self):
        pricing = ModelRouter.get_pricing("anthropic/claude-haiku-4-5-20251001")
        assert pricing["input"] == 0.80
        assert pricing["output"] == 4.00

    def test_get_pricing_unknown_model(self):
        pricing = ModelRouter.get_pricing("totally-unknown")
        assert "input" in pricing
        assert "output" in pricing

    def test_calculate_cost(self):
        cost = ModelRouter.calculate_cost("anthropic/claude-haiku-4-5-20251001", 10000, 2000)
        assert cost > 0
        assert isinstance(cost, float)
