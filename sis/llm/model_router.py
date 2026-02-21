"""Model router — singleton for agent-to-model resolution.

Reads config/models.yml and provides model lookup, tier classification,
and pricing calculations. Additive module — existing config.py constants
continue to work unchanged.
"""

from __future__ import annotations

import os
from pathlib import Path

import yaml

from sis.orchestrator.cost_tracker import MODEL_PRICING, DEFAULT_PRICING, calculate_cost


_CONFIG_PATH = Path(__file__).parent.parent.parent / "config" / "models.yml"


class ModelRouter:
    """Singleton that resolves agent → model mappings from YAML + env overrides."""

    _instance: ModelRouter | None = None

    def __init__(self, config_path: Path | None = None) -> None:
        path = config_path or _CONFIG_PATH
        if path.exists():
            with open(path) as f:
                data = yaml.safe_load(f) or {}
        else:
            data = {}
        self._routing: dict = data.get("model_routing", {})

    @classmethod
    def get_instance(cls) -> ModelRouter:
        """Get or create the singleton."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset singleton (for testing)."""
        cls._instance = None

    def get_model(self, agent_key: str, default: str = "anthropic/claude-sonnet-4-20250514") -> str:
        """Resolve model for an agent: env var > YAML > default."""
        entry = self._routing.get(agent_key, {})
        env_var = entry.get("env_override", "")
        yaml_model = entry.get("model", default)
        if env_var:
            return os.getenv(env_var, yaml_model)
        return yaml_model

    def list_models(self) -> dict[str, str]:
        """Return dict of agent_key → resolved model string."""
        return {key: self.get_model(key) for key in self._routing}

    @staticmethod
    def get_tier(model: str) -> str:
        """Classify model into tier: 'haiku', 'sonnet', or 'opus'."""
        model_lower = model.lower()
        if "haiku" in model_lower:
            return "haiku"
        if "opus" in model_lower:
            return "opus"
        return "sonnet"

    @staticmethod
    def get_pricing(model: str) -> dict:
        """Get pricing dict (input/output per 1M tokens) for a model."""
        return MODEL_PRICING.get(model, DEFAULT_PRICING)

    @staticmethod
    def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
        """Calculate USD cost for a single LLM call."""
        return calculate_cost(model, input_tokens, output_tokens)
