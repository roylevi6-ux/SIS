"""Rep Scorecard service — behavioral dimension scoring per PRD P0-22.

Computes 4 dimensions per rep from agent analysis data:
  1. Stakeholder Engagement (Agent 2 — Relationship & Power Map)
  2. Objection Handling (Agent 3 — Commercial & Risk)
  3. Commercial Progression (Agent 4 — Momentum & Engagement)
  4. Next-Step Setting (Agent 7 — MSP & Next Steps)
"""

from __future__ import annotations

import json
from typing import Optional

from sis.db.session import get_session
from sis.db.models import Account, AgentAnalysis, DealAssessment


DIMENSIONS = [
    "Stakeholder Engagement",
    "Objection Handling",
    "Commercial Progression",
    "Next-Step Setting",
]

# Map agent_id prefixes to dimensions
AGENT_DIMENSION_MAP = {
    "agent_2": "Stakeholder Engagement",
    "agent_3": "Objection Handling",
    "agent_4": "Commercial Progression",
    "agent_7": "Next-Step Setting",
}


def _safe_json(val, default=None):
    if default is None:
        default = []
    if not val:
        return default
    try:
        return json.loads(val)
    except (json.JSONDecodeError, TypeError):
        return default


def score_from_confidence(confidence: float | None) -> int:
    """Convert a 0-1 confidence to a 0-100 score."""
    if confidence is None:
        return 50  # neutral default
    return max(0, min(100, round(confidence * 100)))


def score_from_findings(findings_json: str | None, dimension: str) -> int:
    """Extract a score from agent findings JSON based on dimension heuristics."""
    findings = _safe_json(findings_json, {})
    if not isinstance(findings, dict):
        return 50

    if dimension == "Objection Handling":
        # Look for risk counts, objection handling quality
        risks = findings.get("risks", findings.get("open_risks", []))
        if isinstance(risks, list):
            # Fewer unhandled risks = better score
            return max(20, 100 - len(risks) * 15)
        return 50

    if dimension == "Next-Step Setting":
        # Look for next steps quality
        steps = findings.get("next_steps", findings.get("recommended_actions", []))
        if isinstance(steps, list) and steps:
            # More concrete next steps = better
            return min(100, 50 + len(steps) * 10)
        return 40

    return 50


def score_from_momentum(momentum: str | None) -> int:
    """Convert momentum direction to a numeric score."""
    return {"Improving": 80, "Stable": 55, "Declining": 25}.get(momentum or "", 50)


def get_rep_scorecard(ae_owner: Optional[str] = None) -> list[dict]:
    """Compute behavioral scorecards for reps.

    Args:
        ae_owner: Filter to a single rep. None = all reps.

    Returns:
        List of rep scorecard dicts with dimensions and account details.
    """
    with get_session() as session:
        query = session.query(Account)
        if ae_owner:
            query = query.filter_by(ae_owner=ae_owner)
        accounts = query.all()

        # Group accounts by rep
        reps: dict[str, list] = {}
        for acct in accounts:
            rep = acct.ae_owner or "Unassigned"
            if rep not in reps:
                reps[rep] = []

            # Latest assessment
            latest_assessment = (
                session.query(DealAssessment)
                .filter_by(account_id=acct.id)
                .order_by(DealAssessment.created_at.desc())
                .first()
            )

            if not latest_assessment:
                reps[rep].append({
                    "account_id": acct.id,
                    "account_name": acct.account_name,
                    "scored": False,
                })
                continue

            # Get agent analyses for the latest run
            agent_rows = (
                session.query(AgentAnalysis)
                .filter_by(analysis_run_id=latest_assessment.analysis_run_id)
                .all()
            )

            # Compute dimension scores from agent data
            dimension_scores = {}
            for agent in agent_rows:
                for prefix, dim in AGENT_DIMENSION_MAP.items():
                    if agent.agent_id.startswith(prefix):
                        if dim == "Stakeholder Engagement":
                            dimension_scores[dim] = score_from_confidence(agent.confidence_overall)
                        elif dim == "Commercial Progression":
                            dimension_scores[dim] = score_from_momentum(
                                latest_assessment.momentum_direction
                            )
                        else:
                            dimension_scores[dim] = score_from_findings(
                                agent.findings, dim
                            )

            # Fill missing dimensions
            for dim in DIMENSIONS:
                if dim not in dimension_scores:
                    dimension_scores[dim] = 50

            reps[rep].append({
                "account_id": acct.id,
                "account_name": acct.account_name,
                "scored": True,
                "health_score": latest_assessment.health_score,
                "dimensions": dimension_scores,
            })

        # Build scorecard per rep
        scorecards = []
        for rep_name, rep_accounts in sorted(reps.items()):
            scored_accounts = [a for a in rep_accounts if a.get("scored")]

            # Average dimensions across accounts
            avg_dimensions = {}
            for dim in DIMENSIONS:
                scores = [a["dimensions"][dim] for a in scored_accounts if "dimensions" in a]
                avg_dimensions[dim] = round(sum(scores) / len(scores), 1) if scores else None

            overall = (
                round(sum(v for v in avg_dimensions.values() if v is not None)
                      / sum(1 for v in avg_dimensions.values() if v is not None), 1)
                if any(v is not None for v in avg_dimensions.values())
                else None
            )

            scorecards.append({
                "rep_name": rep_name,
                "total_accounts": len(rep_accounts),
                "scored_accounts": len(scored_accounts),
                "dimensions": avg_dimensions,
                "overall_score": overall,
                "accounts": rep_accounts,
            })

        scorecards.sort(key=lambda s: -(s["overall_score"] or 0))
        return scorecards
