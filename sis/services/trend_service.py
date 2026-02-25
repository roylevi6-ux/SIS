"""Trend Analysis service — pipeline health change over time per PRD P1-3.

Per-deal and per-team health trajectories using DealAssessment time-series data.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy.orm import Session

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
            "cp_estimate": acct.cp_estimate or 0,
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

    # 4. Weighted health (CP-weighted average health score)
    current_weighted = 0.0
    current_total_cp = 0.0
    for da, acct in latest.values():
        cp = acct.cp_estimate or 0
        current_weighted += da.health_score * cp
        current_total_cp += cp
    current_wh = round(current_weighted / current_total_cp, 1) if current_total_cp > 0 else 0

    # Compute previous week's weighted health for delta
    previous_wh = 0.0
    if len(sorted_weeks) >= 2:
        prev_week = sorted_weeks[-2]
        prev_deals = weekly_latest[prev_week]
        prev_weighted = 0.0
        prev_total_cp = 0.0
        for da, acct in prev_deals.values():
            cp = acct.cp_estimate or 0
            prev_weighted += da.health_score * cp
            prev_total_cp += cp
        previous_wh = round(prev_weighted / prev_total_cp, 1) if prev_total_cp > 0 else 0

    return {
        "distribution_over_time": distribution,
        "biggest_movers": biggest_movers,
        "component_averages": component_averages,
        "weighted_health": {"current": current_wh, "previous": previous_wh, "delta": round(current_wh - previous_wh, 1)},
        "avg_health_score": round(sum(da.health_score for da, _ in latest.values()) / len(latest), 1) if latest else 0,
        "total_deals": len(latest),
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
            mrr = acct.cp_estimate or 0
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

        new_deals = sum((curr_deals[aid][1].cp_estimate or 0) for aid in curr_ids - prev_ids)
        lost_deals = sum((prev_deals[aid][1].cp_estimate or 0) for aid in prev_ids - curr_ids)
        common = prev_ids & curr_ids
        upgrades = 0.0
        downgrades = 0.0
        for aid in common:
            prev_mrr = prev_deals[aid][1].cp_estimate or 0
            curr_mrr = curr_deals[aid][1].cp_estimate or 0
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
    current_year = str(datetime.now().year)
    quota_query = db.query(Quota).filter(Quota.period == current_year)
    if visible_user_ids is not None:
        quota_query = quota_query.filter(Quota.user_id.in_(visible_user_ids))
    for q in quota_query.all():
        total_quota += q.amount or 0

    coverage_trend = []
    for wk in sorted_weeks:
        pv = weekly_totals.get(wk, 0)
        ratio = round(pv / total_quota, 2) if total_quota > 0 else None
        coverage_trend.append({"week": wk, "coverage_ratio": ratio, "pipeline_value": round(pv, 2), "quota": round(total_quota, 2)})

    # Count active deals in the latest week
    latest_week_deals = len(weekly_latest[sorted_weeks[-1]]) if sorted_weeks else 0

    return {
        "waterfall": waterfall,
        "coverage_trend": coverage_trend,
        "pipeline_by_category": pipeline_by_category,
        "total_deals": latest_week_deals,
    }


def get_forecast_migration(
    db: Session,
    weeks: int = 4,
    visible_user_ids: set[str] | None = None,
) -> dict:
    """Forecast category migrations and AI vs IC divergence trending."""
    rows = _get_assessments_in_window(db, weeks, visible_user_ids)
    if not rows:
        return {"migrations": [], "migration_summary": {"upgrades": 0, "downgrades": 0, "net": 0, "upgrade_value": 0, "downgrade_value": 0}, "divergence_trend": []}

    by_account: dict[str, list[tuple[DealAssessment, Account]]] = {}
    for da, acct in rows:
        by_account.setdefault(da.account_id, []).append((da, acct))

    migrations = []
    for aid, items in by_account.items():
        if len(items) < 2:
            continue
        da_first, _ = items[0]
        da_last, acct = items[-1]
        prev_cat = da_first.ai_forecast_category
        curr_cat = da_last.ai_forecast_category
        if prev_cat == curr_cat:
            continue
        prev_rank = FORECAST_RANK.get(prev_cat, 0)
        curr_rank = FORECAST_RANK.get(curr_cat, 0)
        direction = "upgrade" if curr_rank > prev_rank else "downgrade"
        migrations.append({
            "account_id": aid,
            "account_name": acct.account_name,
            "cp_estimate": acct.cp_estimate or 0,
            "previous_category": prev_cat,
            "current_category": curr_cat,
            "changed_at": da_last.created_at[:10],
            "direction": direction,
        })

    migrations.sort(key=lambda m: -(m["cp_estimate"]))

    ups = [m for m in migrations if m["direction"] == "upgrade"]
    downs = [m for m in migrations if m["direction"] == "downgrade"]
    summary = {
        "upgrades": len(ups),
        "downgrades": len(downs),
        "net": len(ups) - len(downs),
        "upgrade_value": round(sum(m["cp_estimate"] for m in ups), 2),
        "downgrade_value": round(sum(m["cp_estimate"] for m in downs), 2),
    }

    by_week = _group_by_week(rows)
    weekly_latest = _latest_per_account_per_week(by_week)
    sorted_weeks = sorted(weekly_latest.keys())

    divergence_trend = []
    for wk in sorted_weeks:
        deals = weekly_latest[wk]
        total = len(deals)
        divergent = sum(1 for da, acct in deals.values()
                        if acct.ic_forecast_category and da.ai_forecast_category != acct.ic_forecast_category)
        pct = round(divergent / total * 100, 1) if total > 0 else 0
        divergence_trend.append({"week": wk, "divergent_count": divergent, "total_deals": total, "divergence_pct": pct})

    return {"migrations": migrations, "migration_summary": summary, "divergence_trend": divergence_trend}


def get_velocity_trends(
    db: Session,
    weeks: int = 4,
    visible_user_ids: set[str] | None = None,
) -> dict:
    """Stage durations, stalled deals, stage progression events."""
    rows = _get_assessments_in_window(db, weeks, visible_user_ids)
    if not rows:
        return {"stage_durations": [], "stalled_deals": [], "stage_events": []}

    from statistics import median

    now = datetime.now(timezone.utc)

    by_account: dict[str, list[tuple[DealAssessment, Account]]] = {}
    for da, acct in rows:
        by_account.setdefault(da.account_id, []).append((da, acct))

    completed_stage_days: dict[int, list[float]] = {}  # only completed transitions (for benchmarks)
    stage_names: dict[int, str] = {}
    events: list[dict] = []
    current_stages: list[dict] = []

    for aid, items in by_account.items():
        prev_stage = None
        stage_entry_date = None
        acct = items[-1][1]

        for da, _ in items:
            stage = da.inferred_stage
            stage_names[stage] = da.stage_name
            entry_dt = datetime.fromisoformat(da.created_at.replace("Z", "+00:00"))

            if prev_stage is None:
                prev_stage = stage
                stage_entry_date = entry_dt
                continue

            if stage != prev_stage:
                days = (entry_dt - stage_entry_date).total_seconds() / 86400
                completed_stage_days.setdefault(prev_stage, []).append(days)
                events.append({
                    "account_id": aid,
                    "account_name": acct.account_name,
                    "from_stage": prev_stage,
                    "to_stage": stage,
                    "from_stage_name": stage_names.get(prev_stage, f"Stage {prev_stage}"),
                    "to_stage_name": da.stage_name,
                    "event_date": da.created_at[:10],
                    "direction": "advance" if stage > prev_stage else "regression",
                })
                prev_stage = stage
                stage_entry_date = entry_dt
            else:
                prev_stage = stage

        # Track current in-progress deals separately (NOT included in benchmark medians)
        if stage_entry_date and prev_stage is not None:
            days = (now - stage_entry_date).total_seconds() / 86400
            current_stages.append({
                "account_id": aid,
                "account_name": acct.account_name,
                "cp_estimate": acct.cp_estimate or 0,
                "current_stage": prev_stage,
                "stage_name": stage_names.get(prev_stage, f"Stage {prev_stage}"),
                "days_in_stage": round(days, 1),
                "health_score": items[-1][0].health_score,
            })

    events.sort(key=lambda e: e["event_date"], reverse=True)

    stage_durations = []
    for stage_num in sorted(completed_stage_days.keys()):
        days_list = completed_stage_days[stage_num]
        med = round(median(days_list), 1) if days_list else 0
        avg = round(sum(days_list) / len(days_list), 1) if days_list else 0
        stage_durations.append({
            "stage": stage_num,
            "stage_name": stage_names.get(stage_num, f"Stage {stage_num}"),
            "avg_days": avg,
            "median_days": med,
            "deal_count": len(days_list),
        })

    median_by_stage = {sd["stage"]: sd["median_days"] for sd in stage_durations}
    stalled = []
    for deal in current_stages:
        stage_med = median_by_stage.get(deal["current_stage"], 0)
        if stage_med > 0 and deal["days_in_stage"] > stage_med * 1.5:
            stalled.append({
                **deal,
                "median_for_stage": stage_med,
                "excess_days": round(deal["days_in_stage"] - stage_med, 1),
            })
    stalled.sort(key=lambda s: -s["excess_days"])

    return {"stage_durations": stage_durations, "stalled_deals": stalled, "stage_events": events[:20]}


def get_team_comparison(
    db: Session,
    weeks: int = 4,
    visible_user_ids: set[str] | None = None,
) -> dict:
    """Per-team pipeline trends, benchmarking, momentum distribution."""
    rows = _get_assessments_in_window(db, weeks, visible_user_ids)
    if not rows:
        return {"team_pipeline_trend": [], "benchmark_table": [], "momentum_distribution": []}

    user_team_cache: dict[str, str] = {}

    def _get_team_name(acct: Account) -> str:
        if acct.owner_id and acct.owner_id not in user_team_cache:
            owner = db.query(User).filter_by(id=acct.owner_id).first()
            if owner and owner.team_id:
                team = db.query(Team).filter_by(id=owner.team_id).first()
                user_team_cache[acct.owner_id] = team.name if team else "Unassigned"
            else:
                user_team_cache[acct.owner_id] = "Unassigned"
        return user_team_cache.get(acct.owner_id, acct.team_name or "Unassigned")

    by_week = _group_by_week(rows)
    weekly_latest = _latest_per_account_per_week(by_week)
    sorted_weeks = sorted(weekly_latest.keys())

    team_pipeline_trend = []
    for wk in sorted_weeks:
        teams_val: dict[str, float] = {}
        for da, acct in weekly_latest[wk].values():
            tn = _get_team_name(acct)
            teams_val[tn] = teams_val.get(tn, 0) + (acct.cp_estimate or 0)
        team_pipeline_trend.append({"week": wk, "teams": {k: round(v, 2) for k, v in teams_val.items()}})

    latest = _latest_per_account(rows)
    team_deals: dict[str, list[tuple[DealAssessment, Account]]] = {}
    for da, acct in latest.values():
        tn = _get_team_name(acct)
        team_deals.setdefault(tn, []).append((da, acct))

    benchmark_table = []
    momentum_distribution = []
    for tn, deals in team_deals.items():
        total_mrr = sum(acct.cp_estimate or 0 for _, acct in deals)
        scores = [da.health_score for da, _ in deals if da.health_score is not None]
        avg_health = round(sum(scores) / len(scores), 1) if scores else None
        improving = sum(1 for da, _ in deals if da.momentum_direction == "Improving")
        stable = sum(1 for da, _ in deals if da.momentum_direction == "Stable")
        declining = sum(1 for da, _ in deals if da.momentum_direction == "Declining")

        benchmark_table.append({
            "team_name": tn,
            "total_deals": len(deals),
            "pipeline_value": round(total_mrr, 2),
            "avg_health": avg_health,
            "improving_count": improving,
            "stable_count": stable,
            "declining_count": declining,
        })
        momentum_distribution.append({"team_name": tn, "improving": improving, "stable": stable, "declining": declining})

    benchmark_table.sort(key=lambda t: -t["pipeline_value"])

    return {"team_pipeline_trend": team_pipeline_trend, "benchmark_table": benchmark_table, "momentum_distribution": momentum_distribution}


def get_deal_trends(
    db: Session,
    account_id: Optional[str] = None,
    weeks: int = 4,
    visible_user_ids: set[str] | None = None,
) -> list[dict]:
    """Per-deal health trajectory over N weeks.

    Returns list of deal trend dicts sorted by biggest movers first (abs delta).
    """
    cutoff = (datetime.now(timezone.utc) - timedelta(weeks=weeks)).isoformat()

    query = (
        db.query(DealAssessment, Account.account_name, Account.team_name, Account.ae_owner)
        .join(Account, DealAssessment.account_id == Account.id)
        .filter(DealAssessment.created_at >= cutoff)
        .order_by(DealAssessment.account_id, DealAssessment.created_at)
    )
    if account_id:
        query = query.filter(DealAssessment.account_id == account_id)
    if visible_user_ids is not None:
        query = query.filter(Account.owner_id.in_(visible_user_ids))

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
    Callers must pass deal_trends (from get_deal_trends with scoping).
    """
    if deal_trends is None:
        return []

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

    Callers must pass deal_trends (from get_deal_trends with scoping).
    """
    if deal_trends is None:
        deal_trends = []

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
