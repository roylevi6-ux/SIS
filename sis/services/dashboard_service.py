"""Dashboard service — pipeline overview, divergence, team rollup per Section 6.6."""

from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from typing import Optional

from sis.db.session import get_session
from sis.db.models import Account, DealAssessment, AnalysisRun, Transcript
from sis.config import STALE_CALL_DAYS_THRESHOLD


def get_pipeline_overview(
    team: Optional[str] = None,
    visible_user_ids: Optional[set[str]] = None,
) -> dict:
    """Aggregated pipeline view with deals grouped by health tier.

    Args:
        team: Legacy team name filter (optional, backward compat)
        visible_user_ids: If provided, only return accounts where owner_id is in this set.
                          None means no scoping (admin/gm sees all).

    Returns:
        dict with tiers (healthy/at_risk/critical), deals per tier, and aggregates
    """
    with get_session() as session:
        query = session.query(Account)
        if visible_user_ids is not None:
            query = query.filter(Account.owner_id.in_(visible_user_ids))
        elif team:
            query = query.filter_by(team_name=team)
        accounts = query.all()

        deals = []
        for acct in accounts:
            latest = (
                session.query(DealAssessment)
                .filter_by(account_id=acct.id)
                .order_by(DealAssessment.created_at.desc())
                .first()
            )

            # Days since last call
            latest_transcript = (
                session.query(Transcript)
                .filter_by(account_id=acct.id, is_active=1)
                .order_by(Transcript.call_date.desc())
                .first()
            )

            deal = {
                "account_id": acct.id,
                "account_name": acct.account_name,
                "mrr_estimate": acct.mrr_estimate,
                "team_lead": acct.team_lead,
                "ae_owner": acct.ae_owner,
                "team_name": acct.team_name,
                "ic_forecast_category": acct.ic_forecast_category,
                "last_call_date": latest_transcript.call_date if latest_transcript else None,
            }

            if latest:
                deal.update({
                    "health_score": latest.health_score,
                    "momentum_direction": latest.momentum_direction,
                    "ai_forecast_category": latest.ai_forecast_category,
                    "inferred_stage": latest.inferred_stage,
                    "stage_name": latest.stage_name,
                    "overall_confidence": latest.overall_confidence,
                    "divergence_flag": bool(latest.divergence_flag),
                    "deal_memo_preview": (latest.deal_memo[:200] + "...") if latest.deal_memo and len(latest.deal_memo) > 200 else latest.deal_memo,
                })
            else:
                deal.update({
                    "health_score": None,
                    "momentum_direction": None,
                    "ai_forecast_category": None,
                    "inferred_stage": None,
                    "stage_name": None,
                    "overall_confidence": None,
                    "divergence_flag": False,
                    "deal_memo_preview": None,
                })

            deals.append(deal)

        # Group by health tier
        healthy = [d for d in deals if d["health_score"] is not None and d["health_score"] >= 70]
        at_risk = [d for d in deals if d["health_score"] is not None and 45 <= d["health_score"] < 70]
        critical = [d for d in deals if d["health_score"] is not None and d["health_score"] < 45]
        unscored = [d for d in deals if d["health_score"] is None]

        return {
            "total_deals": len(deals),
            "healthy": sorted(healthy, key=lambda d: -d["health_score"]),
            "at_risk": sorted(at_risk, key=lambda d: -d["health_score"]),
            "critical": sorted(critical, key=lambda d: -d["health_score"]),
            "unscored": unscored,
            "summary": {
                "healthy_count": len(healthy),
                "at_risk_count": len(at_risk),
                "critical_count": len(critical),
                "unscored_count": len(unscored),
                "total_mrr_healthy": sum(d["mrr_estimate"] or 0 for d in healthy),
                "total_mrr_at_risk": sum(d["mrr_estimate"] or 0 for d in at_risk),
                "total_mrr_critical": sum(d["mrr_estimate"] or 0 for d in critical),
            },
        }


def get_divergence_report(
    team: Optional[str] = None,
    visible_user_ids: Optional[set[str]] = None,
) -> list[dict]:
    """Deals where AI and IC forecasts differ, sorted by value impact."""
    with get_session() as session:
        query = (
            session.query(DealAssessment, Account)
            .join(Account, DealAssessment.account_id == Account.id)
            .filter(DealAssessment.divergence_flag == 1)
        )
        if visible_user_ids is not None:
            query = query.filter(Account.owner_id.in_(visible_user_ids))
        elif team:
            query = query.filter(Account.team_name == team)

        # Get only latest assessment per account
        results = query.order_by(DealAssessment.created_at.desc()).all()

        seen_accounts = set()
        divergent = []
        for assessment, account in results:
            if account.id in seen_accounts:
                continue
            seen_accounts.add(account.id)
            divergent.append({
                "account_id": account.id,
                "account_name": account.account_name,
                "mrr_estimate": account.mrr_estimate,
                "team_lead": account.team_lead,
                "ai_forecast_category": assessment.ai_forecast_category,
                "ic_forecast_category": account.ic_forecast_category,
                "health_score": assessment.health_score,
                "divergence_explanation": assessment.divergence_explanation,
                "forecast_rationale": assessment.forecast_rationale,
            })

        # Sort by MRR impact (highest value divergences first)
        divergent.sort(key=lambda d: -(d["mrr_estimate"] or 0))
        return divergent


def get_team_rollup(
    team: Optional[str] = None,
    visible_user_ids: Optional[set[str]] = None,
) -> list[dict]:
    """Aggregate health metrics per team."""
    with get_session() as session:
        query = session.query(Account)
        if visible_user_ids is not None:
            query = query.filter(Account.owner_id.in_(visible_user_ids))
        accounts = query.all()

        # Group by team
        teams: dict[str, list] = {}
        for acct in accounts:
            t = acct.team_name or acct.team_lead or "Unassigned"
            if team and t != team:
                continue
            if t not in teams:
                teams[t] = []

            latest = (
                session.query(DealAssessment)
                .filter_by(account_id=acct.id)
                .order_by(DealAssessment.created_at.desc())
                .first()
            )

            teams[t].append({
                "account": acct,
                "assessment": latest,
            })

        rollup = []
        for team_name, members in teams.items():
            scored = [m for m in members if m["assessment"]]
            rollup.append({
                "team_name": team_name,
                "total_deals": len(members),
                "scored_deals": len(scored),
                "avg_health_score": (
                    round(sum(m["assessment"].health_score for m in scored) / len(scored), 1)
                    if scored else None
                ),
                "healthy_count": sum(1 for m in scored if m["assessment"].health_score >= 70),
                "at_risk_count": sum(1 for m in scored if 45 <= m["assessment"].health_score < 70),
                "critical_count": sum(1 for m in scored if m["assessment"].health_score < 45),
                "total_mrr": sum(m["account"].mrr_estimate or 0 for m in members),
                "divergent_count": sum(1 for m in scored if m["assessment"].divergence_flag),
            })

        rollup.sort(key=lambda r: -(r["total_mrr"]))
        return rollup


def get_pipeline_insights(visible_user_ids: Optional[set[str]] = None) -> dict:
    """Auto-generated pipeline insights: stuck, improving, declining, new risks, stale, forecast flips.

    Compares latest vs previous DealAssessment per account to detect changes.
    Per PRD P0-20.
    """
    with get_session() as session:
        query = session.query(Account)
        if visible_user_ids is not None:
            query = query.filter(Account.owner_id.in_(visible_user_ids))
        accounts = query.all()

        stuck = []
        improving = []
        declining = []
        new_risks = []
        stale = []
        forecast_flips = []

        now = datetime.now(timezone.utc)
        stale_cutoff = (now - timedelta(days=STALE_CALL_DAYS_THRESHOLD)).strftime("%Y-%m-%d")

        def _parse_risks(val):
            if not val:
                return []
            try:
                parsed = json.loads(val)
                return [r.get("risk", str(r)) if isinstance(r, dict) else str(r) for r in parsed]
            except (json.JSONDecodeError, TypeError):
                return []

        for acct in accounts:
            # Get latest two assessments
            assessments = (
                session.query(DealAssessment)
                .filter_by(account_id=acct.id)
                .order_by(DealAssessment.created_at.desc())
                .limit(2)
                .all()
            )

            # Check for stale deals (no transcript in threshold days)
            latest_transcript = (
                session.query(Transcript)
                .filter_by(account_id=acct.id, is_active=1)
                .order_by(Transcript.call_date.desc())
                .first()
            )
            if latest_transcript and latest_transcript.call_date[:10] < stale_cutoff:
                stale.append({
                    "account_id": acct.id,
                    "account_name": acct.account_name,
                    "last_call_date": latest_transcript.call_date,
                    "description": f"No transcript in {STALE_CALL_DAYS_THRESHOLD}+ days",
                })
            elif not latest_transcript and assessments:
                stale.append({
                    "account_id": acct.id,
                    "account_name": acct.account_name,
                    "last_call_date": None,
                    "description": "No transcripts on file",
                })

            if len(assessments) < 2:
                continue

            latest, previous = assessments[0], assessments[1]
            score_delta = latest.health_score - previous.health_score

            # Stuck deals: health < 50, momentum Stable or Declining for 2+ runs
            if (latest.health_score < 50
                    and latest.momentum_direction in ("Stable", "Declining")
                    and previous.momentum_direction in ("Stable", "Declining")):
                stuck.append({
                    "account_id": acct.id,
                    "account_name": acct.account_name,
                    "health_score": latest.health_score,
                    "momentum": latest.momentum_direction,
                    "score_delta": score_delta,
                    "description": f"Health {latest.health_score}, {latest.momentum_direction} for 2+ runs",
                })

            # Improving: score increased by 10+ points
            if score_delta >= 10:
                improving.append({
                    "account_id": acct.id,
                    "account_name": acct.account_name,
                    "health_score": latest.health_score,
                    "score_delta": score_delta,
                    "description": f"Health improved {previous.health_score} -> {latest.health_score} (+{score_delta})",
                })

            # Declining: score dropped by 10+ points
            if score_delta <= -10:
                declining.append({
                    "account_id": acct.id,
                    "account_name": acct.account_name,
                    "health_score": latest.health_score,
                    "score_delta": score_delta,
                    "description": f"Health dropped {previous.health_score} -> {latest.health_score} ({score_delta})",
                })

            # New risks: compare top_risks JSON
            latest_risks = set(_parse_risks(latest.top_risks))
            previous_risks = set(_parse_risks(previous.top_risks))
            added_risks = latest_risks - previous_risks
            if added_risks:
                new_risks.append({
                    "account_id": acct.id,
                    "account_name": acct.account_name,
                    "health_score": latest.health_score,
                    "new_risks": list(added_risks),
                    "description": f"{len(added_risks)} new risk(s) identified",
                })

            # Forecast flips
            if latest.ai_forecast_category != previous.ai_forecast_category:
                forecast_flips.append({
                    "account_id": acct.id,
                    "account_name": acct.account_name,
                    "health_score": latest.health_score,
                    "previous_forecast": previous.ai_forecast_category,
                    "current_forecast": latest.ai_forecast_category,
                    "description": f"Forecast changed: {previous.ai_forecast_category} -> {latest.ai_forecast_category}",
                })

        return {
            "stuck": stuck,
            "improving": improving,
            "declining": declining,
            "new_risks": new_risks,
            "stale": stale,
            "forecast_flips": forecast_flips,
        }
