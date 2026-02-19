"""SIS configuration — loads from .env and calibration YAML."""

import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

# Load .env from project root
PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(PROJECT_ROOT / ".env")


# --- API Configuration (via Riskified LLM Proxy) ---
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_BASE_URL = os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com")
MODEL_AGENTS_1_9 = os.getenv("MODEL_AGENTS_1_9", "anthropic/claude-sonnet-4-20250514")
MODEL_AGENT_10 = os.getenv("MODEL_AGENT_10", "anthropic/claude-opus-4-20250514")

# --- Database ---
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///data/sis.db")

# --- Token Budgets (per Technical Architecture) ---
MAX_TOKENS_PER_TRANSCRIPT = 8_000
MAX_TRANSCRIPTS_PER_ACCOUNT = 5
TOTAL_CONTEXT_BUDGET = 60_000
MAX_OUTPUT_TOKENS_PER_AGENT = 4_000

# --- Alerts ---
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")
SCORE_DROP_ALERT_THRESHOLD = 15
STALE_CALL_DAYS_THRESHOLD = 30


def load_calibration_config() -> dict:
    """Load calibration config from YAML. Separated from prompt logic per PRD Section 7.9."""
    config_path = PROJECT_ROOT / "src" / "prompts" / "calibration" / "config.yaml"
    if config_path.exists():
        with open(config_path) as f:
            return yaml.safe_load(f)
    return _default_calibration_config()


def _default_calibration_config() -> dict:
    """Default calibration values from PRD Section 7.9."""
    return {
        "global": {
            "confidence_ceiling_sparse_data": 0.60,
            "sparse_data_threshold": 3,
            "stale_signal_days": 30,
        },
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
    }
