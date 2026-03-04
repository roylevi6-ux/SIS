"""Database layer — SQLAlchemy ORM models, engine setup, session management.

SQLite for POC, schema designed for PostgreSQL migration.
All timestamps stored as TEXT (ISO 8601) for SQLite compatibility.
"""

from .engine import get_engine, init_db
from .session import get_session, Session
from .models import (
    Account,
    Transcript,
    AnalysisRun,
    AgentAnalysis,
    DealAssessment,
    CoachingEntry,
    CalibrationLog,
    PromptVersion,
    ChatSession,
    ChatMessage,
    Quota,
    DealContextEntry,
)

__all__ = [
    "get_engine",
    "init_db",
    "get_session",
    "Session",
    "Account",
    "Transcript",
    "AnalysisRun",
    "AgentAnalysis",
    "DealAssessment",
    "CoachingEntry",
    "CalibrationLog",
    "PromptVersion",
    "ChatSession",
    "ChatMessage",
    "Quota",
    "DealContextEntry",
]
