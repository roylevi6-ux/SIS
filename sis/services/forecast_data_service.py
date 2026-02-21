"""Forecast data service — data access for forecast comparison UI per PRD P0-21."""

from __future__ import annotations

from typing import Optional

from sis.db.session import get_session
from sis.db.models import Account, DealAssessment


def load_forecast_data(team: Optional[str] = None) -> list[dict]:
    """Load deal-level forecast data for the comparison view.

    Returns list of dicts with account info, AI/IC forecasts, health, momentum, divergence.
    """
    with get_session() as session:
        query = session.query(Account)
        if team:
            query = query.filter_by(team_name=team)
        accounts = query.all()

        rows = []
        for acct in accounts:
            latest = (
                session.query(DealAssessment)
                .filter_by(account_id=acct.id)
                .order_by(DealAssessment.created_at.desc())
                .first()
            )
            if not latest:
                continue
            rows.append({
                "account_id": acct.id,
                "account_name": acct.account_name,
                "mrr": acct.mrr_estimate or 0,
                "team_name": acct.team_name or "Unassigned",
                "ae_owner": acct.ae_owner or "N/A",
                "ai_forecast": latest.ai_forecast_category,
                "ic_forecast": acct.ic_forecast_category,
                "health_score": latest.health_score,
                "momentum": latest.momentum_direction,
                "divergence": bool(latest.divergence_flag),
            })
    return rows


def get_team_names() -> list[str]:
    """Return distinct non-null team names."""
    with get_session() as session:
        results = session.query(Account.team_name).distinct().all()
        return [r[0] for r in results if r[0]]
