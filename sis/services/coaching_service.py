"""Coaching service — coaching log CRUD per PRD P1-2.

TL logs coaching feedback linked to rep behavioral dimensions, tracks incorporation.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sis.db.session import get_session
from sis.db.models import CoachingEntry, Account, DealAssessment, AgentAnalysis
from sis.services.rep_scorecard_service import (
    DIMENSIONS,
    AGENT_DIMENSION_MAP,
    score_from_confidence,
    score_from_findings,
    score_from_momentum,
)


def _get_dimension_score(session, account_id: str, dimension: str) -> int | None:
    """Compute current dimension score for an account."""
    latest = (
        session.query(DealAssessment)
        .filter_by(account_id=account_id)
        .order_by(DealAssessment.created_at.desc())
        .first()
    )
    if not latest:
        return None

    agents = (
        session.query(AgentAnalysis)
        .filter_by(analysis_run_id=latest.analysis_run_id)
        .all()
    )
    for agent in agents:
        for prefix, dim in AGENT_DIMENSION_MAP.items():
            if agent.agent_id.startswith(prefix) and dim == dimension:
                if dim == "Stakeholder Engagement":
                    return score_from_confidence(agent.confidence_overall)
                elif dim == "Commercial Progression":
                    return score_from_momentum(latest.momentum_direction)
                else:
                    return score_from_findings(agent.findings, dim)
    return None


def submit_coaching(
    account_id: str,
    rep_name: str,
    coach_name: str,
    dimension: str,
    feedback_text: str,
) -> dict:
    """Submit a coaching entry for a rep on a specific dimension."""
    if dimension not in DIMENSIONS:
        raise ValueError(f"dimension must be one of {DIMENSIONS}")
    if not rep_name.strip():
        raise ValueError("rep_name cannot be empty")
    if not coach_name.strip():
        raise ValueError("coach_name cannot be empty")
    if not feedback_text.strip():
        raise ValueError("feedback_text cannot be empty")

    with get_session() as session:
        acct = session.query(Account).filter_by(id=account_id).one_or_none()
        if not acct:
            raise ValueError(f"Account not found: {account_id}")

        # Snapshot current scores
        dim_score = _get_dimension_score(session, account_id, dimension)
        latest_assessment = (
            session.query(DealAssessment)
            .filter_by(account_id=account_id)
            .order_by(DealAssessment.created_at.desc())
            .first()
        )
        health_score = latest_assessment.health_score if latest_assessment else None

        entry = CoachingEntry(
            account_id=account_id,
            rep_name=rep_name,
            coach_name=coach_name,
            dimension=dimension,
            feedback_text=feedback_text.strip(),
            dimension_score_at_time=dim_score,
            health_score_at_time=health_score,
        )
        session.add(entry)
        session.flush()
        return {
            "id": entry.id,
            "account_id": entry.account_id,
            "rep_name": entry.rep_name,
            "dimension": entry.dimension,
            "dimension_score_at_time": entry.dimension_score_at_time,
            "health_score_at_time": entry.health_score_at_time,
        }


def list_coaching(
    rep_name: Optional[str] = None,
    account_id: Optional[str] = None,
    dimension: Optional[str] = None,
    incorporated: Optional[bool] = None,
) -> list[dict]:
    """List coaching entries with optional filters. Includes account_name via join."""
    with get_session() as session:
        query = (
            session.query(CoachingEntry, Account.account_name)
            .join(Account, CoachingEntry.account_id == Account.id)
        )
        if rep_name:
            query = query.filter(CoachingEntry.rep_name == rep_name)
        if account_id:
            query = query.filter(CoachingEntry.account_id == account_id)
        if dimension:
            query = query.filter(CoachingEntry.dimension == dimension)
        if incorporated is not None:
            query = query.filter(CoachingEntry.incorporated == (1 if incorporated else 0))

        results = query.order_by(CoachingEntry.coaching_date.desc()).all()
        return [
            {
                "id": e.id,
                "account_id": e.account_id,
                "account_name": acct_name,
                "rep_name": e.rep_name,
                "coach_name": e.coach_name,
                "dimension": e.dimension,
                "coaching_date": e.coaching_date,
                "feedback_text": e.feedback_text,
                "dimension_score_at_time": e.dimension_score_at_time,
                "health_score_at_time": e.health_score_at_time,
                "incorporated": bool(e.incorporated),
                "incorporated_at": e.incorporated_at,
                "incorporated_notes": e.incorporated_notes,
                "created_at": e.created_at,
            }
            for e, acct_name in results
        ]


def mark_incorporated(entry_id: str, notes: Optional[str] = None) -> dict:
    """Mark a coaching entry as incorporated."""
    with get_session() as session:
        entry = session.query(CoachingEntry).filter_by(id=entry_id).one_or_none()
        if not entry:
            raise ValueError(f"Coaching entry not found: {entry_id}")
        entry.incorporated = 1
        entry.incorporated_at = datetime.now(timezone.utc).isoformat()
        entry.incorporated_notes = notes
        session.flush()
        return {"id": entry.id, "incorporated": True}


def get_coaching_summary(rep_name: Optional[str] = None) -> dict:
    """Aggregate coaching stats: total, by dimension, incorporation rate."""
    entries = list_coaching(rep_name=rep_name)

    by_dimension = {}
    for dim in DIMENSIONS:
        dim_entries = [e for e in entries if e["dimension"] == dim]
        incorporated_count = sum(1 for e in dim_entries if e["incorporated"])
        by_dimension[dim] = {
            "total": len(dim_entries),
            "incorporated": incorporated_count,
            "rate": round(incorporated_count / len(dim_entries) * 100, 1) if dim_entries else 0,
        }

    total = len(entries)
    total_incorporated = sum(1 for e in entries if e["incorporated"])

    return {
        "total": total,
        "incorporated": total_incorporated,
        "incorporation_rate": round(total_incorporated / total * 100, 1) if total else 0,
        "by_dimension": by_dimension,
        "coaches": sorted(set(e["coach_name"] for e in entries)),
    }


def check_incorporation(rep_name: str) -> list[dict]:
    """Check pending coaching entries for score improvements.

    If a dimension score improved by 5+ points since coaching, suggest marking incorporated.
    """
    pending = list_coaching(rep_name=rep_name, incorporated=False)
    suggestions = []

    with get_session() as session:
        for entry in pending:
            if entry["dimension_score_at_time"] is None:
                continue
            current_score = _get_dimension_score(
                session, entry["account_id"], entry["dimension"]
            )
            if current_score is None:
                continue
            delta = current_score - entry["dimension_score_at_time"]
            if delta >= 5:
                suggestions.append({
                    "entry_id": entry["id"],
                    "account_name": entry["account_name"],
                    "dimension": entry["dimension"],
                    "score_at_time": entry["dimension_score_at_time"],
                    "current_score": current_score,
                    "delta": delta,
                    "feedback_text": entry["feedback_text"],
                })

    return suggestions
