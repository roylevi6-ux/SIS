"""Dashboard API routes — pipeline overview, divergence, team rollup, insights, trends."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from sis.api.deps import get_current_user, get_db
from sis.services import dashboard_service, trend_service
from sis.services.scoping_service import get_visible_user_ids
from sis.db.models import User

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


def _resolve_scoping(user: dict, db: Session) -> Optional[set[str]]:
    """Compute visible user IDs from JWT user dict. None = no restriction."""
    user_id = user.get("user_id") if user else None
    if not user_id:
        return None
    db_user = db.query(User).filter_by(id=user_id).first()
    if not db_user or db_user.role in ("admin", "gm"):
        return None
    return get_visible_user_ids(db_user, db)


@router.get("/pipeline")
def pipeline_overview(
    team: Optional[str] = None,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Aggregated pipeline view with deals grouped by health tier."""
    visible_ids = _resolve_scoping(user, db)
    return dashboard_service.get_pipeline_overview(team=team, visible_user_ids=visible_ids)


@router.get("/divergence")
def divergence_report(
    team: Optional[str] = None,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Deals where AI and IC forecasts diverge."""
    visible_ids = _resolve_scoping(user, db)
    return dashboard_service.get_divergence_report(team=team, visible_user_ids=visible_ids)


@router.get("/team-rollup")
def team_rollup(
    team: Optional[str] = None,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Aggregate health metrics per team."""
    visible_ids = _resolve_scoping(user, db)
    return dashboard_service.get_team_rollup(team=team, visible_user_ids=visible_ids)


@router.get("/team-rollup/hierarchy")
def team_rollup_hierarchy(
    team: Optional[str] = None,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Hierarchical team rollup: Team → Reps → Deals with aggregates."""
    visible_ids = _resolve_scoping(user, db)
    return dashboard_service.get_team_rollup_hierarchy(team=team, visible_user_ids=visible_ids)


@router.get("/insights")
def pipeline_insights(
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Auto-generated pipeline insights: stuck, improving, declining, etc."""
    visible_ids = _resolve_scoping(user, db)
    return dashboard_service.get_pipeline_insights(visible_user_ids=visible_ids)


@router.get("/trends/deals")
def deal_trends(account_id: Optional[str] = None, weeks: int = 4, user: dict = Depends(get_current_user)):
    """Per-deal health trajectory over N weeks."""
    return trend_service.get_deal_trends(account_id=account_id, weeks=weeks)


@router.get("/trends/teams")
def team_trends(weeks: int = 4, user: dict = Depends(get_current_user)):
    """Aggregated deal trends per team."""
    deal_data = trend_service.get_deal_trends(weeks=weeks)
    return trend_service.get_team_trends(weeks=weeks, deal_trends=deal_data)


@router.get("/trends/portfolio")
def portfolio_summary(weeks: int = 4, user: dict = Depends(get_current_user)):
    """Portfolio-wide trend summary."""
    deal_data = trend_service.get_deal_trends(weeks=weeks)
    return trend_service.get_portfolio_summary(weeks=weeks, deal_trends=deal_data)


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
    visible = _resolve_scoping(user, db)
    return dashboard_service.get_command_center(
        db=db,
        visible_user_ids=visible,
        period=period,
        quarter=quarter,
        team_id=team,
        ae_name=ae,
    )
