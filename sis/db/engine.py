"""SQLAlchemy engine setup — supports both SQLite and PostgreSQL.

Per Technical Architecture Section 4:
- SQLite with TEXT timestamps, UUIDs, and JSON columns (dev/test)
- PostgreSQL with connection pooling for production
"""

from __future__ import annotations

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine

from sis.config import DATABASE_URL

_engine: Engine | None = None


def get_engine() -> Engine:
    """Get or create the shared SQLAlchemy engine.

    Engine configuration depends on the DATABASE_URL scheme:
    - sqlite: WAL journal mode, foreign key enforcement
    - postgresql: connection pooling (pool_size=5, max_overflow=10, pool_pre_ping=True)
    """
    global _engine
    if _engine is None:
        if DATABASE_URL.startswith("sqlite"):
            _engine = create_engine(
                DATABASE_URL,
                echo=False,
                future=True,
            )

            @event.listens_for(_engine, "connect")
            def set_sqlite_pragma(dbapi_conn, connection_record):
                cursor = dbapi_conn.cursor()
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()
        else:
            # PostgreSQL (or other server-based databases)
            _engine = create_engine(
                DATABASE_URL,
                echo=False,
                future=True,
                pool_size=5,
                max_overflow=10,
                pool_pre_ping=True,
            )
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
