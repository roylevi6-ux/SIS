"""Deal Context API routes — submit, retrieve, question catalog."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from sis.api.deps import get_current_user, require_role
from sis.constants import DEAL_CONTEXT_QUESTIONS
from sis.services import deal_context_service
from sis.api.schemas.deal_context import DealContextUpsert

router = APIRouter(prefix="/api/deal-context", tags=["deal-context"])


# NOTE: /questions must be registered BEFORE /{account_id} to avoid path conflict.


@router.get("/questions")
def get_questions(user: dict = Depends(get_current_user)):
    """Return the question catalog for rendering the form."""
    result = {}
    for k, v in DEAL_CONTEXT_QUESTIONS.items():
        entry = {
            "label": v["label"],
            "category": v["category"],
            "input_type": v["input_type"],
        }
        for extra_key in ("options", "scale_min", "scale_max", "max_chars", "change_categories"):
            if extra_key in v:
                entry[extra_key] = v[extra_key]
        result[str(k)] = entry
    return result


@router.get("/{account_id}")
def get_context(account_id: str, user: dict = Depends(get_current_user)):
    """Get current deal context + history for an account."""
    return deal_context_service.get_current_context(account_id)


@router.post("/")
def upsert(body: DealContextUpsert, user: dict = Depends(get_current_user)):
    """Submit or update deal context. Requires TL+ role."""
    require_role(user, "team_lead")
    try:
        return deal_context_service.upsert_context(
            account_id=body.account_id,
            author_id=user["user_id"],
            entries=[e.model_dump() for e in body.entries],
        )
    except ValueError as e:
        raise HTTPException(
            status_code=404 if "not found" in str(e).lower() else 422,
            detail=str(e),
        )
