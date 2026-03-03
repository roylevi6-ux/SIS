"""Dashboard API routes — pipeline overview, divergence, team rollup, insights, trends."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from sis.api.deps import get_current_user, get_db, resolve_scoping
from sis.services import dashboard_service, trend_service

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/pipeline")
def pipeline_overview(
    team: Optional[str] = None,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Aggregated pipeline view with deals grouped by health tier."""
    visible_ids = resolve_scoping(user, db)
    return dashboard_service.get_pipeline_overview(team=team, visible_user_ids=visible_ids)


@router.get("/divergence")
def divergence_report(
    team: Optional[str] = None,
    team_id: Optional[str] = None,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Deals where AI and IC forecasts diverge."""
    visible_ids = resolve_scoping(user, db)
    return dashboard_service.get_divergence_report(team=team, team_id=team_id, visible_user_ids=visible_ids)


@router.get("/team-rollup")
def team_rollup(
    team: Optional[str] = None,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Aggregate health metrics per team."""
    visible_ids = resolve_scoping(user, db)
    return dashboard_service.get_team_rollup(team=team, visible_user_ids=visible_ids)


@router.get("/team-rollup/hierarchy")
def team_rollup_hierarchy(
    team_id: Optional[str] = None,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Hierarchical team rollup: Team → Reps → Deals with aggregates."""
    visible_ids = resolve_scoping(user, db)
    return dashboard_service.get_team_rollup_hierarchy(team_id=team_id, visible_user_ids=visible_ids)


@router.get("/insights")
def pipeline_insights(
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Auto-generated pipeline insights: stuck, improving, declining, etc."""
    visible_ids = resolve_scoping(user, db)
    return dashboard_service.get_pipeline_insights(visible_user_ids=visible_ids)


@router.get("/trends/deals")
def deal_trends(account_id: Optional[str] = None, weeks: int = 4, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """Per-deal health trajectory over N weeks."""
    visible_ids = resolve_scoping(user, db)
    return trend_service.get_deal_trends(db=db, account_id=account_id, weeks=weeks, visible_user_ids=visible_ids)


@router.get("/trends/teams")
def team_trends(weeks: int = 4, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """Aggregated deal trends per team."""
    visible_ids = resolve_scoping(user, db)
    deal_data = trend_service.get_deal_trends(db=db, weeks=weeks, visible_user_ids=visible_ids)
    return trend_service.get_team_trends(weeks=weeks, deal_trends=deal_data)


@router.get("/trends/portfolio")
def portfolio_summary(weeks: int = 4, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """Portfolio-wide trend summary."""
    visible_ids = resolve_scoping(user, db)
    deal_data = trend_service.get_deal_trends(db=db, weeks=weeks, visible_user_ids=visible_ids)
    return trend_service.get_portfolio_summary(weeks=weeks, deal_trends=deal_data)


@router.get("/trends/deal-health")
def trends_deal_health(
    weeks: int = 4,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Health distribution, movers, component averages, weighted health."""
    visible_ids = resolve_scoping(user, db)
    return trend_service.get_deal_health_trends(db=db, weeks=weeks, visible_user_ids=visible_ids)


@router.get("/trends/pipeline-flow")
def trends_pipeline_flow(
    weeks: int = 4,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Pipeline waterfall, coverage ratio, pipeline by forecast category."""
    visible_ids = resolve_scoping(user, db)
    return trend_service.get_pipeline_flow(db=db, weeks=weeks, visible_user_ids=visible_ids)


@router.get("/trends/forecast-migration")
def trends_forecast_migration(
    weeks: int = 4,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Forecast category migrations and divergence trending."""
    visible_ids = resolve_scoping(user, db)
    return trend_service.get_forecast_migration(db=db, weeks=weeks, visible_user_ids=visible_ids)


@router.get("/trends/velocity")
def trends_velocity(
    weeks: int = 4,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Stage velocity, stalled deals, progression events."""
    visible_ids = resolve_scoping(user, db)
    return trend_service.get_velocity_trends(db=db, weeks=weeks, visible_user_ids=visible_ids)


@router.get("/trends/team-comparison")
def trends_team_comparison(
    weeks: int = 4,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Per-team pipeline trends, benchmarking, momentum distribution."""
    visible_ids = resolve_scoping(user, db)
    return trend_service.get_team_comparison(db=db, weeks=weeks, visible_user_ids=visible_ids)


@router.get("/command-center")
def command_center(
    team: Optional[str] = None,
    ae: Optional[str] = None,
    period: str = "2026",
    quarter: Optional[str] = None,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Command Center: quota attainment, forecast breakdown, pipeline totals, attention items."""
    visible = resolve_scoping(user, db)
    return dashboard_service.get_command_center(
        db=db,
        visible_user_ids=visible,
        period=period,
        quarter=quarter,
        team_id=team,
        ae_name=ae,
    )
