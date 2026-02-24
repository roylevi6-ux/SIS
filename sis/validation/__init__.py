"""Output validation — schema + content guardrails per PRD Section 7.10.

Three layers of validation:
1. validate_agent_output() — rules-based checks on individual agent output quality
2. validate_synthesis_output() — post-synthesis schema + NEVER-rule validation
3. apply_confidence_penalties() — automatic confidence adjustments
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def validate_agent_output(output: dict) -> list[str]:
    """Run PRD 7.10 validation rules on an agent envelope output.

    Args:
        output: Agent output dict (after model_dump)

    Returns:
        List of warning strings. Empty list = clean output.
    """
    warnings = []

    # Rule 1: Evidence citation required
    evidence = output.get("evidence", [])
    if not evidence:
        warnings.append("UNVERIFIED: No evidence citations provided")

    # Rule 2: Confidence-evidence alignment
    conf = output.get("confidence", {}).get("overall", 0)
    evidence_count = len(evidence)

    if conf >= 0.7 and evidence_count < 3:
        warnings.append(
            f"Confidence {conf:.0%} but only {evidence_count} citations "
            "(need 3+ for HIGH confidence)"
        )
    if conf >= 0.5 and evidence_count < 1:
        warnings.append(
            f"Confidence {conf:.0%} but zero citations "
            "(need 1+ for MODERATE confidence)"
        )

    # Rule 3: Sparse data ceiling
    if output.get("sparse_data_flag") and conf > 0.75:
        warnings.append(
            f"sparse_data_flag=true but confidence={conf:.0%} exceeds 0.75 ceiling"
        )

    # Rule 4: Narrative presence
    narrative = output.get("narrative", "")
    if not narrative or len(narrative) < 50:
        warnings.append("Narrative missing or too short (< 50 chars)")

    # Rule 5: Agent ID present
    if not output.get("agent_id"):
        warnings.append("Missing agent_id field")

    return warnings


# ── Synthesis (Agent 10) validation ────────────────────────────────────

# Required top-level fields in synthesis output
_SYNTHESIS_REQUIRED_FIELDS = [
    "deal_memo",
    "inferred_stage",
    "inferred_stage_name",
    "health_score",
    "health_score_breakdown",
    "momentum_direction",
    "forecast_category",
    "top_positive_signals",
    "top_risks",
    "recommended_actions",
    "confidence_interval",
]


def validate_synthesis_output(
    synthesis_output: dict,
    agent_outputs: dict | None = None,
    deal_type: str = "new_logo",
) -> list[str]:
    """Validate Agent 10 synthesis output before persistence.

    Checks:
    1. Required fields present and non-empty
    2. Health score in valid range (0-100)
    3. Stage in valid range (1-7)
    4. Confidence in valid range (0.0-1.0)
    5. Momentum direction is valid enum
    6. Forecast category is valid enum
    7. NEVER rules (if agent_outputs provided)

    Returns:
        List of warning/error strings. Empty = clean.
    """
    warnings: list[str] = []

    # Check 1: Required fields
    for field in _SYNTHESIS_REQUIRED_FIELDS:
        val = synthesis_output.get(field)
        if val is None:
            warnings.append(f"SYNTHESIS_MISSING_FIELD: '{field}' is None")
        elif isinstance(val, str) and not val.strip():
            warnings.append(f"SYNTHESIS_EMPTY_FIELD: '{field}' is empty string")

    # Check 2: Health score range
    health = synthesis_output.get("health_score")
    if health is not None:
        if not isinstance(health, (int, float)) or health < 0 or health > 100:
            warnings.append(f"SYNTHESIS_INVALID_HEALTH: {health} not in [0, 100]")

    # Check 3: Stage range
    stage = synthesis_output.get("inferred_stage")
    if stage is not None:
        if not isinstance(stage, (int, float)) or stage < 1 or stage > 7:
            warnings.append(f"SYNTHESIS_INVALID_STAGE: {stage} not in [1, 7]")

    # Check 4: Confidence range
    conf_interval = synthesis_output.get("confidence_interval", {})
    if isinstance(conf_interval, dict):
        overall = conf_interval.get("overall_confidence")
        if overall is not None:
            if not isinstance(overall, (int, float)) or overall < 0.0 or overall > 1.0:
                warnings.append(f"SYNTHESIS_INVALID_CONFIDENCE: {overall} not in [0.0, 1.0]")

    # Check 5: Momentum direction
    valid_momentum = {"Improving", "Stable", "Declining", "Unknown"}
    momentum = synthesis_output.get("momentum_direction")
    if momentum and momentum not in valid_momentum:
        warnings.append(f"SYNTHESIS_INVALID_MOMENTUM: '{momentum}' not in {valid_momentum}")

    # Check 6: Forecast category
    valid_forecasts = {"Commit", "Realistic", "Upside", "At Risk"}
    forecast = synthesis_output.get("forecast_category")
    if forecast and forecast not in valid_forecasts:
        warnings.append(f"SYNTHESIS_INVALID_FORECAST: '{forecast}' not in {valid_forecasts}")

    # Check 7: NEVER rules (if agent outputs provided)
    if agent_outputs:
        try:
            from sis.validation.never_rules import check_all_never_rules
            violations = check_all_never_rules(agent_outputs, synthesis_output, deal_type=deal_type)
            for v in violations:
                warnings.append(f"NEVER_RULE_{v.rule_id}: {v.description}")
        except Exception as e:
            logger.warning("Failed to run NEVER rules: %s", e)

    # Check 8: Deal memo minimum length
    memo = synthesis_output.get("deal_memo", "")
    if isinstance(memo, str) and len(memo) < 100:
        warnings.append(f"SYNTHESIS_SHORT_MEMO: deal_memo is {len(memo)} chars (min 100)")

    return warnings


def apply_confidence_penalties(
    raw_confidence: float,
    transcript_count: int,
    most_recent_transcript_age_days: Optional[int] = None,
    key_stakeholder_absent: bool = False,
    contradicting_evidence: bool = False,
    sparse_data_flag: bool = False,
) -> tuple[float, list[str]]:
    """Apply automatic confidence penalties per PRD 7.4.

    Args:
        raw_confidence: The LLM-provided confidence score (0.0-1.0)
        transcript_count: Number of transcripts analyzed
        most_recent_transcript_age_days: Days since most recent transcript
        key_stakeholder_absent: Whether a key stakeholder is absent from data
        contradicting_evidence: Whether contradicting evidence was found
        sparse_data_flag: Whether the sparse data flag is set

    Returns:
        Tuple of (adjusted_confidence, list of penalty reasons applied)
    """
    adjusted = raw_confidence
    reasons: list[str] = []

    if transcript_count == 1:
        adjusted -= 0.15
        reasons.append("Single transcript: -0.15")

    if key_stakeholder_absent:
        adjusted -= 0.10
        reasons.append("Key stakeholder absent: -0.10")

    if contradicting_evidence:
        adjusted -= 0.10
        reasons.append("Contradicting evidence: -0.10")

    if most_recent_transcript_age_days is not None and most_recent_transcript_age_days > 30:
        adjusted -= 0.05
        reasons.append("Stale data (>30 days): -0.05")

    if sparse_data_flag:
        if adjusted > 0.75:
            adjusted = 0.75
            reasons.append("Sparse data ceiling applied: capped at 0.75")

    adjusted = max(0.0, min(1.0, adjusted))

    return adjusted, reasons
