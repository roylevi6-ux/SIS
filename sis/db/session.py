"""Session management for SQLAlchemy."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Generator

from sqlalchemy.orm import Session as SASession, sessionmaker

from .engine import get_engine

_SessionFactory: sessionmaker | None = None


def _get_factory() -> sessionmaker:
    global _SessionFactory
    if _SessionFactory is None:
        _SessionFactory = sessionmaker(bind=get_engine(), expire_on_commit=False)
    return _SessionFactory


# Alias for type annotations
Session = SASession


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """Context manager that provides a transactional DB session.

    Usage:
        with get_session() as session:
            session.add(account)
            # auto-commits on exit, auto-rollbacks on exception
    """
    session = _get_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
