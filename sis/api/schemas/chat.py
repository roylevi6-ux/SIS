"""Pydantic schemas for chat endpoints."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class ChatMessage(BaseModel):
    """Incoming chat message with optional conversation history."""

    message: str
    history: Optional[List[Dict[str, Any]]] = None


class ChatResponse(BaseModel):
    """Chat response from the query agent."""

    response: str
