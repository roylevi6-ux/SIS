"""Export API routes — deal brief and forecast report export."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter

from sis.services import export_service

router = APIRouter(prefix="/api/export", tags=["export"])


@router.get("/brief/{account_id}")
def export_deal_brief(account_id: str, format: str = "markdown"):
    """Export a one-page deal brief for pipeline review prep."""
    content = export_service.export_deal_brief(
        account_id=account_id,
        format=format,
    )
    return {"content": content}


@router.get("/forecast")
def export_forecast_report(team: Optional[str] = None, format: str = "markdown"):
    """Export AI vs IC forecast comparison report."""
    content = export_service.export_forecast_report(
        team=team,
        format=format,
    )
    return {"content": content}
