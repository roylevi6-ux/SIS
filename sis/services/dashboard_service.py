"""Dashboard service — pipeline overview, divergence, team rollup per Section 6.6."""

from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from typing import Optional

from sis.db.session import get_session
from sis.db.models import Account, DealAssessment, AnalysisRun, Transcript, User, Team, Quota
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
                "cp_estimate": acct.cp_estimate,
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
                    "stage_gap_direction": latest.stage_gap_direction,
                    "stage_gap_magnitude": latest.stage_gap_magnitude,
                    "forecast_gap_direction": latest.forecast_gap_direction,
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
                    "stage_gap_direction": None,
                    "stage_gap_magnitude": None,
                    "forecast_gap_direction": None,
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
                "total_mrr_healthy": sum(d["cp_estimate"] or 0 for d in healthy),
                "total_mrr_at_risk": sum(d["cp_estimate"] or 0 for d in at_risk),
                "total_mrr_critical": sum(d["cp_estimate"] or 0 for d in critical),
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
                "cp_estimate": account.cp_estimate,
                "team_lead": account.team_lead,
                "ai_forecast_category": assessment.ai_forecast_category,
                "ic_forecast_category": account.ic_forecast_category,
                "health_score": assessment.health_score,
                "divergence_explanation": assessment.divergence_explanation,
                "forecast_rationale": assessment.forecast_rationale,
            })

        # Sort by CP Estimate impact (highest value divergences first)
        divergent.sort(key=lambda d: -(d["cp_estimate"] or 0))
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
                "total_mrr": sum(m["account"].cp_estimate or 0 for m in members),
                "divergent_count": sum(1 for m in scored if m["assessment"].divergence_flag),
            })

        rollup.sort(key=lambda r: -(r["total_mrr"]))
        return rollup


def get_team_rollup_hierarchy(
    team: Optional[str] = None,
    visible_user_ids: Optional[set[str]] = None,
) -> list[dict]:
    """Hierarchical team rollup: Team → Reps → Deals with aggregates at each level.

    Groups accounts by Account.owner_id → User.team_id → Team.
    Falls back to team_name string for legacy accounts without owner_id.
    Default sort: critical_count DESC at team level.
    """
    with get_session() as session:
        query = session.query(Account)
        if visible_user_ids is not None:
            query = query.filter(Account.owner_id.in_(visible_user_ids))
        accounts = query.all()

        # Build a lookup: team_id → team info
        all_teams = {t.id: t for t in session.query(Team).all()}
        # Build a lookup: user_id → user
        all_users = {u.id: u for u in session.query(User).filter(User.is_active == 1).all()}

        # Group accounts into team → rep → deals
        # Structure: {team_key: {rep_key: [deal_dicts]}}
        hierarchy: dict[str, dict[str, list[dict]]] = {}
        team_meta: dict[str, dict] = {}  # team_key → {name, leader}

        for acct in accounts:
            # Get latest assessment
            latest = (
                session.query(DealAssessment)
                .filter_by(account_id=acct.id)
                .order_by(DealAssessment.created_at.desc())
                .first()
            )

            deal = {
                "account_id": acct.id,
                "account_name": acct.account_name,
                "cp_estimate": acct.cp_estimate,
                "health_score": latest.health_score if latest else None,
                "momentum_direction": latest.momentum_direction if latest else None,
                "ai_forecast_category": latest.ai_forecast_category if latest else None,
                "stage_name": latest.stage_name if latest else None,
                "divergence_flag": bool(latest.divergence_flag) if latest else False,
            }

            # Resolve team via hierarchy (owner_id → user.team_id → team)
            team_key = "Unassigned"
            team_name_resolved = "Unassigned"
            team_leader_name = None
            rep_name = acct.ae_owner or "Unknown Rep"

            if acct.owner_id and acct.owner_id in all_users:
                owner = all_users[acct.owner_id]
                rep_name = owner.name
                if owner.team_id and owner.team_id in all_teams:
                    t = all_teams[owner.team_id]
                    team_key = t.id
                    team_name_resolved = t.name
                    if t.leader_id and t.leader_id in all_users:
                        team_leader_name = all_users[t.leader_id].name
            elif acct.team_name:
                # Legacy fallback: group by string team_name
                team_key = f"legacy:{acct.team_name}"
                team_name_resolved = acct.team_name
                team_leader_name = acct.team_lead

            # Apply team filter
            if team and team_name_resolved != team:
                continue

            if team_key not in hierarchy:
                hierarchy[team_key] = {}
                team_meta[team_key] = {"name": team_name_resolved, "leader": team_leader_name}

            rep_key = acct.owner_id or f"legacy:{rep_name}"
            if rep_key not in hierarchy[team_key]:
                hierarchy[team_key][rep_key] = []
            hierarchy[team_key][rep_key].append(deal)

        # Build response with aggregates
        result = []
        for team_key, reps in hierarchy.items():
            meta = team_meta[team_key]
            all_deals = [d for deals in reps.values() for d in deals]
            scored = [d for d in all_deals if d["health_score"] is not None]

            team_entry = {
                "team_id": team_key if not team_key.startswith("legacy:") else None,
                "team_name": meta["name"],
                "team_lead": meta["leader"],
                "total_deals": len(all_deals),
                "avg_health_score": (
                    round(sum(d["health_score"] for d in scored) / len(scored), 1)
                    if scored else None
                ),
                "healthy_count": sum(1 for d in scored if d["health_score"] >= 70),
                "at_risk_count": sum(1 for d in scored if 45 <= d["health_score"] < 70),
                "critical_count": sum(1 for d in scored if d["health_score"] < 45),
                "total_mrr": sum(d["cp_estimate"] or 0 for d in all_deals),
                "divergent_count": sum(1 for d in scored if d["divergence_flag"]),
                "reps": [],
            }

            for rep_key, deals in reps.items():
                rep_scored = [d for d in deals if d["health_score"] is not None]
                rep_user = all_users.get(rep_key) if not rep_key.startswith("legacy:") else None
                rep_entry = {
                    "rep_id": rep_key if not rep_key.startswith("legacy:") else None,
                    "rep_name": rep_user.name if rep_user else rep_key.replace("legacy:", ""),
                    "total_deals": len(deals),
                    "avg_health_score": (
                        round(sum(d["health_score"] for d in rep_scored) / len(rep_scored), 1)
                        if rep_scored else None
                    ),
                    "healthy_count": sum(1 for d in rep_scored if d["health_score"] >= 70),
                    "at_risk_count": sum(1 for d in rep_scored if 45 <= d["health_score"] < 70),
                    "critical_count": sum(1 for d in rep_scored if d["health_score"] < 45),
                    "total_mrr": sum(d["cp_estimate"] or 0 for d in deals),
                    "deals": deals,
                }
                team_entry["reps"].append(rep_entry)

            # Sort reps by critical count DESC
            team_entry["reps"].sort(key=lambda r: -(r["critical_count"]))

            result.append(team_entry)

        # Sort teams by critical count DESC (risk-first)
        result.sort(key=lambda t: -(t["critical_count"]))
        return result


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


def get_command_center(
    db,
    visible_user_ids: Optional[set[str]],
    period: str = "2026",
    quarter: Optional[str] = None,
    team_id: Optional[str] = None,
    ae_name: Optional[str] = None,
) -> dict:
    """Command Center: quota, forecast breakdown, pipeline totals, attention items.

    Args:
        db: SQLAlchemy session (injected by route via Depends).
        visible_user_ids: Scoping set from JWT — None means admin/gm sees all.
        period: Quota period, e.g. "2026" for annual.
        quarter: Optional quarter filter, e.g. "Q1". Not yet applied to deals
                 (placeholder for future close-date filtering).
        team_id: Optional Team.id filter.
        ae_name: Optional ae_owner string filter.

    Returns:
        dict with keys: deals, forecast, pipeline, quota_amount, attention, weekly_changes.
    """
    now = datetime.now(timezone.utc)
    stale_cutoff_30 = (now - timedelta(days=STALE_CALL_DAYS_THRESHOLD)).strftime("%Y-%m-%d")

    # ── 1. Resolve accounts ───────────────────────────────────────────────
    query = db.query(Account)
    if visible_user_ids is not None:
        query = query.filter(Account.owner_id.in_(visible_user_ids))
    if team_id is not None:
        # Filter by accounts whose owner belongs to this team
        team_user_ids = [
            u.id for u in db.query(User).filter(User.team_id == team_id).all()
        ]
        query = query.filter(Account.owner_id.in_(team_user_ids))
    if ae_name is not None:
        query = query.filter(Account.ae_owner == ae_name)

    accounts = query.all()

    # ── 2. Build deal list — batch queries to avoid N+1 ─────────────────
    from sqlalchemy import func, and_

    account_ids = [a.id for a in accounts]
    acct_map = {a.id: a for a in accounts}

    # Batch: latest assessment per account (single query)
    latest_assess_sq = (
        db.query(
            DealAssessment.account_id,
            func.max(DealAssessment.created_at).label("max_ca"),
        )
        .filter(DealAssessment.account_id.in_(account_ids))
        .group_by(DealAssessment.account_id)
        .subquery()
    ) if account_ids else None

    assess_map: dict[str, DealAssessment] = {}
    if latest_assess_sq is not None:
        for da in (
            db.query(DealAssessment)
            .join(latest_assess_sq, and_(
                DealAssessment.account_id == latest_assess_sq.c.account_id,
                DealAssessment.created_at == latest_assess_sq.c.max_ca,
            ))
            .all()
        ):
            assess_map[da.account_id] = da

    # Batch: latest transcript per account (single query)
    latest_tx_sq = (
        db.query(
            Transcript.account_id,
            func.max(Transcript.call_date).label("max_cd"),
        )
        .filter(Transcript.account_id.in_(account_ids), Transcript.is_active == 1)
        .group_by(Transcript.account_id)
        .subquery()
    ) if account_ids else None

    tx_map: dict[str, str] = {}  # account_id → call_date
    if latest_tx_sq is not None:
        for tx in (
            db.query(Transcript)
            .join(latest_tx_sq, and_(
                Transcript.account_id == latest_tx_sq.c.account_id,
                Transcript.call_date == latest_tx_sq.c.max_cd,
            ))
            .all()
        ):
            tx_map[tx.account_id] = tx.call_date

    deals = []
    for acct in accounts:
        latest = assess_map.get(acct.id)
        deal: dict = {
            "account_id": acct.id,
            "account_name": acct.account_name,
            "cp_estimate": acct.cp_estimate,
            "team_lead": acct.team_lead,
            "ae_owner": acct.ae_owner,
            "team_name": acct.team_name,
            "ic_forecast_category": acct.ic_forecast_category,
            "deal_type": acct.deal_type,
            "last_call_date": tx_map.get(acct.id),
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
                "deal_memo_preview": (
                    (latest.deal_memo[:200] + "...")
                    if latest.deal_memo and len(latest.deal_memo) > 200
                    else latest.deal_memo
                ),
                "stage_gap_direction": latest.stage_gap_direction,
                "stage_gap_magnitude": latest.stage_gap_magnitude,
                "forecast_gap_direction": latest.forecast_gap_direction,
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
                "stage_gap_direction": None,
                "stage_gap_magnitude": None,
                "forecast_gap_direction": None,
            })

        deals.append(deal)

    # ── 3. Forecast breakdown ─────────────────────────────────────────────
    # Map backend category names → frontend keys (frontend expects "risk", not "at_risk")
    _CAT_MAP = {"Commit": "commit", "Realistic": "realistic", "Upside": "upside", "At Risk": "risk"}
    forecast: dict = {}
    for db_cat, fe_key in _CAT_MAP.items():
        cat_deals = [d for d in deals if d.get("ai_forecast_category") == db_cat]
        forecast[fe_key] = {
            "count": len(cat_deals),
            "value": sum(d["cp_estimate"] or 0 for d in cat_deals),
        }

    # ── 4. Pipeline totals ────────────────────────────────────────────────
    total_mrr = sum(d["cp_estimate"] or 0 for d in deals)

    # Weighted pipeline per design spec: Commit×0.90 + Realistic×0.60 + Upside×0.30 + Risk×0.10
    _WEIGHTS = {"commit": 0.90, "realistic": 0.60, "upside": 0.30, "risk": 0.10}
    weighted_mrr = sum(
        forecast[k]["value"] * w for k, w in _WEIGHTS.items()
    )

    # ── 5. Quota lookup ───────────────────────────────────────────────────
    # Sum quotas for all visible users (or all ICs if no scoping)
    quota_query = db.query(Quota).filter(Quota.period == period)
    if visible_user_ids is not None:
        quota_query = quota_query.filter(Quota.user_id.in_(visible_user_ids))
    quota_rows = quota_query.all()
    total_quota = sum(q.amount for q in quota_rows)

    # Divide by 4 for quarterly view
    if quarter is not None:
        quota_for_period = total_quota / 4
    else:
        quota_for_period = total_quota

    # Pipeline coverage ratio (total pipeline / quota)
    coverage = (total_mrr / quota_for_period) if quota_for_period > 0 else 0.0
    # Gap: weighted - quota (positive = ahead, negative = behind)
    gap = weighted_mrr - quota_for_period

    # ── 6. Attention items ────────────────────────────────────────────────
    scored_deals = [d for d in deals if d.get("health_score") is not None]

    # Declining health — momentum_direction == "declining" (case-insensitive)
    declining_attn = sorted(
        [
            d for d in scored_deals
            if (d.get("momentum_direction") or "").lower() == "declining"
        ],
        key=lambda d: -(d["cp_estimate"] or 0),
    )[:5]

    # Divergent forecast — divergence_flag True
    divergent_attn = sorted(
        [d for d in scored_deals if d.get("divergence_flag")],
        key=lambda d: -(d["cp_estimate"] or 0),
    )[:5]

    # Stale — no call in 30+ days
    stale_attn = sorted(
        [
            d for d in deals
            if (
                d.get("last_call_date") is None
                or d["last_call_date"][:10] < stale_cutoff_30
            )
        ],
        key=lambda d: -(d["cp_estimate"] or 0),
    )[:5]

    attention = {
        "declining_health": declining_attn,
        "divergent_forecast": divergent_attn,
        "stale_deals": stale_attn,
    }

    # ── 7. Weekly changes (compare current vs 7-day-old assessments) ─────
    weekly_changes = _compute_weekly_changes(db, accounts)

    # ── 8. Flatten attention items into single list ────────────────────────
    attention_items = []
    for d in declining_attn:
        attention_items.append({
            "account_id": d["account_id"],
            "account_name": d["account_name"],
            "cp_estimate": d["cp_estimate"] or 0,
            "reason": f"Health declining — momentum {d.get('momentum_direction', 'unknown')}",
            "type": "declining",
        })
    for d in divergent_attn:
        attention_items.append({
            "account_id": d["account_id"],
            "account_name": d["account_name"],
            "cp_estimate": d["cp_estimate"] or 0,
            "reason": f"AI/IC forecast divergence — AI: {d.get('ai_forecast_category', '?')}, IC: {d.get('ic_forecast_category', '?')}",
            "type": "divergent",
        })
    for d in stale_attn:
        attention_items.append({
            "account_id": d["account_id"],
            "account_name": d["account_name"],
            "cp_estimate": d["cp_estimate"] or 0,
            "reason": f"No call in {STALE_CALL_DAYS_THRESHOLD}+ days (last: {d.get('last_call_date', 'never')[:10] if d.get('last_call_date') else 'never'})",
            "type": "stale",
        })
    # Sort by CP Estimate descending and limit to top 10
    attention_items.sort(key=lambda x: -x["cp_estimate"])
    attention_items = attention_items[:10]

    # ── Return shape matching frontend CommandCenterResponse ──────────────
    return {
        "deals": deals,
        "forecast_breakdown": forecast,
        "pipeline": {
            "total_value": total_mrr,
            "total_deals": len(deals),
            "coverage": round(coverage, 2) if coverage is not None else 0,
            "weighted_value": round(weighted_mrr, 2),
            "gap": round(gap, 2),
        },
        "quota": {
            "amount": round(quota_for_period, 2),
            "period": quarter or period,
        },
        "attention_items": attention_items,
        "changes_this_week": weekly_changes,
    }


def _compute_weekly_changes(db, accounts: list) -> dict:
    """Compare current vs 7-day-old assessments for weekly pipeline movement."""
    from sqlalchemy import func, and_

    one_week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    account_ids = [a.id for a in accounts]
    acct_mrr = {a.id: (a.cp_estimate or 0) for a in accounts}

    if not account_ids:
        return {"added": 0, "dropped": 0, "net": 0, "stage_advances": 0, "forecast_flips": 0, "new_risks": 0}

    # Batch: latest assessment per account (reuse subquery pattern)
    latest_sq = (
        db.query(
            DealAssessment.account_id,
            func.max(DealAssessment.created_at).label("max_ca"),
        )
        .filter(DealAssessment.account_id.in_(account_ids))
        .group_by(DealAssessment.account_id)
        .subquery()
    )
    current: dict[str, dict] = {}
    for da in (
        db.query(DealAssessment)
        .join(latest_sq, and_(
            DealAssessment.account_id == latest_sq.c.account_id,
            DealAssessment.created_at == latest_sq.c.max_ca,
        ))
        .all()
    ):
        current[da.account_id] = {
            "mrr": acct_mrr.get(da.account_id, 0),
            "stage": da.inferred_stage,
            "forecast": da.ai_forecast_category,
            "health": da.health_score,
        }

    # Batch: latest assessment before 7 days ago
    prev_sq = (
        db.query(
            DealAssessment.account_id,
            func.max(DealAssessment.created_at).label("max_ca"),
        )
        .filter(
            DealAssessment.account_id.in_(account_ids),
            DealAssessment.created_at < one_week_ago,
        )
        .group_by(DealAssessment.account_id)
        .subquery()
    )
    previous: dict[str, dict] = {}
    for da in (
        db.query(DealAssessment)
        .join(prev_sq, and_(
            DealAssessment.account_id == prev_sq.c.account_id,
            DealAssessment.created_at == prev_sq.c.max_ca,
        ))
        .all()
    ):
        previous[da.account_id] = {
            "mrr": acct_mrr.get(da.account_id, 0),
            "stage": da.inferred_stage,
            "forecast": da.ai_forecast_category,
            "health": da.health_score,
        }

    # Compute deltas
    added = sum(d["mrr"] for aid, d in current.items() if aid not in previous)
    dropped = sum(d["mrr"] for aid, d in previous.items() if aid not in current)
    stage_advances = 0
    forecast_flips = 0
    new_risks = 0

    for aid, cur in current.items():
        prev = previous.get(aid)
        if not prev:
            continue
        if cur["stage"] and prev["stage"] and cur["stage"] > prev["stage"]:
            stage_advances += 1
        if cur["forecast"] != prev["forecast"]:
            forecast_flips += 1
        cur_health = cur.get("health") or 100
        prev_health = prev.get("health") or 100
        if cur_health < 45 and prev_health >= 45:
            new_risks += 1

    return {
        "added": round(added, 0),
        "dropped": round(dropped, 0),
        "net": round(added - dropped, 0),
        "stage_advances": stage_advances,
        "forecast_flips": forecast_flips,
        "new_risks": new_risks,
    }
