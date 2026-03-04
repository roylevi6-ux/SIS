"""Pydantic schemas for Deal Context API."""

from pydantic import BaseModel, Field


class DealContextEntryInput(BaseModel):
    question_id: int = Field(ge=1, le=12)
    response_text: str = Field(max_length=2000)


class DealContextUpsert(BaseModel):
    account_id: str
    entries: list[DealContextEntryInput] = Field(min_length=1, max_length=12)
