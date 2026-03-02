"""User preferences API routes."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Union

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from sis.api.deps import get_current_user, get_db
from sis.db.models import UserPreference

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/preferences", tags=["preferences"])


# Default widget configuration
DEFAULT_DEAL_WIDGETS = [
    {"id": "status_strip", "label": "Status Strip", "description": "Health, stage, forecast, and confidence badges", "visible": True, "order": 0},
    {"id": "call_timeline", "label": "Call Timeline", "description": "Chronological view of all calls", "visible": True, "order": 1},
    {"id": "what_changed", "label": "What Changed", "description": "Metric deltas between latest and previous run", "visible": True, "order": 2},
    {"id": "deal_memo", "label": "Deal Memo", "description": "TL Insider Brief and Leadership Summary", "visible": True, "order": 3},
    {"id": "manager_actions", "label": "Manager Actions", "description": "Consolidated weekly action items from all agents", "visible": True, "order": 4},
    {"id": "health_breakdown", "label": "Health Breakdown", "description": "Radar chart and score table for health components", "visible": True, "order": 5},
    {"id": "actions_risks", "label": "Actions & Risks", "description": "Recommended actions and risk signals", "visible": True, "order": 6},
    {"id": "positive_contradictions", "label": "Signals & Contradictions", "description": "Positive signals and contradiction map", "visible": True, "order": 7},
    {"id": "forecast_divergence", "label": "Forecast Divergence", "description": "AI vs IC forecast divergence explanation", "visible": True, "order": 8},
    {"id": "key_unknowns", "label": "Key Unknowns", "description": "Outstanding questions and unknowns", "visible": True, "order": 9},
    {"id": "forecast_rationale", "label": "Forecast Rationale", "description": "Reasoning behind the AI forecast", "visible": True, "order": 10},
    {"id": "sf_gap", "label": "SF Gap Analysis", "description": "SIS vs Salesforce stage and forecast comparison", "visible": True, "order": 11},
    {"id": "agent_analyses", "label": "Per-Agent Analysis", "description": "Collapsible cards for each agent's findings", "visible": True, "order": 12},
    {"id": "deal_timeline", "label": "Deal Timeline", "description": "Assessment history trend chart", "visible": True, "order": 13},
    {"id": "analysis_history", "label": "Analysis History", "description": "List of past analysis runs", "visible": True, "order": 14},
    {"id": "transcript_list", "label": "Transcripts", "description": "All uploaded transcripts for this account", "visible": True, "order": 15},
]

DEFAULT_PIPELINE_WIDGETS = [
    {"id": "number_line", "label": "Number Line", "description": "Pipeline stage funnel visualization", "visible": True, "order": 0},
    {"id": "attention_strip", "label": "Attention Strip", "description": "Deals needing immediate attention", "visible": True, "order": 1},
    {"id": "pipeline_changes", "label": "Pipeline Changes", "description": "Recent deal movements and updates", "visible": True, "order": 2},
    {"id": "filter_chips", "label": "Filter Chips", "description": "Quick filters for deal table", "visible": True, "order": 3},
    {"id": "team_forecast_grid", "label": "Team Forecast Grid", "description": "Team-level forecast summary (VP+ only)", "visible": True, "order": 4},
    {"id": "deal_table", "label": "Deal Table", "description": "Main pipeline data table", "visible": True, "order": 5},
]


class PreferenceUpdate(BaseModel):
    value: Union[dict, list]


def _get_user_id_from_token(user: dict, db) -> str | None:
    """Resolve JWT sub (username) to users.id."""
    from sis.db.models import User
    row = db.query(User).filter(User.name == user["sub"]).first()
    return row.id if row else None


@router.get("/{key}")
def get_preference(key: str, user: dict = Depends(get_current_user), db=Depends(get_db)):
    _WIDGET_DEFAULTS = {
        "deal_page_widgets": DEFAULT_DEAL_WIDGETS,
        "pipeline_page_widgets": DEFAULT_PIPELINE_WIDGETS,
    }

    user_id = _get_user_id_from_token(user, db)
    if not user_id:
        if key in _WIDGET_DEFAULTS:
            return {"widgets": _WIDGET_DEFAULTS[key]}
        return {"value": None}

    pref = db.query(UserPreference).filter(
        UserPreference.user_id == user_id,
        UserPreference.preference_key == key,
    ).first()

    if not pref:
        if key in _WIDGET_DEFAULTS:
            return {"widgets": _WIDGET_DEFAULTS[key]}
        return {"value": None}

    return json.loads(pref.preference_value)


@router.put("/{key}")
def save_preference(key: str, body: PreferenceUpdate, user: dict = Depends(get_current_user), db=Depends(get_db)):
    user_id = _get_user_id_from_token(user, db)
    if not user_id:
        raise HTTPException(status_code=404, detail="User not found")

    pref = db.query(UserPreference).filter(
        UserPreference.user_id == user_id,
        UserPreference.preference_key == key,
    ).first()

    value_json = json.dumps(body.value)

    if pref:
        pref.preference_value = value_json
        pref.updated_at = datetime.now(timezone.utc).isoformat()
    else:
        pref = UserPreference(
            user_id=user_id,
            preference_key=key,
            preference_value=value_json,
        )
        db.add(pref)

    db.commit()
    return json.loads(pref.preference_value)
