"""Dashboard API routes — pipeline overview, divergence, team rollup, insights, trends."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends

from sis.api.deps import get_current_user
from sis.services import dashboard_service, trend_service

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/pipeline")
def pipeline_overview(team: Optional[str] = None, user: dict = Depends(get_current_user)):
    """Aggregated pipeline view with deals grouped by health tier."""
    return dashboard_service.get_pipeline_overview(team=team)


@router.get("/divergence")
def divergence_report(team: Optional[str] = None, user: dict = Depends(get_current_user)):
    """Deals where AI and IC forecasts diverge."""
    return dashboard_service.get_divergence_report(team=team)


@router.get("/team-rollup")
def team_rollup(team: Optional[str] = None, user: dict = Depends(get_current_user)):
    """Aggregate health metrics per team."""
    return dashboard_service.get_team_rollup(team=team)


@router.get("/insights")
def pipeline_insights(user: dict = Depends(get_current_user)):
    """Auto-generated pipeline insights: stuck, improving, declining, etc."""
    return dashboard_service.get_pipeline_insights()


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
