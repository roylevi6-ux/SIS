"""FastAPI dependency injection providers."""

from __future__ import annotations

from typing import Generator

from sqlalchemy.orm import Session

from sis.db.session import get_session


def get_db() -> Generator[Session, None, None]:
    """Yield a transactional DB session, auto-closing on exit."""
    with get_session() as session:
        yield session
