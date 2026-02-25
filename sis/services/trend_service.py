"""Trend Analysis service — pipeline health change over time per PRD P1-3.

Per-deal and per-team health trajectories using DealAssessment time-series data.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from sis.db.session import get_session
from sis.db.models import Account, DealAssessment, User, Team, Quota


FORECAST_RANK = {"At Risk": 0, "Upside": 1, "Realistic": 2, "Commit": 3}

HEALTH_TIERS = {"healthy": 70, "at_risk": 45}  # >= 70 healthy, >= 45 at_risk, < 45 critical


def _iso_week(date_str: str) -> str:
    """Convert ISO 8601 timestamp to 'YYYY-WNN' for weekly grouping."""
    dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    year, week, _ = dt.isocalendar()
    return f"{year}-W{week:02d}"


def _get_assessments_in_window(
    db: Session,
    weeks: int,
    visible_user_ids: set[str] | None,
) -> list[tuple[DealAssessment, Account]]:
    """Fetch all assessments within time window, joined with Account.
    Returns list of (DealAssessment, Account) tuples, ordered by account_id, created_at ASC.
    """
    cutoff = (datetime.now(timezone.utc) - timedelta(weeks=weeks)).isoformat()
    query = (
        db.query(DealAssessment, Account)
        .join(Account, DealAssessment.account_id == Account.id)
        .filter(DealAssessment.created_at >= cutoff)
        .order_by(DealAssessment.account_id, DealAssessment.created_at)
    )
    if visible_user_ids is not None:
        query = query.filter(Account.owner_id.in_(visible_user_ids))
    return query.all()


def _latest_per_account(
    assessments: list[tuple[DealAssessment, Account]],
) -> dict[str, tuple[DealAssessment, Account]]:
    """From time-ordered list, return dict of account_id -> (latest_assessment, account)."""
    result: dict[str, tuple[DealAssessment, Account]] = {}
    for da, acct in assessments:
        result[da.account_id] = (da, acct)
    return result


def _group_by_week(
    assessments: list[tuple[DealAssessment, Account]],
) -> dict[str, list[tuple[DealAssessment, Account]]]:
    """Group assessments by ISO week. Returns dict of week_label -> list."""
    by_week: dict[str, list[tuple[DealAssessment, Account]]] = {}
    for da, acct in assessments:
        wk = _iso_week(da.created_at)
        by_week.setdefault(wk, []).append((da, acct))
    return by_week


def _latest_per_account_per_week(
    by_week: dict[str, list[tuple[DealAssessment, Account]]],
) -> dict[str, dict[str, tuple[DealAssessment, Account]]]:
    """For each week, keep only the latest assessment per account.
    Returns dict of week_label -> {account_id -> (assessment, account)}.
    """
    result: dict[str, dict[str, tuple[DealAssessment, Account]]] = {}
    for wk, items in by_week.items():
        latest: dict[str, tuple[DealAssessment, Account]] = {}
        for da, acct in items:
            latest[da.account_id] = (da, acct)  # items are pre-sorted ASC, last wins
        result[wk] = latest
    return result


def get_deal_health_trends(
    db: Session,
    weeks: int = 4,
    visible_user_ids: set[str] | None = None,
) -> dict:
    """Health distribution, biggest movers, component averages, weighted health."""
    rows = _get_assessments_in_window(db, weeks, visible_user_ids)
    if not rows:
        return {
            "distribution_over_time": [],
            "biggest_movers": [],
            "component_averages": [],
            "weighted_health": {"current": 0, "previous": 0, "delta": 0},
        }

    by_week = _group_by_week(rows)
    weekly_latest = _latest_per_account_per_week(by_week)
    sorted_weeks = sorted(weekly_latest.keys())

    # 1. Distribution over time
    distribution = []
    for wk in sorted_weeks:
        deals = weekly_latest[wk]
        healthy = sum(1 for da, _ in deals.values() if da.health_score >= 70)
        at_risk = sum(1 for da, _ in deals.values() if 45 <= da.health_score < 70)
        critical = sum(1 for da, _ in deals.values() if da.health_score < 45)
        distribution.append({"week": wk, "healthy": healthy, "at_risk": at_risk, "critical": critical})

    # 2. Biggest movers (first vs last score)
    by_account: dict[str, list[tuple[DealAssessment, Account]]] = {}
    for da, acct in rows:
        by_account.setdefault(da.account_id, []).append((da, acct))

    movers = []
    for aid, items in by_account.items():
        da_first, _ = items[0]
        da_last, acct = items[-1]
        delta = da_last.health_score - da_first.health_score
        direction = "Improving" if delta >= 10 else ("Declining" if delta <= -10 else "Stable")
        sparkline = [da.health_score for da, _ in items]
        movers.append({
            "account_id": aid,
            "account_name": acct.account_name,
            "mrr_estimate": acct.mrr_estimate or 0,
            "current_score": da_last.health_score,
            "delta": delta,
            "direction": direction,
            "sparkline": sparkline,
        })
    movers.sort(key=lambda m: -abs(m["delta"]))
    biggest_movers = movers[:10]

    # 3. Component averages from latest assessments
    latest = _latest_per_account(rows)
    comp_totals: dict[str, list[float]] = {}
    for da, _ in latest.values():
        try:
            breakdown = json.loads(da.health_breakdown) if isinstance(da.health_breakdown, str) else da.health_breakdown
            if isinstance(breakdown, list):
                for comp in breakdown:
                    name = comp.get("component", comp.get("name", "Unknown"))
                    score = comp.get("score", 0)
                    max_score = comp.get("max_score", 1)
                    pct = (score / max_score * 100) if max_score > 0 else 0
                    comp_totals.setdefault(name, []).append(pct)
        except (json.JSONDecodeError, TypeError):
            pass

    component_averages = []
    for name, scores in comp_totals.items():
        component_averages.append({
            "component": name,
            "avg_score": round(sum(scores) / len(scores), 1) if scores else 0,
            "trend_delta": 0,
        })
    component_averages.sort(key=lambda c: c["avg_score"])

    # 4. Weighted health (MRR-weighted average health score)
    current_weighted = 0.0
    current_total_mrr = 0.0
    for da, acct in latest.values():
        mrr = acct.mrr_estimate or 0
        current_weighted += da.health_score * mrr
        current_total_mrr += mrr
    current_wh = round(current_weighted / current_total_mrr, 1) if current_total_mrr > 0 else 0

    return {
        "distribution_over_time": distribution,
        "biggest_movers": biggest_movers,
        "component_averages": component_averages,
        "weighted_health": {"current": current_wh, "previous": 0, "delta": 0},
    }


def get_pipeline_flow(
    db: Session,
    weeks: int = 4,
    visible_user_ids: set[str] | None = None,
) -> dict:
    """Pipeline waterfall, coverage ratio trend, pipeline by forecast category."""
    rows = _get_assessments_in_window(db, weeks, visible_user_ids)
    if not rows:
        return {"waterfall": None, "coverage_trend": [], "pipeline_by_category": []}

    by_week = _group_by_week(rows)
    weekly_latest = _latest_per_account_per_week(by_week)
    sorted_weeks = sorted(weekly_latest.keys())

    # 1. Pipeline by forecast category per week
    pipeline_by_category = []
    weekly_totals = {}
    for wk in sorted_weeks:
        deals = weekly_latest[wk]
        cats = {"commit": 0.0, "realistic": 0.0, "upside": 0.0, "risk": 0.0}
        total = 0.0
        for da, acct in deals.values():
            mrr = acct.mrr_estimate or 0
            total += mrr
            cat = (da.ai_forecast_category or "").lower().replace(" ", "_").replace("at_risk", "risk")
            if cat in cats:
                cats[cat] += mrr
        pipeline_by_category.append({"week": wk, **cats})
        weekly_totals[wk] = total

    # 2. Waterfall: compare last two weeks
    waterfall = None
    if len(sorted_weeks) >= 2:
        prev_wk = sorted_weeks[-2]
        curr_wk = sorted_weeks[-1]
        prev_deals = weekly_latest[prev_wk]
        curr_deals = weekly_latest[curr_wk]
        prev_ids = set(prev_deals.keys())
        curr_ids = set(curr_deals.keys())

        new_deals = sum((curr_deals[aid][1].mrr_estimate or 0) for aid in curr_ids - prev_ids)
        lost_deals = sum((prev_deals[aid][1].mrr_estimate or 0) for aid in prev_ids - curr_ids)
        common = prev_ids & curr_ids
        upgrades = 0.0
        downgrades = 0.0
        for aid in common:
            prev_mrr = prev_deals[aid][1].mrr_estimate or 0
            curr_mrr = curr_deals[aid][1].mrr_estimate or 0
            diff = curr_mrr - prev_mrr
            if diff > 0:
                upgrades += diff
            elif diff < 0:
                downgrades += diff

        waterfall = {
            "previous_total": round(weekly_totals[prev_wk], 2),
            "new_deals": round(new_deals, 2),
            "lost_deals": round(-lost_deals, 2),
            "upgrades": round(upgrades, 2),
            "downgrades": round(downgrades, 2),
            "current_total": round(weekly_totals[curr_wk], 2),
        }

    # 3. Coverage ratio trend
    total_quota = 0.0
    quota_query = db.query(Quota).filter(Quota.period == "2026")
    if visible_user_ids is not None:
        quota_query = quota_query.filter(Quota.user_id.in_(visible_user_ids))
    for q in quota_query.all():
        total_quota += q.amount or 0

    coverage_trend = []
    for wk in sorted_weeks:
        pv = weekly_totals.get(wk, 0)
        ratio = round(pv / total_quota, 2) if total_quota > 0 else None
        coverage_trend.append({"week": wk, "coverage_ratio": ratio, "pipeline_value": round(pv, 2), "quota": round(total_quota, 2)})

    return {
        "waterfall": waterfall,
        "coverage_trend": coverage_trend,
        "pipeline_by_category": pipeline_by_category,
    }


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
