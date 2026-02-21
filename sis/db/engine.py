"""SQLAlchemy engine setup — SQLite for POC, PostgreSQL-compatible schema.

Per Technical Architecture Section 4:
- SQLite with TEXT timestamps, UUIDs, and JSON columns
- PostgreSQL migration path documented in migration notes
"""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine

from config import DATABASE_URL

_engine: Engine | None = None


def get_engine() -> Engine:
    """Get or create the shared SQLAlchemy engine."""
    global _engine
    if _engine is None:
        _engine = create_engine(
            DATABASE_URL,
            echo=False,
            future=True,
        )
        # Enable WAL mode and foreign keys for SQLite
        if DATABASE_URL.startswith("sqlite"):
            @event.listens_for(_engine, "connect")
            def set_sqlite_pragma(dbapi_conn, connection_record):
                cursor = dbapi_conn.cursor()
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()
    return _engine


def init_db() -> None:
    """Create all tables. Safe to call multiple times (CREATE IF NOT EXISTS)."""
    from .models import Base
    engine = get_engine()
    Base.metadata.create_all(engine)


def reset_engine() -> None:
    """Reset the engine (for testing)."""
    global _engine
    if _engine is not None:
        _engine.dispose()
        _engine = None
