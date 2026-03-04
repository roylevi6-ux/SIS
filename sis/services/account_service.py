"""Account service — CRUD + rep forecast + divergence per Technical Architecture Section 6.2."""

from __future__ import annotations

import json
import logging
from typing import Optional

from sis.db.session import get_session
from sis.db.models import (
    Account, AnalysisRun, DealAssessment,
    AgentAnalysis, Transcript, CoachingEntry,
    User, Team,
)

logger = logging.getLogger(__name__)


def normalize_account_name(name: str) -> str:
    """Normalize account name to Title Case for consistent dedup."""
    return name.strip().title()


# Whitelist of fields that can be updated via update_account
UPDATABLE_FIELDS = {"account_name", "cp_estimate", "team_lead", "ae_owner", "team_name", "deal_type", "prior_contract_value", "owner_id", "sf_stage", "sf_forecast_category", "sf_close_quarter", "buying_culture"}

# Whitelist of fields that can be used for sorting
SORTABLE_FIELDS = {"account_name", "cp_estimate", "team_name", "created_at", "updated_at"}


def create_account(
    name: str,
    cp_estimate: Optional[float] = None,
    team_lead: Optional[str] = None,
    ae_owner: Optional[str] = None,
    team: Optional[str] = None,
    deal_type: str = "new_logo",
    prior_contract_value: Optional[float] = None,
    owner_id: Optional[str] = None,
    sf_stage: Optional[int] = None,
    sf_forecast_category: Optional[str] = None,
    sf_close_quarter: Optional[str] = None,
    buying_culture: str = "direct",
) -> Account:
    """Create a new account.

    When owner_id is provided, auto-resolve ae_owner, team_lead, and team_name
    from the org hierarchy (User → Team → Team.leader).
    """
    with get_session() as session:
        # Auto-resolve hierarchy fields from owner_id
        if owner_id:
            owner = session.query(User).filter_by(id=owner_id).first()
            if owner:
                ae_owner = ae_owner or owner.name
                if owner.team_id:
                    owner_team = session.query(Team).filter_by(id=owner.team_id).first()
                    if owner_team:
                        team = team or owner_team.name
                        if owner_team.leader_id:
                            leader = session.query(User).filter_by(id=owner_team.leader_id).first()
                            if leader:
                                team_lead = team_lead or leader.name

        account = Account(
            account_name=normalize_account_name(name),
            cp_estimate=cp_estimate,
            team_lead=team_lead,
            ae_owner=ae_owner,
            team_name=team,
            deal_type=deal_type,
            prior_contract_value=prior_contract_value,
            owner_id=owner_id,
            sf_stage=sf_stage,
            sf_forecast_category=sf_forecast_category,
            sf_close_quarter=sf_close_quarter,
            buying_culture=buying_culture,
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
                if key == "account_name":
                    value = normalize_account_name(value)
                setattr(account, key, value)
        session.flush()
        session.expunge(account)
        return account


def set_rep_forecast(account_id: str, category: str) -> dict:
    """Set the rep (SF) forecast category. Computes divergence against latest AI forecast.

    Returns:
        dict with divergence_flag and explanation
    """
    valid_categories = {"Commit", "Realistic", "Upside", "At Risk"}
    if category not in valid_categories:
        raise ValueError(f"Invalid category: {category}. Must be one of {valid_categories}")

    with get_session() as session:
        account = session.query(Account).filter_by(id=account_id).one_or_none()
        if not account:
            raise ValueError(f"Account not found: {account_id}")
        account.sf_forecast_category = category

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
            # "At Risk" is SIS-only — treat as aligned with SF "Upside"
            is_match = (ai_category == category) or (ai_category == "At Risk" and category == "Upside")
            if not is_match:
                latest.divergence_flag = 1
                explanation = (
                    f"AI forecasts '{ai_category}' but rep set "
                    f"'{category}' in Salesforce. "
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
    visible_user_ids: Optional[set[str]] = None,
) -> list[dict]:
    """List accounts with latest assessment summary.

    Args:
        team: Legacy team name filter (optional, backward compat)
        sort_by: Sort column
        visible_user_ids: If provided, only return accounts where owner_id is in this set.
                          None means no scoping (admin/gm sees all).
    """
    with get_session() as session:
        query = session.query(Account)
        if visible_user_ids is not None:
            query = query.filter(Account.owner_id.in_(visible_user_ids))
        elif team:
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
                "account_id": acct.id,
                "account_name": acct.account_name,
                "cp_estimate": acct.cp_estimate,
                "team_lead": acct.team_lead,
                "ae_owner": acct.ae_owner,
                "team_name": acct.team_name,
                "sf_stage": acct.sf_stage,
                "sf_forecast_category": acct.sf_forecast_category,
                "sf_close_quarter": acct.sf_close_quarter,
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
                    "stage_gap_direction": latest_assessment.stage_gap_direction,
                    "stage_gap_magnitude": latest_assessment.stage_gap_magnitude,
                    "forecast_gap_direction": latest_assessment.forecast_gap_direction,
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
                    "stage_gap_direction": None,
                    "stage_gap_magnitude": None,
                    "forecast_gap_direction": None,
                })

            result.append(summary)
        return result


def delete_account(account_id: str) -> dict:
    """Delete an account and all related data in correct FK dependency order.

    Returns dict with account_name and total rows_deleted.
    """
    with get_session() as session:
        account = session.query(Account).filter_by(id=account_id).one_or_none()
        if not account:
            raise ValueError(f"Account not found: {account_id}")

        account_name = account.account_name
        total_deleted = 0

        # 1. coaching_entries (FK to account_id)
        n = session.query(CoachingEntry).filter_by(account_id=account_id).delete()
        total_deleted += n

        # 3. agent_analyses (FK to analysis_run_id — get run IDs first)
        run_ids = [
            r.id for r in
            session.query(AnalysisRun.id).filter_by(account_id=account_id).all()
        ]
        if run_ids:
            n = session.query(AgentAnalysis).filter(
                AgentAnalysis.analysis_run_id.in_(run_ids)
            ).delete(synchronize_session="fetch")
            total_deleted += n

        # 4. deal_assessments (FK to account_id)
        n = session.query(DealAssessment).filter_by(account_id=account_id).delete()
        total_deleted += n

        # 5. analysis_runs (FK to account_id)
        n = session.query(AnalysisRun).filter_by(account_id=account_id).delete()
        total_deleted += n

        # 6. transcripts (FK to account_id)
        n = session.query(Transcript).filter_by(account_id=account_id).delete()
        total_deleted += n

        # 7. account itself
        session.delete(account)
        total_deleted += 1

        logger.info(
            "Deleted account %s (%s) — %d rows total",
            account_id, account_name, total_deleted,
        )
        return {"account_name": account_name, "rows_deleted": total_deleted}


def resolve_account_by_name(
    name: str,
    visible_user_ids: set[str] | None = None,
) -> dict | None:
    """Fuzzy-match an account name from user input.

    Handles underscores vs spaces, case differences, partial matches.
    Returns the best-matching account summary dict or None.
    """
    accounts = list_accounts(visible_user_ids=visible_user_ids)
    if not accounts:
        return None

    def _normalize(s: str) -> str:
        return s.replace("_", " ").lower().strip()

    query_norm = _normalize(name)
    best_match = None
    best_length = 0

    for acct in accounts:
        acct_name = acct.get("account_name", "")
        if not acct_name:
            continue
        acct_norm = _normalize(acct_name)

        # Exact normalized match
        if acct_norm == query_norm:
            return acct

        # Full-name substring match (prefer longest)
        if acct_norm in query_norm or query_norm in acct_norm:
            match_len = len(acct_norm)
            if match_len > best_length:
                best_match = acct
                best_length = match_len
            continue

        # Multi-word: all significant words present
        words = [w for w in query_norm.split() if len(w) > 2]
        if words and all(w in acct_norm for w in words):
            match_len = sum(len(w) for w in words)
            if match_len > best_length:
                best_match = acct
                best_length = match_len

    return best_match


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

        # Determine which transcripts were used in the latest analysis
        latest_run = (
            session.query(AnalysisRun)
            .filter_by(account_id=account_id)
            .order_by(AnalysisRun.started_at.desc())
            .first()
        )
        analyzed_ids: set[str] = set()
        if latest_run and latest_run.transcript_ids:
            analyzed_ids = set(json.loads(latest_run.transcript_ids))

        transcripts = [
            {
                "id": t.id,
                "call_date": t.call_date,
                "duration_minutes": t.duration_minutes,
                "token_count": t.token_count,
                "is_active": bool(t.is_active),
                "created_at": t.created_at,
                "participants": json.loads(t.participants) if t.participants else None,
                "call_title": t.call_title,
                "call_topics": json.loads(t.call_topics) if t.call_topics else None,
                "analyzed": t.id in analyzed_ids,
            }
            for t in account.transcripts
        ]

        detail = {
            "id": account.id,
            "account_name": account.account_name,
            "cp_estimate": account.cp_estimate,
            "team_lead": account.team_lead,
            "ae_owner": account.ae_owner,
            "team_name": account.team_name,
            "sf_stage": account.sf_stage,
            "sf_forecast_category": account.sf_forecast_category,
            "sf_close_quarter": account.sf_close_quarter,
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
                "sf_stage_at_run": latest_assessment.sf_stage_at_run,
                "sf_forecast_at_run": latest_assessment.sf_forecast_at_run,
                "sf_close_quarter_at_run": latest_assessment.sf_close_quarter_at_run,
                "cp_estimate_at_run": latest_assessment.cp_estimate_at_run,
                "stage_gap_direction": latest_assessment.stage_gap_direction,
                "stage_gap_magnitude": latest_assessment.stage_gap_magnitude,
                "forecast_gap_direction": latest_assessment.forecast_gap_direction,
                "sf_gap_interpretation": latest_assessment.sf_gap_interpretation,
                "manager_brief": latest_assessment.manager_brief,
                "attention_level": latest_assessment.attention_level,
                "deal_memo_sections": json.loads(latest_assessment.deal_memo_sections) if latest_assessment.deal_memo_sections else [],
                "created_at": latest_assessment.created_at,
            }

        return detail
