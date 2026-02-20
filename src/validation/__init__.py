"""Output validation — schema + content guardrails per PRD Section 7.10.

Two layers of validation:
1. validate_agent_output() — rules-based checks on LLM output quality
2. apply_confidence_penalties() — automatic confidence adjustments
"""

from __future__ import annotations

from typing import Optional


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
