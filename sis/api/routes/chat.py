"""Chat API route — sync endpoint for LLM-powered pipeline Q&A."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends

from sis.api.deps import get_optional_user
from sis.api.schemas.chat import ChatMessage
from sis.services import query_service

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/query")
def query(body: ChatMessage, user: Optional[dict] = Depends(get_optional_user)):
    """Query the AI assistant. Blocks until response is ready.

    This is intentionally a sync ``def`` — query_service uses
    ``client.messages.stream()`` which blocks.  FastAPI will run it
    in an external thread-pool automatically.
    """
    result = query_service.query(body.message, body.history or [])
    return {"response": result}
