"""Trend Analysis service — pipeline health change over time per PRD P1-3.

Per-deal and per-team health trajectories using DealAssessment time-series data.
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Optional

from sis.db.session import get_session
from sis.db.models import Account, DealAssessment


def get_deal_trends(
    account_id: Optional[str] = None,
    weeks: int = 4,
) -> list[dict]:
    """Per-deal health trajectory over N weeks.

    Returns list of deal trend dicts sorted by biggest movers first (abs delta).
    """
    cutoff = (datetime.now(timezone.utc) - timedelta(weeks=weeks)).isoformat()

    with get_session() as session:
        query = (
            session.query(DealAssessment, Account.account_name, Account.team_name, Account.ae_owner)
            .join(Account, DealAssessment.account_id == Account.id)
            .filter(DealAssessment.created_at >= cutoff)
            .order_by(DealAssessment.account_id, DealAssessment.created_at)
        )
        if account_id:
            query = query.filter(DealAssessment.account_id == account_id)

        rows = query.all()

        # Group by account
        by_account: dict[str, dict] = {}
        for assessment, acct_name, team_name, ae_owner in rows:
            aid = assessment.account_id
            if aid not in by_account:
                by_account[aid] = {
                    "account_id": aid,
                    "account_name": acct_name,
                    "team_name": team_name or "Unassigned",
                    "ae_owner": ae_owner or "Unassigned",
                    "data_points": [],
                }
            by_account[aid]["data_points"].append({
                "date": assessment.created_at[:10],
                "health_score": assessment.health_score,
                "momentum": assessment.momentum_direction,
                "forecast": assessment.ai_forecast_category,
            })

        # Compute trends
        trends = []
        for deal in by_account.values():
            points = deal["data_points"]
            first_score = points[0]["health_score"]
            last_score = points[-1]["health_score"]
            delta = last_score - first_score

            if delta >= 10:
                direction = "Improving"
            elif delta <= -10:
                direction = "Declining"
            else:
                direction = "Stable"

            trends.append({
                "account_id": deal["account_id"],
                "account_name": deal["account_name"],
                "team_name": deal["team_name"],
                "ae_owner": deal["ae_owner"],
                "data_points": points,
                "first_score": first_score,
                "last_score": last_score,
                "delta": delta,
                "trend_direction": direction,
            })

        # Sort by biggest movers first (abs delta descending)
        trends.sort(key=lambda t: -abs(t["delta"]))
        return trends


def get_team_trends(
    weeks: int = 4,
    deal_trends: list[dict] | None = None,
) -> list[dict]:
    """Aggregate deal trends per team.

    Returns list of team trend dicts sorted worst-trending first.
    Pass deal_trends to avoid redundant DB queries.
    """
    if deal_trends is None:
        deal_trends = get_deal_trends(weeks=weeks)

    by_team: dict[str, list[dict]] = {}
    for deal in deal_trends:
        team = deal["team_name"]
        if team not in by_team:
            by_team[team] = []
        by_team[team].append(deal)

    team_summaries = []
    for team_name, deals in by_team.items():
        avg_health = round(
            sum(d["last_score"] for d in deals) / len(deals), 1
        )
        avg_delta = round(
            sum(d["delta"] for d in deals) / len(deals), 1
        )
        improving = sum(1 for d in deals if d["trend_direction"] == "Improving")
        declining = sum(1 for d in deals if d["trend_direction"] == "Declining")
        stable = sum(1 for d in deals if d["trend_direction"] == "Stable")

        if avg_delta >= 10:
            team_direction = "Improving"
        elif avg_delta <= -10:
            team_direction = "Declining"
        else:
            team_direction = "Stable"

        team_summaries.append({
            "team_name": team_name,
            "deal_count": len(deals),
            "avg_health": avg_health,
            "avg_delta": avg_delta,
            "improving_count": improving,
            "declining_count": declining,
            "stable_count": stable,
            "team_direction": team_direction,
        })

    # Sort worst-trending first
    team_summaries.sort(key=lambda t: t["avg_delta"])
    return team_summaries


def get_portfolio_summary(
    weeks: int = 4,
    deal_trends: list[dict] | None = None,
) -> dict:
    """Portfolio-wide trend summary.

    Pass deal_trends to avoid redundant DB queries.
    """
    if deal_trends is None:
        deal_trends = get_deal_trends(weeks=weeks)

    if not deal_trends:
        return {
            "total_deals": 0,
            "improving": 0,
            "stable": 0,
            "declining": 0,
            "avg_delta": 0,
            "portfolio_direction": "Stable",
            "biggest_improver": None,
            "biggest_decliner": None,
        }

    improving = sum(1 for d in deal_trends if d["trend_direction"] == "Improving")
    declining = sum(1 for d in deal_trends if d["trend_direction"] == "Declining")
    stable = sum(1 for d in deal_trends if d["trend_direction"] == "Stable")
    avg_delta = round(sum(d["delta"] for d in deal_trends) / len(deal_trends), 1)

    if avg_delta >= 10:
        portfolio_direction = "Improving"
    elif avg_delta <= -10:
        portfolio_direction = "Declining"
    else:
        portfolio_direction = "Stable"

    # Biggest movers
    sorted_by_delta = sorted(deal_trends, key=lambda d: d["delta"])
    biggest_decliner = sorted_by_delta[0] if sorted_by_delta[0]["delta"] < 0 else None
    biggest_improver = sorted_by_delta[-1] if sorted_by_delta[-1]["delta"] > 0 else None

    return {
        "total_deals": len(deal_trends),
        "improving": improving,
        "stable": stable,
        "declining": declining,
        "avg_delta": avg_delta,
        "portfolio_direction": portfolio_direction,
        "biggest_improver": {
            "account_name": biggest_improver["account_name"],
            "delta": biggest_improver["delta"],
            "last_score": biggest_improver["last_score"],
        } if biggest_improver else None,
        "biggest_decliner": {
            "account_name": biggest_decliner["account_name"],
            "delta": biggest_decliner["delta"],
            "last_score": biggest_decliner["last_score"],
        } if biggest_decliner else None,
    }
