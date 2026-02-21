"""Calibration cycle tooling service — per PRD P0-18, Sec 7.9.

Analyzes feedback patterns, reads calibration config, and logs calibration changes.
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from pathlib import Path
from typing import Optional

import yaml

from sis.db.session import get_session
from sis.db.models import CalibrationLog, ScoreFeedback, AgentAnalysis

logger = logging.getLogger(__name__)

CONFIG_DIR = Path(__file__).parent.parent.parent / "config" / "calibration"


def get_feedback_patterns() -> dict:
    """Analyze feedback to identify patterns: top flagged reasons, agents, direction skew.

    Returns dict with:
    - by_reason: {reason: count}
    - by_agent: {agent_id: count} (from agent_analyses linked via deal_assessment)
    - direction_skew: {direction: count}
    - top_flagged_reasons: sorted list of (reason, count)
    """
    with get_session() as session:
        feedback_items = session.query(ScoreFeedback).all()

        by_reason: dict[str, int] = defaultdict(int)
        by_direction: dict[str, int] = defaultdict(int)

        for f in feedback_items:
            by_reason[f.reason_category] += 1
            by_direction[f.disagreement_direction] += 1

        # Identify which agents are most associated with flagged assessments
        by_agent: dict[str, int] = defaultdict(int)
        flagged_assessment_ids = [f.deal_assessment_id for f in feedback_items]

        if flagged_assessment_ids:
            # Find agent analyses from the same analysis runs
            from sis.db.models import DealAssessment
            assessments = (
                session.query(DealAssessment)
                .filter(DealAssessment.id.in_(flagged_assessment_ids))
                .all()
            )
            run_ids = [a.analysis_run_id for a in assessments]

            if run_ids:
                agent_analyses = (
                    session.query(AgentAnalysis)
                    .filter(AgentAnalysis.analysis_run_id.in_(run_ids))
                    .all()
                )
                for aa in agent_analyses:
                    by_agent[aa.agent_id] += 1

        # Direction skew per agent (too_high vs too_low)
        direction_per_agent: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        for f in feedback_items:
            # Use account_id to correlate
            agent_results = (
                session.query(AgentAnalysis.agent_id)
                .filter(AgentAnalysis.account_id == f.account_id)
                .distinct()
                .all()
            )
            for (agent_id,) in agent_results:
                direction_per_agent[agent_id][f.disagreement_direction] += 1

    top_flagged_reasons = sorted(by_reason.items(), key=lambda x: -x[1])

    return {
        "total_feedback": len(feedback_items),
        "by_reason": dict(by_reason),
        "by_direction": dict(by_direction),
        "by_agent": dict(by_agent),
        "direction_per_agent": {k: dict(v) for k, v in direction_per_agent.items()},
        "top_flagged_reasons": top_flagged_reasons,
    }


def get_current_calibration() -> dict:
    """Load the current calibration config from YAML."""
    current_path = CONFIG_DIR / "current.yml"
    if not current_path.exists():
        return {}
    with open(current_path) as f:
        return yaml.safe_load(f) or {}


def create_calibration_log(
    config_version: str,
    previous_version: Optional[str] = None,
    changes: Optional[str] = None,
    feedback_items_reviewed: int = 0,
    approved_by: Optional[str] = None,
) -> dict:
    """Persist a calibration change log entry."""
    with get_session() as session:
        log = CalibrationLog(
            config_version=config_version,
            config_previous_version=previous_version,
            config_changes=changes,
            feedback_items_reviewed=feedback_items_reviewed,
            approved_by=approved_by,
        )
        session.add(log)
        session.flush()
        return {
            "id": log.id,
            "config_version": log.config_version,
            "calibration_date": log.calibration_date,
            "approved_by": log.approved_by,
        }


def list_calibration_history() -> list[dict]:
    """All calibration logs ordered by date descending."""
    with get_session() as session:
        logs = (
            session.query(CalibrationLog)
            .order_by(CalibrationLog.calibration_date.desc())
            .all()
        )
        return [
            {
                "id": log.id,
                "calibration_date": log.calibration_date,
                "config_version": log.config_version,
                "config_previous_version": log.config_previous_version,
                "feedback_items_reviewed": log.feedback_items_reviewed,
                "config_changes": log.config_changes,
                "approved_by": log.approved_by,
                "created_at": log.created_at,
            }
            for log in logs
        ]
