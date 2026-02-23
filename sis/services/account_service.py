"""Account service — CRUD + IC forecast + divergence per Technical Architecture Section 6.2."""

from __future__ import annotations

import json
import logging
from typing import Optional

from sis.db.session import get_session
from sis.db.models import Account, DealAssessment

logger = logging.getLogger(__name__)

# Whitelist of fields that can be updated via update_account
UPDATABLE_FIELDS = {"account_name", "mrr_estimate", "ic_forecast_category", "team_lead", "ae_owner", "team_name"}

# Whitelist of fields that can be used for sorting
SORTABLE_FIELDS = {"account_name", "mrr_estimate", "team_name", "created_at", "updated_at"}


def create_account(
    name: str,
    mrr: Optional[float] = None,
    team_lead: Optional[str] = None,
    ae_owner: Optional[str] = None,
    team: Optional[str] = None,
    deal_type: Optional[str] = None,
) -> Account:
    """Create a new account."""
    with get_session() as session:
        account = Account(
            account_name=name,
            mrr_estimate=mrr,
            team_lead=team_lead,
            ae_owner=ae_owner,
            team_name=team,
            deal_type=deal_type,
        )
        session.add(account)
        session.flush()
        session.expunge(account)
        return account


def update_account(account_id: str, **fields) -> Account:
    """Update account fields. Only whitelisted fields are accepted.

    Raises ValueError if account not found.
    Logs warning for any non-whitelisted fields.
    """
    ignored = set(fields.keys()) - UPDATABLE_FIELDS
    if ignored:
        logger.warning("update_account: ignoring non-updatable fields: %s", ignored)

    with get_session() as session:
        account = session.query(Account).filter_by(id=account_id).one_or_none()
        if not account:
            raise ValueError(f"Account not found: {account_id}")
        for key, value in fields.items():
            if key in UPDATABLE_FIELDS:
                setattr(account, key, value)
        session.flush()
        session.expunge(account)
        return account


def set_ic_forecast(account_id: str, category: str) -> dict:
    """Set the IC forecast category. Computes divergence against latest AI forecast.

    Returns:
        dict with divergence_flag and explanation
    """
    valid_categories = {"Commit", "Best Case", "Pipeline", "Upside", "At Risk", "No Decision Risk"}
    if category not in valid_categories:
        raise ValueError(f"Invalid category: {category}. Must be one of {valid_categories}")

    with get_session() as session:
        account = session.query(Account).filter_by(id=account_id).one_or_none()
        if not account:
            raise ValueError(f"Account not found: {account_id}")
        account.ic_forecast_category = category

        # Find latest deal assessment for divergence computation
        latest = (
            session.query(DealAssessment)
            .filter_by(account_id=account_id)
            .order_by(DealAssessment.created_at.desc())
            .first()
        )

        divergence_result = {"divergence_flag": False, "explanation": None}

        if latest:
            ai_category = latest.ai_forecast_category
            if ai_category != category:
                latest.divergence_flag = 1
                explanation = (
                    f"AI forecasts '{ai_category}' but IC forecasts '{category}'. "
                    f"AI rationale: {latest.forecast_rationale or 'N/A'}"
                )
                latest.divergence_explanation = explanation
                divergence_result = {"divergence_flag": True, "explanation": explanation}
            else:
                latest.divergence_flag = 0
                latest.divergence_explanation = None

        session.flush()
        return divergence_result


def list_accounts(
    team: Optional[str] = None,
    sort_by: str = "account_name",
) -> list[dict]:
    """List accounts with latest assessment summary."""
    with get_session() as session:
        query = session.query(Account)
        if team:
            query = query.filter_by(team_name=team)

        if sort_by not in SORTABLE_FIELDS:
            sort_by = "account_name"
        accounts = query.order_by(getattr(Account, sort_by)).all()

        result = []
        for acct in accounts:
            latest_assessment = (
                session.query(DealAssessment)
                .filter_by(account_id=acct.id)
                .order_by(DealAssessment.created_at.desc())
                .first()
            )

            summary = {
                "id": acct.id,
                "account_name": acct.account_name,
                "mrr_estimate": acct.mrr_estimate,
                "team_lead": acct.team_lead,
                "ae_owner": acct.ae_owner,
                "team_name": acct.team_name,
                "ic_forecast_category": acct.ic_forecast_category,
            }

            if latest_assessment:
                summary.update({
                    "health_score": latest_assessment.health_score,
                    "momentum_direction": latest_assessment.momentum_direction,
                    "ai_forecast_category": latest_assessment.ai_forecast_category,
                    "inferred_stage": latest_assessment.inferred_stage,
                    "stage_name": latest_assessment.stage_name,
                    "overall_confidence": latest_assessment.overall_confidence,
                    "divergence_flag": bool(latest_assessment.divergence_flag),
                    "last_assessed": latest_assessment.created_at,
                })
            else:
                summary.update({
                    "health_score": None,
                    "momentum_direction": None,
                    "ai_forecast_category": None,
                    "inferred_stage": None,
                    "stage_name": None,
                    "overall_confidence": None,
                    "divergence_flag": False,
                    "last_assessed": None,
                })

            result.append(summary)
        return result


def get_account_detail(account_id: str) -> dict:
    """Full account detail with latest assessment, transcripts, feedback history."""
    with get_session() as session:
        account = session.query(Account).filter_by(id=account_id).one_or_none()
        if not account:
            raise ValueError(f"Account not found: {account_id}")

        latest_assessment = (
            session.query(DealAssessment)
            .filter_by(account_id=account_id)
            .order_by(DealAssessment.created_at.desc())
            .first()
        )

        transcripts = [
            {
                "id": t.id,
                "call_date": t.call_date,
                "duration_minutes": t.duration_minutes,
                "token_count": t.token_count,
                "is_active": bool(t.is_active),
                "created_at": t.created_at,
            }
            for t in account.transcripts
        ]

        detail = {
            "id": account.id,
            "account_name": account.account_name,
            "mrr_estimate": account.mrr_estimate,
            "team_lead": account.team_lead,
            "ae_owner": account.ae_owner,
            "team_name": account.team_name,
            "ic_forecast_category": account.ic_forecast_category,
            "transcripts": transcripts,
            "assessment": None,
        }

        if latest_assessment:
            detail["assessment"] = {
                "id": latest_assessment.id,
                "deal_memo": latest_assessment.deal_memo,
                "health_score": latest_assessment.health_score,
                "health_breakdown": json.loads(latest_assessment.health_breakdown) if latest_assessment.health_breakdown else {},
                "momentum_direction": latest_assessment.momentum_direction,
                "momentum_trend": latest_assessment.momentum_trend,
                "ai_forecast_category": latest_assessment.ai_forecast_category,
                "forecast_rationale": latest_assessment.forecast_rationale,
                "inferred_stage": latest_assessment.inferred_stage,
                "stage_name": latest_assessment.stage_name,
                "stage_confidence": latest_assessment.stage_confidence,
                "overall_confidence": latest_assessment.overall_confidence,
                "key_unknowns": json.loads(latest_assessment.key_unknowns) if latest_assessment.key_unknowns else [],
                "top_positive_signals": json.loads(latest_assessment.top_positive_signals) if latest_assessment.top_positive_signals else [],
                "top_risks": json.loads(latest_assessment.top_risks) if latest_assessment.top_risks else [],
                "recommended_actions": json.loads(latest_assessment.recommended_actions) if latest_assessment.recommended_actions else [],
                "contradiction_map": json.loads(latest_assessment.contradiction_map) if latest_assessment.contradiction_map else [],
                "divergence_flag": bool(latest_assessment.divergence_flag),
                "divergence_explanation": latest_assessment.divergence_explanation,
                "created_at": latest_assessment.created_at,
            }

        return detail
