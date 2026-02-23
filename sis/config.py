"""SIS configuration — loads from .env and YAML config files.

Config loading priority (per Technical Architecture Section 5.2, Rule 4):
  1. Environment variables (highest priority — deployment overrides)
  2. YAML config files in config/ (runtime tunable)
  3. Hardcoded defaults (fallback)
"""

import logging
import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load .env from project root
PROJECT_ROOT = Path(__file__).parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"
load_dotenv(PROJECT_ROOT / ".env")


# ---------------------------------------------------------------------------
# YAML config loaders
# ---------------------------------------------------------------------------

def _load_yaml(path: Path) -> dict:
    """Load a YAML file, returning empty dict if missing."""
    if path.exists():
        with open(path) as f:
            return yaml.safe_load(f) or {}
    logger.warning("Config file not found: %s — using defaults", path)
    return {}


def _load_models_config() -> dict:
    """Load model routing from config/models.yml."""
    data = _load_yaml(CONFIG_DIR / "models.yml")
    return data.get("model_routing", {})


_MODELS_CONFIG = _load_models_config()


def _get_model(agent_key: str, default: str) -> str:
    """Resolve model for an agent: env var > YAML > hardcoded default."""
    entry = _MODELS_CONFIG.get(agent_key, {})
    env_var = entry.get("env_override", "")
    yaml_model = entry.get("model", default)
    if env_var:
        return os.getenv(env_var, yaml_model)
    return yaml_model


# --- API Configuration (via Riskified LLM Proxy) ---
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_BASE_URL = os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com")

# Model assignments: resolved from config/models.yml with env var overrides
MODEL_AGENT_1 = _get_model("agent_1", "anthropic/claude-haiku-4-5-20251001")
MODEL_AGENTS_2_8 = _get_model("agent_2", "anthropic/claude-sonnet-4-20250514")
MODEL_AGENT_9 = _get_model("agent_9", "anthropic/claude-sonnet-4-20250514")
MODEL_AGENT_10 = _get_model("agent_10", "anthropic/claude-opus-4-20250514")
MODEL_CHAT = _get_model("chat", "anthropic/claude-sonnet-4-20250514")

# Backwards compat aliases (used by test scripts and legacy imports)
MODEL_AGENTS_1_8 = MODEL_AGENTS_2_8
MODEL_AGENTS_9_10 = MODEL_AGENT_10

# --- Database ---
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///data/sis.db")

# --- Token Budgets (per Technical Architecture Section 3.4) ---
MAX_TOKENS_PER_TRANSCRIPT = 8_000
MAX_TRANSCRIPTS_PER_ACCOUNT = 5
TOTAL_CONTEXT_BUDGET = 60_000
MAX_OUTPUT_TOKENS_PER_AGENT = 3_500
MAX_OUTPUT_TOKENS_SYNTHESIS = 8_000

# --- Alerts (defaults; overridden by calibration YAML) ---
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")
SCORE_DROP_ALERT_THRESHOLD = 15
STALE_CALL_DAYS_THRESHOLD = 30

# --- Google Drive Integration ---
GOOGLE_DRIVE_TRANSCRIPTS_PATH = os.getenv("GOOGLE_DRIVE_TRANSCRIPTS_PATH", "")


# ---------------------------------------------------------------------------
# Calibration config
# ---------------------------------------------------------------------------

def load_calibration_config() -> dict:
    """Load calibration config from config/calibration/current.yml.

    Falls back to legacy path (sis/prompts/calibration/config.yaml),
    then to hardcoded defaults. Per PRD Section 7.9.
    """
    # Primary: config/calibration/current.yml (follows symlink to versioned file)
    primary = CONFIG_DIR / "calibration" / "current.yml"
    if primary.exists():
        with open(primary) as f:
            return yaml.safe_load(f) or _default_calibration_config()

    # Legacy fallback
    legacy = PROJECT_ROOT / "sis" / "prompts" / "calibration" / "config.yaml"
    if legacy.exists():
        logger.info("Using legacy calibration config at %s", legacy)
        with open(legacy) as f:
            return yaml.safe_load(f) or _default_calibration_config()

    logger.warning("No calibration config found — using hardcoded defaults")
    return _default_calibration_config()


def _default_calibration_config() -> dict:
    """Hardcoded fallback calibration values from PRD Section 7.9.

    Nested by deal type: global, new_logo, expansion, alerts.
    """
    return {
        "global": {
            "confidence_ceiling_sparse_data": 0.60,
            "sparse_data_threshold": 3,
            "stale_signal_days": 30,
        },
        "new_logo": {
            "agent_6_economic_buyer": {
                "eb_absence_health_ceiling": 70,
                "secondhand_mention_counts_as_engaged": False,
            },
            "synthesis_agent_10": {
                "health_score_weights": {
                    "economic_buyer_engagement": 20,
                    "stage_appropriateness": 15,
                    "momentum_quality": 15,
                    "technical_path_clarity": 10,
                    "competitive_position": 10,
                    "stakeholder_completeness": 10,
                    "commitment_quality": 10,
                    "commercial_clarity": 10,
                },
                "forecast_commit_minimum_health": 75,
                "forecast_at_risk_maximum_health": 45,
            },
        },
        "expansion": {
            "agent_0e_account_health": {
                "relationship_health_weight_in_score": 15,
            },
            "agent_6_economic_buyer": {
                "eb_absence_health_ceiling": 85,
                "secondhand_mention_counts_as_engaged": False,
            },
            "synthesis_agent_10": {
                "health_score_weights": {
                    "account_relationship_health": 15,
                    "economic_buyer_engagement": 15,
                    "stage_appropriateness": 10,
                    "momentum_quality": 15,
                    "technical_path_clarity": 10,
                    "competitive_position": 5,
                    "stakeholder_completeness": 10,
                    "commitment_quality": 10,
                    "commercial_clarity": 10,
                },
                "forecast_commit_minimum_health": 65,
                "forecast_at_risk_maximum_health": 40,
            },
        },
        "alerts": {
            "score_drop_threshold": 15,
            "stale_call_days": 30,
            "forecast_flip_alert": True,
        },
    }


def load_agents_config() -> dict:
    """Load agent registry from config/agents.yml."""
    data = _load_yaml(CONFIG_DIR / "agents.yml")
    return data.get("agents", {})


def load_stage_relevance() -> dict:
    """Load agent-stage relevance matrix from config/stage_relevance.yml.

    Returns dict mapping agent_id -> {stage_N: weight} per Section 7.5.
    """
    data = _load_yaml(CONFIG_DIR / "stage_relevance.yml")
    return data.get("stage_relevance", {})
