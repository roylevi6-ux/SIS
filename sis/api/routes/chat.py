"""Chat API route — sync endpoint for LLM-powered pipeline Q&A."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from sis.api.deps import get_current_user, get_db, resolve_scoping
from sis.api.schemas.chat import ChatMessage
from sis.services import query_service

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/query")
def query(
    body: ChatMessage,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Query the AI assistant. Blocks until response is ready.

    This is intentionally a sync ``def`` — query_service uses
    ``client.messages.stream()`` which blocks.  FastAPI will run it
    in an external thread-pool automatically.
    """
    visible_ids = resolve_scoping(user, db)
    result = query_service.query(body.message, body.history or [], visible_user_ids=visible_ids)
    return {"response": result}
