# Deal Trends Page Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the basic 3-tab `/trends` page with a 5-tab deal trends analytics hub (Pipeline Flow, Forecast Movement, Deal Health, Velocity, Team Comparison).

**Architecture:** 5 new backend service functions in `trend_service.py` feeding 5 new FastAPI endpoints in `dashboard.py`. Frontend: complete rewrite of `trends/page.tsx` as a 5-tab shell, with one component per tab, shared sparkline/waterfall components, and 5 React Query hooks. All data fetched per-tab on activation.

**Tech Stack:** FastAPI + SQLAlchemy 2.0 (backend), Next.js 16 + React 19 + Recharts 3.7 + shadcn/ui (frontend), SQLite (WAL mode).

**Design doc:** `docs/plans/2026-02-25-deal-trends-design.md`

---

## Task 1: Backend Shared Helpers

**Files:**
- Modify: `sis/services/trend_service.py` (add helpers at top, keep existing functions)

**Step 1: Add shared constants and helpers**

Add these at the top of `trend_service.py`, after the existing imports:

```python
import json
from sqlalchemy.orm import Session
from sis.db.models import Account, DealAssessment, User, Team, Quota

FORECAST_RANK = {"At Risk": 0, "Upside": 1, "Realistic": 2, "Commit": 3}

HEALTH_TIERS = {"healthy": 70, "at_risk": 45}  # >= 70 healthy, >= 45 at_risk, < 45 critical


def _iso_week(date_str: str) -> str:
    """Convert ISO 8601 timestamp to 'YYYY-WNN' for weekly grouping."""
    from datetime import datetime
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
```

**Step 2: Verify helpers work**

Run: `cd /Users/roylevierez/Documents/Sales/SIS && python -c "from sis.services.trend_service import _iso_week, FORECAST_RANK; print(_iso_week('2026-02-25T10:00:00+00:00'), FORECAST_RANK)"`

Expected: `2026-W09 {'At Risk': 0, 'Upside': 1, 'Realistic': 2, 'Commit': 3}`

**Step 3: Commit**

```bash
git add sis/services/trend_service.py
git commit -m "feat(trends): add shared helpers for 5-tab trends page"
```

---

## Task 2: Backend — Deal Health Endpoint

**Files:**
- Modify: `sis/services/trend_service.py` (add `get_deal_health_trends`)
- Modify: `sis/api/routes/dashboard.py` (add route)

**Step 1: Add service function**

Add to `trend_service.py`:

```python
def get_deal_health_trends(
    db: Session,
    weeks: int = 4,
    visible_user_ids: set[str] | None = None,
) -> dict:
    """Health distribution, biggest movers, component averages, weighted health."""
    rows = _get_assessments_in_window(db, weeks, visible_user_ids)
    if not rows:
        return {"distribution_over_time": [], "biggest_movers": [], "component_averages": [], "weighted_health": {"current": 0, "previous": 0, "delta": 0}}

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
            "trend_delta": 0,  # TODO: compute from first-vs-last week
        })
    component_averages.sort(key=lambda c: c["avg_score"])

    # 4. Weighted health
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
```

**Step 2: Add route**

Add to `dashboard.py` after the existing trends routes:

```python
@router.get("/trends/deal-health")
def trends_deal_health(
    weeks: int = 4,
    team: Optional[str] = None,
    deal_type: Optional[str] = None,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Health distribution, movers, component averages, weighted health."""
    visible_ids = _resolve_scoping(user, db)
    return trend_service.get_deal_health_trends(db=db, weeks=weeks, visible_user_ids=visible_ids)
```

**Step 3: Test endpoint**

Run: `cd /Users/roylevierez/Documents/Sales/SIS && python -c "
from sis.db.session import get_session
from sis.services.trend_service import get_deal_health_trends
with get_session() as s:
    result = get_deal_health_trends(s, weeks=12)
    print('Distribution weeks:', len(result['distribution_over_time']))
    print('Movers:', len(result['biggest_movers']))
    print('Components:', len(result['component_averages']))
    print('Weighted health:', result['weighted_health'])
"`

**Step 4: Commit**

```bash
git add sis/services/trend_service.py sis/api/routes/dashboard.py
git commit -m "feat(trends): add deal-health endpoint with distribution, movers, components"
```

---

## Task 3: Backend — Pipeline Flow Endpoint

**Files:**
- Modify: `sis/services/trend_service.py` (add `get_pipeline_flow`)
- Modify: `sis/api/routes/dashboard.py` (add route)

**Step 1: Add service function**

Add to `trend_service.py`:

```python
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
    # Get total quota for visible users
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
```

**Step 2: Add route**

Add to `dashboard.py`:

```python
@router.get("/trends/pipeline-flow")
def trends_pipeline_flow(
    weeks: int = 4,
    team: Optional[str] = None,
    deal_type: Optional[str] = None,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Pipeline waterfall, coverage ratio, pipeline by forecast category."""
    visible_ids = _resolve_scoping(user, db)
    return trend_service.get_pipeline_flow(db=db, weeks=weeks, visible_user_ids=visible_ids)
```

**Step 3: Test endpoint**

Run: `cd /Users/roylevierez/Documents/Sales/SIS && python -c "
from sis.db.session import get_session
from sis.services.trend_service import get_pipeline_flow
with get_session() as s:
    r = get_pipeline_flow(s, weeks=12)
    print('Waterfall:', r['waterfall'])
    print('Coverage points:', len(r['coverage_trend']))
    print('Category points:', len(r['pipeline_by_category']))
"`

**Step 4: Commit**

```bash
git add sis/services/trend_service.py sis/api/routes/dashboard.py
git commit -m "feat(trends): add pipeline-flow endpoint with waterfall, coverage, categories"
```

---

## Task 4: Backend — Forecast Migration Endpoint

**Files:**
- Modify: `sis/services/trend_service.py` (add `get_forecast_migration`)
- Modify: `sis/api/routes/dashboard.py` (add route)

**Step 1: Add service function**

```python
def get_forecast_migration(
    db: Session,
    weeks: int = 4,
    visible_user_ids: set[str] | None = None,
) -> dict:
    """Forecast category migrations and AI vs IC divergence trending."""
    rows = _get_assessments_in_window(db, weeks, visible_user_ids)
    if not rows:
        return {"migrations": [], "migration_summary": {"upgrades": 0, "downgrades": 0, "net": 0, "upgrade_value": 0, "downgrade_value": 0}, "divergence_trend": []}

    # Group by account to find category changes
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
            "mrr_estimate": acct.mrr_estimate or 0,
            "previous_category": prev_cat,
            "current_category": curr_cat,
            "changed_at": da_last.created_at[:10],
            "direction": direction,
        })

    migrations.sort(key=lambda m: -(m["mrr_estimate"]))

    ups = [m for m in migrations if m["direction"] == "upgrade"]
    downs = [m for m in migrations if m["direction"] == "downgrade"]
    summary = {
        "upgrades": len(ups),
        "downgrades": len(downs),
        "net": len(ups) - len(downs),
        "upgrade_value": round(sum(m["mrr_estimate"] for m in ups), 2),
        "downgrade_value": round(sum(m["mrr_estimate"] for m in downs), 2),
    }

    # Divergence trend per week
    by_week = _group_by_week(rows)
    weekly_latest = _latest_per_account_per_week(by_week)
    sorted_weeks = sorted(weekly_latest.keys())

    # Get IC forecasts from Account table
    divergence_trend = []
    for wk in sorted_weeks:
        deals = weekly_latest[wk]
        total = len(deals)
        divergent = sum(1 for da, acct in deals.values()
                        if acct.ic_forecast_category and da.ai_forecast_category != acct.ic_forecast_category)
        pct = round(divergent / total * 100, 1) if total > 0 else 0
        divergence_trend.append({"week": wk, "divergent_count": divergent, "total_deals": total, "divergence_pct": pct})

    return {"migrations": migrations, "migration_summary": summary, "divergence_trend": divergence_trend}
```

**Step 2: Add route**

```python
@router.get("/trends/forecast-migration")
def trends_forecast_migration(
    weeks: int = 4,
    team: Optional[str] = None,
    deal_type: Optional[str] = None,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Forecast category migrations and divergence trending."""
    visible_ids = _resolve_scoping(user, db)
    return trend_service.get_forecast_migration(db=db, weeks=weeks, visible_user_ids=visible_ids)
```

**Step 3: Test and commit**

```bash
git add sis/services/trend_service.py sis/api/routes/dashboard.py
git commit -m "feat(trends): add forecast-migration endpoint with migrations and divergence"
```

---

## Task 5: Backend — Velocity Endpoint

**Files:**
- Modify: `sis/services/trend_service.py` (add `get_velocity_trends`)
- Modify: `sis/api/routes/dashboard.py` (add route)

**Step 1: Add service function**

```python
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

    # Group by account
    by_account: dict[str, list[tuple[DealAssessment, Account]]] = {}
    for da, acct in rows:
        by_account.setdefault(da.account_id, []).append((da, acct))

    # Compute stage durations and events
    stage_days: dict[int, list[float]] = {}  # stage_num -> list of days spent
    stage_names: dict[int, str] = {}
    events: list[dict] = []
    current_stages: list[dict] = []  # for stalled detection

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
                # Record duration for previous stage
                days = (entry_dt - stage_entry_date).total_seconds() / 86400
                stage_days.setdefault(prev_stage, []).append(days)
                # Record event
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

        # Current stage duration (still in stage)
        if stage_entry_date and prev_stage is not None:
            days = (now - stage_entry_date).total_seconds() / 86400
            stage_days.setdefault(prev_stage, []).append(days)
            current_stages.append({
                "account_id": aid,
                "account_name": acct.account_name,
                "mrr_estimate": acct.mrr_estimate or 0,
                "current_stage": prev_stage,
                "stage_name": stage_names.get(prev_stage, f"Stage {prev_stage}"),
                "days_in_stage": round(days, 1),
                "health_score": items[-1][0].health_score,
            })

    events.sort(key=lambda e: e["event_date"], reverse=True)

    # Stage duration stats
    stage_durations = []
    for stage_num in sorted(stage_days.keys()):
        days_list = stage_days[stage_num]
        med = round(median(days_list), 1) if days_list else 0
        avg = round(sum(days_list) / len(days_list), 1) if days_list else 0
        stage_durations.append({
            "stage": stage_num,
            "stage_name": stage_names.get(stage_num, f"Stage {stage_num}"),
            "avg_days": avg,
            "median_days": med,
            "deal_count": len(days_list),
        })

    # Stalled deals: current_days > 1.5x median for that stage
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
```

**Step 2: Add route**

```python
@router.get("/trends/velocity")
def trends_velocity(
    weeks: int = 4,
    team: Optional[str] = None,
    deal_type: Optional[str] = None,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Stage velocity, stalled deals, progression events."""
    visible_ids = _resolve_scoping(user, db)
    return trend_service.get_velocity_trends(db=db, weeks=weeks, visible_user_ids=visible_ids)
```

**Step 3: Test and commit**

```bash
git add sis/services/trend_service.py sis/api/routes/dashboard.py
git commit -m "feat(trends): add velocity endpoint with stage durations, stalled deals, events"
```

---

## Task 6: Backend — Team Comparison Endpoint

**Files:**
- Modify: `sis/services/trend_service.py` (add `get_team_comparison`)
- Modify: `sis/api/routes/dashboard.py` (add route)

**Step 1: Add service function**

```python
def get_team_comparison(
    db: Session,
    weeks: int = 4,
    visible_user_ids: set[str] | None = None,
) -> dict:
    """Per-team pipeline trends, benchmarking, momentum distribution."""
    rows = _get_assessments_in_window(db, weeks, visible_user_ids)
    if not rows:
        return {"team_pipeline_trend": [], "benchmark_table": [], "momentum_distribution": []}

    # Resolve team for each account via owner -> user -> team
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

    # Group by week + team
    by_week = _group_by_week(rows)
    weekly_latest = _latest_per_account_per_week(by_week)
    sorted_weeks = sorted(weekly_latest.keys())

    # Team pipeline trend
    team_pipeline_trend = []
    for wk in sorted_weeks:
        teams_val: dict[str, float] = {}
        for da, acct in weekly_latest[wk].values():
            tn = _get_team_name(acct)
            teams_val[tn] = teams_val.get(tn, 0) + (acct.mrr_estimate or 0)
        team_pipeline_trend.append({"week": wk, "teams": {k: round(v, 2) for k, v in teams_val.items()}})

    # Benchmark table from latest week
    latest = _latest_per_account(rows)
    team_deals: dict[str, list[tuple[DealAssessment, Account]]] = {}
    for da, acct in latest.values():
        tn = _get_team_name(acct)
        team_deals.setdefault(tn, []).append((da, acct))

    benchmark_table = []
    momentum_distribution = []
    for tn, deals in team_deals.items():
        total_mrr = sum(acct.mrr_estimate or 0 for _, acct in deals)
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
```

**Step 2: Add route**

```python
@router.get("/trends/team-comparison")
def trends_team_comparison(
    weeks: int = 4,
    deal_type: Optional[str] = None,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Per-team pipeline trends, benchmarking, momentum distribution."""
    visible_ids = _resolve_scoping(user, db)
    return trend_service.get_team_comparison(db=db, weeks=weeks, visible_user_ids=visible_ids)
```

**Step 3: Test all 5 endpoints via FastAPI**

Run: `cd /Users/roylevierez/Documents/Sales/SIS && python -m uvicorn sis.api.main:app --port 8000 &`
Then: `curl -s http://localhost:8000/api/dashboard/trends/deal-health?weeks=12 | python -m json.tool | head -20`
And: `curl -s http://localhost:8000/api/dashboard/trends/pipeline-flow?weeks=12 | python -m json.tool | head -20`

**Step 4: Commit**

```bash
git add sis/services/trend_service.py sis/api/routes/dashboard.py
git commit -m "feat(trends): add team-comparison endpoint — all 5 backend endpoints complete"
```

---

## Task 7: Frontend — Types, API Client, Hooks

**Files:**
- Modify: `frontend/src/lib/api-types.ts` (add ~20 interfaces)
- Modify: `frontend/src/lib/api.ts` (add 5 API methods)
- Create: `frontend/src/lib/hooks/use-trends.ts` (5 React Query hooks)

**Step 1: Add TypeScript types to `api-types.ts`**

Add at the bottom of the file:

```typescript
// ── Deal Trends (5-tab analytics) ──

export interface WaterfallData {
  previous_total: number;
  new_deals: number;
  lost_deals: number;
  upgrades: number;
  downgrades: number;
  current_total: number;
}

export interface CoverageTrendPoint {
  week: string;
  coverage_ratio: number | null;
  pipeline_value: number;
  quota: number;
}

export interface PipelineByCategoryPoint {
  week: string;
  commit: number;
  realistic: number;
  upside: number;
  risk: number;
}

export interface PipelineFlowResponse {
  waterfall: WaterfallData | null;
  coverage_trend: CoverageTrendPoint[];
  pipeline_by_category: PipelineByCategoryPoint[];
}

export interface ForecastMigration {
  account_id: string;
  account_name: string;
  mrr_estimate: number;
  previous_category: string;
  current_category: string;
  changed_at: string;
  direction: 'upgrade' | 'downgrade';
}

export interface MigrationSummary {
  upgrades: number;
  downgrades: number;
  net: number;
  upgrade_value: number;
  downgrade_value: number;
}

export interface DivergenceTrendPoint {
  week: string;
  divergent_count: number;
  total_deals: number;
  divergence_pct: number;
}

export interface ForecastMovementResponse {
  migrations: ForecastMigration[];
  migration_summary: MigrationSummary;
  divergence_trend: DivergenceTrendPoint[];
}

export interface HealthDistributionPoint {
  week: string;
  healthy: number;
  at_risk: number;
  critical: number;
}

export interface BiggestMover {
  account_id: string;
  account_name: string;
  mrr_estimate: number;
  current_score: number;
  delta: number;
  direction: string;
  sparkline: number[];
}

export interface ComponentAverage {
  component: string;
  avg_score: number;
  trend_delta: number;
}

export interface WeightedHealth {
  current: number;
  previous: number;
  delta: number;
}

export interface DealHealthResponse {
  distribution_over_time: HealthDistributionPoint[];
  biggest_movers: BiggestMover[];
  component_averages: ComponentAverage[];
  weighted_health: WeightedHealth;
}

export interface StageDuration {
  stage: number;
  stage_name: string;
  avg_days: number;
  median_days: number;
  deal_count: number;
}

export interface StalledDeal {
  account_id: string;
  account_name: string;
  mrr_estimate: number;
  current_stage: number;
  stage_name: string;
  days_in_stage: number;
  median_for_stage: number;
  excess_days: number;
  health_score: number | null;
}

export interface StageEvent {
  account_id: string;
  account_name: string;
  from_stage: number;
  to_stage: number;
  from_stage_name: string;
  to_stage_name: string;
  event_date: string;
  direction: 'advance' | 'regression';
}

export interface VelocityResponse {
  stage_durations: StageDuration[];
  stalled_deals: StalledDeal[];
  stage_events: StageEvent[];
}

export interface TeamBenchmark {
  team_name: string;
  total_deals: number;
  pipeline_value: number;
  avg_health: number | null;
  improving_count: number;
  stable_count: number;
  declining_count: number;
}

export interface TeamMomentum {
  team_name: string;
  improving: number;
  stable: number;
  declining: number;
}

export interface TeamPipelineTrendPoint {
  week: string;
  teams: Record<string, number>;
}

export interface TeamComparisonResponse {
  team_pipeline_trend: TeamPipelineTrendPoint[];
  benchmark_table: TeamBenchmark[];
  momentum_distribution: TeamMomentum[];
}
```

**Step 2: Add API methods to `api.ts`**

Add these inside the `dashboard` object in `api.ts` (find the section with `trendDeals`, `trendTeams`, `trendPortfolio`):

```typescript
trendsPipelineFlow: (weeks?: number) =>
  apiFetch<PipelineFlowResponse>(`/api/dashboard/trends/pipeline-flow?weeks=${weeks ?? 4}`),
trendsForecastMovement: (weeks?: number) =>
  apiFetch<ForecastMovementResponse>(`/api/dashboard/trends/forecast-migration?weeks=${weeks ?? 4}`),
trendsDealHealth: (weeks?: number) =>
  apiFetch<DealHealthResponse>(`/api/dashboard/trends/deal-health?weeks=${weeks ?? 4}`),
trendsVelocity: (weeks?: number) =>
  apiFetch<VelocityResponse>(`/api/dashboard/trends/velocity?weeks=${weeks ?? 4}`),
trendsTeamComparison: (weeks?: number) =>
  apiFetch<TeamComparisonResponse>(`/api/dashboard/trends/team-comparison?weeks=${weeks ?? 4}`),
```

Also add the new types to the import block at the top of `api.ts`.

**Step 3: Create hooks file**

Create `frontend/src/lib/hooks/use-trends.ts`:

```typescript
import { useQuery } from '@tanstack/react-query';
import { api } from '../api';

export function usePipelineFlow(weeks: number) {
  return useQuery({
    queryKey: ['trends', 'pipeline-flow', weeks],
    queryFn: () => api.dashboard.trendsPipelineFlow(weeks),
  });
}

export function useForecastMovement(weeks: number) {
  return useQuery({
    queryKey: ['trends', 'forecast-movement', weeks],
    queryFn: () => api.dashboard.trendsForecastMovement(weeks),
  });
}

export function useDealHealth(weeks: number) {
  return useQuery({
    queryKey: ['trends', 'deal-health', weeks],
    queryFn: () => api.dashboard.trendsDealHealth(weeks),
  });
}

export function useVelocity(weeks: number) {
  return useQuery({
    queryKey: ['trends', 'velocity', weeks],
    queryFn: () => api.dashboard.trendsVelocity(weeks),
  });
}

export function useTeamComparison(weeks: number) {
  return useQuery({
    queryKey: ['trends', 'team-comparison', weeks],
    queryFn: () => api.dashboard.trendsTeamComparison(weeks),
  });
}
```

**Step 4: Commit**

```bash
git add frontend/src/lib/api-types.ts frontend/src/lib/api.ts frontend/src/lib/hooks/use-trends.ts
git commit -m "feat(trends): add frontend types, API client methods, and React Query hooks"
```

---

## Task 8: Frontend — Shared Components (Sparkline, Waterfall)

**Files:**
- Create: `frontend/src/components/trends/sparkline.tsx`
- Create: `frontend/src/components/trends/waterfall-chart.tsx`

**Step 1: Create sparkline component**

Create `frontend/src/components/trends/sparkline.tsx`:

```tsx
'use client';

import { LineChart, Line, ResponsiveContainer } from 'recharts';

interface SparklineProps {
  data: number[];
  width?: number;
  height?: number;
  color?: string;
  className?: string;
}

export function Sparkline({ data, width = 80, height = 24, color, className }: SparklineProps) {
  if (!data || data.length === 0) return <span className="text-muted-foreground text-xs">--</span>;

  const chartData = data.map((value, i) => ({ i, v: value }));
  const trend = data[data.length - 1] - data[0];
  const lineColor = color || (trend >= 0 ? 'oklch(0.60 0.18 145)' : 'oklch(0.60 0.20 25)');

  return (
    <div className={className} style={{ width, height }}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData} margin={{ top: 2, right: 2, bottom: 2, left: 2 }}>
          <Line
            type="monotone"
            dataKey="v"
            stroke={lineColor}
            strokeWidth={1.5}
            dot={data.length === 1}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
```

**Step 2: Create waterfall chart component**

Create `frontend/src/components/trends/waterfall-chart.tsx`:

```tsx
'use client';

import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell, ReferenceLine } from 'recharts';
import type { WaterfallData } from '@/lib/api-types';

interface WaterfallChartProps {
  data: WaterfallData;
}

export function WaterfallChart({ data }: WaterfallChartProps) {
  const items = [
    { name: 'Previous', value: data.previous_total, color: '#94a3b8' },
    { name: 'New Deals', value: data.new_deals, color: '#22c55e' },
    { name: 'Upgrades', value: data.upgrades, color: '#3b82f6' },
    { name: 'Downgrades', value: data.downgrades, color: '#f97316' },
    { name: 'Lost', value: data.lost_deals, color: '#ef4444' },
    { name: 'Current', value: data.current_total, color: '#16a34a' },
  ];

  const formatValue = (v: number) => {
    if (Math.abs(v) >= 1_000_000) return `$${(v / 1_000_000).toFixed(1)}M`;
    if (Math.abs(v) >= 1_000) return `$${(v / 1_000).toFixed(0)}K`;
    return `$${v.toFixed(0)}`;
  };

  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={items} margin={{ top: 20, right: 20, bottom: 5, left: 20 }}>
        <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
        <XAxis dataKey="name" className="text-xs" />
        <YAxis tickFormatter={formatValue} className="text-xs" />
        <Tooltip formatter={(v: number) => formatValue(v)} />
        <Bar dataKey="value" radius={[4, 4, 0, 0]} isAnimationActive={false}>
          {items.map((item, idx) => (
            <Cell key={idx} fill={item.color} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
```

**Step 3: Commit**

```bash
git add frontend/src/components/trends/sparkline.tsx frontend/src/components/trends/waterfall-chart.tsx
git commit -m "feat(trends): add sparkline and waterfall shared chart components"
```

---

## Task 9: Frontend — 5 Tab Components + Page Shell + Sidebar

This is the largest task. Build each tab component and then wire them together in the page shell. Each tab follows the same pattern: hook → loading/empty → summary cards → charts/tables.

**Files:**
- Create: `frontend/src/components/trends/deal-health-tab.tsx`
- Create: `frontend/src/components/trends/pipeline-flow-tab.tsx`
- Create: `frontend/src/components/trends/forecast-movement-tab.tsx`
- Create: `frontend/src/components/trends/velocity-tab.tsx`
- Create: `frontend/src/components/trends/team-comparison-tab.tsx`
- Rewrite: `frontend/src/app/trends/page.tsx` (5-tab shell)
- Modify: `frontend/src/components/sidebar.tsx` (add Trends nav item)

**Step 1: Create all 5 tab components**

Each tab follows this pattern:
1. Call its React Query hook
2. Show loading spinner while fetching
3. Show empty state if no data
4. Render summary cards (4 per tab) in a responsive grid
5. Render charts/tables below

Reference the design doc (`docs/plans/2026-02-25-deal-trends-design.md`) for exact visualizations per tab. Use:
- `Card, CardHeader, CardTitle, CardContent` for layout
- `Table, TableBody, TableCell, TableHead, TableHeader, TableRow` for tables
- Recharts `AreaChart` (stacked) for health distribution + pipeline-by-category
- Recharts `BarChart` for waterfall, stage duration, momentum
- Recharts `LineChart` for coverage ratio, team pipeline
- Recharts `ComposedChart` (Bar + Line) for divergence trend
- `Sparkline` component for inline table sparklines
- `WaterfallChart` component for pipeline waterfall
- `Badge` for direction badges (Improving/Stable/Declining)
- `Progress` (shadcn) for excess days bars in velocity tab
- Links via `<Link href={/deals/${accountId}}>` for deal drill-through
- `isAnimationActive={false}` on ALL Recharts components

Color conventions:
- Healthy/Improving/Commit: `oklch(0.60 0.18 145)` (green)
- At Risk/Stable/Realistic: `oklch(0.75 0.15 85)` (amber)
- Critical/Declining/At Risk: `oklch(0.60 0.20 25)` (red)
- Upside: `oklch(0.70 0.15 230)` (blue)

**Step 2: Rewrite page shell**

Rewrite `frontend/src/app/trends/page.tsx`:

```tsx
'use client';

import { useState } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { PipelineFlowTab } from '@/components/trends/pipeline-flow-tab';
import { ForecastMovementTab } from '@/components/trends/forecast-movement-tab';
import { DealHealthTab } from '@/components/trends/deal-health-tab';
import { VelocityTab } from '@/components/trends/velocity-tab';
import { TeamComparisonTab } from '@/components/trends/team-comparison-tab';

const WEEK_OPTIONS = [4, 8, 12] as const;

export default function TrendsPage() {
  const [weeks, setWeeks] = useState<number>(4);

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Deal Trends</h1>
          <p className="text-muted-foreground text-sm">Pipeline analytics over time</p>
        </div>
        <div className="flex gap-1">
          {WEEK_OPTIONS.map((w) => (
            <Badge
              key={w}
              variant={weeks === w ? 'default' : 'outline'}
              className="cursor-pointer"
              onClick={() => setWeeks(w)}
            >
              {w}w
            </Badge>
          ))}
        </div>
      </div>

      <Tabs defaultValue="pipeline-flow">
        <TabsList className="grid w-full grid-cols-5">
          <TabsTrigger value="pipeline-flow">Pipeline Flow</TabsTrigger>
          <TabsTrigger value="forecast-movement">Forecast Movement</TabsTrigger>
          <TabsTrigger value="deal-health">Deal Health</TabsTrigger>
          <TabsTrigger value="velocity">Velocity</TabsTrigger>
          <TabsTrigger value="team-comparison">Team Comparison</TabsTrigger>
        </TabsList>
        <TabsContent value="pipeline-flow"><PipelineFlowTab weeks={weeks} /></TabsContent>
        <TabsContent value="forecast-movement"><ForecastMovementTab weeks={weeks} /></TabsContent>
        <TabsContent value="deal-health"><DealHealthTab weeks={weeks} /></TabsContent>
        <TabsContent value="velocity"><VelocityTab weeks={weeks} /></TabsContent>
        <TabsContent value="team-comparison"><TeamComparisonTab weeks={weeks} /></TabsContent>
      </Tabs>
    </div>
  );
}
```

**Step 3: Add Trends to sidebar**

In `frontend/src/components/sidebar.tsx`, add to the Analytics group (after Pipeline, before Team Rollup):

```typescript
{ label: 'Deal Trends', href: '/trends', icon: TrendingUp },
```

Add `TrendingUp` to the lucide-react imports if not already there.

**Step 4: Verify the page loads**

Run the dev servers and navigate to `http://localhost:3000/trends`. Verify:
- All 5 tabs render without errors
- Switching tabs loads data from the correct endpoint
- Changing the weeks selector refreshes the active tab
- "Deal Trends" appears in the sidebar and navigates correctly

**Step 5: Commit**

```bash
git add frontend/src/components/trends/ frontend/src/app/trends/page.tsx frontend/src/components/sidebar.tsx
git commit -m "feat(trends): complete 5-tab deal trends page with sidebar navigation"
```

---

## Summary

| Task | Scope | Dependencies |
|------|-------|-------------|
| 1 | Backend shared helpers | None |
| 2 | Deal Health endpoint | Task 1 |
| 3 | Pipeline Flow endpoint | Task 1 |
| 4 | Forecast Migration endpoint | Task 1 |
| 5 | Velocity endpoint | Task 1 |
| 6 | Team Comparison endpoint | Task 1 |
| 7 | Frontend types + API + hooks | Tasks 2-6 |
| 8 | Shared components (sparkline, waterfall) | None |
| 9 | 5 tab components + page shell + sidebar | Tasks 7-8 |

**Tasks 2-6 can run in parallel** (independent endpoints).
**Tasks 7 and 8 can run in parallel** (types vs components).
**Task 9 depends on all prior tasks.**

**Critical path:** Task 1 → Tasks 2-6 (parallel) → Task 7 → Task 9
