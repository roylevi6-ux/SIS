"""Test user action log service — log_action, get_action_logs, get_action_summary."""

from __future__ import annotations

import json
from contextlib import contextmanager
from unittest.mock import patch

import pytest

from sis.db.models import UserActionLog


@pytest.fixture
def action_log_session(session):
    """Patch get_session in the user_action_log_service module and clear the table."""
    @contextmanager
    def _test_get_session():
        yield session

    # Clean the table first
    session.query(UserActionLog).delete()
    session.flush()

    # Patch where get_session is used, not where it's defined
    with patch("sis.services.user_action_log_service.get_session", _test_get_session):
        yield session

    session.rollback()


class TestLogAction:
    def test_log_action_basic(self, action_log_session):
        from sis.services.user_action_log_service import log_action, ACTION_ANALYSIS_RUN
        session = action_log_session
        log_action(ACTION_ANALYSIS_RUN, action_detail="Ran pipeline", user_name="tester")
        session.flush()
        rows = session.query(UserActionLog).all()
        assert len(rows) == 1
        assert rows[0].action_type == "analysis_run"
        assert rows[0].action_detail == "Ran pipeline"
        assert rows[0].user_name == "tester"

    def test_log_action_with_metadata(self, action_log_session):
        from sis.services.user_action_log_service import log_action, ACTION_IC_FORECAST
        session = action_log_session
        log_action(
            ACTION_IC_FORECAST,
            action_detail="Set forecast",
            metadata={"old": "Realistic", "new": "Commit"},
        )
        session.flush()
        rows = session.query(UserActionLog).all()
        assert len(rows) == 1
        meta = json.loads(rows[0].metadata_json)
        assert meta["old"] == "Realistic"
        assert meta["new"] == "Commit"

    def test_log_action_with_page_and_name(self, action_log_session):
        from sis.services.user_action_log_service import log_action, ACTION_CHAT_QUERY
        session = action_log_session
        log_action(
            ACTION_CHAT_QUERY,
            action_detail="Hello",
            account_name="TestCo",
            page_name="Chat",
        )
        session.flush()
        row = session.query(UserActionLog).first()
        assert row.account_name == "TestCo"
        assert row.page_name == "Chat"
        assert row.account_id is None  # no FK reference

    def test_log_action_null_metadata(self, action_log_session):
        from sis.services.user_action_log_service import log_action, ACTION_ANALYSIS_RUN
        session = action_log_session
        log_action(ACTION_ANALYSIS_RUN, metadata=None)
        session.flush()
        row = session.query(UserActionLog).first()
        assert row.metadata_json is None


class TestGetActionLogs:
    def test_get_action_logs_empty(self, action_log_session):
        from sis.services.user_action_log_service import get_action_logs
        logs = get_action_logs(days=30)
        assert logs == []

    def test_get_action_logs_returns_recent(self, action_log_session):
        from sis.services.user_action_log_service import log_action, get_action_logs
        from sis.services.user_action_log_service import ACTION_ANALYSIS_RUN, ACTION_CHAT_QUERY
        log_action(ACTION_ANALYSIS_RUN, action_detail="run1", user_name="alice")
        log_action(ACTION_CHAT_QUERY, action_detail="chat1", user_name="bob")
        logs = get_action_logs(days=30)
        assert len(logs) == 2

    def test_get_action_logs_filter_by_type(self, action_log_session):
        from sis.services.user_action_log_service import log_action, get_action_logs
        from sis.services.user_action_log_service import ACTION_ANALYSIS_RUN, ACTION_CHAT_QUERY
        log_action(ACTION_ANALYSIS_RUN, action_detail="run1")
        log_action(ACTION_CHAT_QUERY, action_detail="chat1")
        logs = get_action_logs(days=30, action_type=ACTION_ANALYSIS_RUN)
        assert len(logs) == 1
        assert logs[0]["action_type"] == "analysis_run"

    def test_get_action_logs_filter_by_user(self, action_log_session):
        from sis.services.user_action_log_service import log_action, get_action_logs
        from sis.services.user_action_log_service import ACTION_ANALYSIS_RUN
        log_action(ACTION_ANALYSIS_RUN, user_name="alice")
        log_action(ACTION_ANALYSIS_RUN, user_name="bob")
        logs = get_action_logs(days=30, user_name="alice")
        assert len(logs) == 1
        assert logs[0]["user_name"] == "alice"

    def test_get_action_logs_anonymous_fallback(self, action_log_session):
        from sis.services.user_action_log_service import log_action, get_action_logs
        from sis.services.user_action_log_service import ACTION_ANALYSIS_RUN
        log_action(ACTION_ANALYSIS_RUN)  # no user_name
        logs = get_action_logs(days=30)
        assert logs[0]["user_name"] == "anonymous"

    def test_get_action_logs_metadata_parsed(self, action_log_session):
        from sis.services.user_action_log_service import log_action, get_action_logs
        from sis.services.user_action_log_service import ACTION_IC_FORECAST
        log_action(ACTION_IC_FORECAST, metadata={"key": "val"})
        logs = get_action_logs(days=30)
        assert logs[0]["metadata"] == {"key": "val"}

    def test_get_action_logs_limit(self, action_log_session):
        from sis.services.user_action_log_service import log_action, get_action_logs
        from sis.services.user_action_log_service import ACTION_ANALYSIS_RUN
        for i in range(10):
            log_action(ACTION_ANALYSIS_RUN, action_detail=f"run_{i}")
        logs = get_action_logs(days=30, limit=3)
        assert len(logs) == 3


class TestGetActionSummary:
    def test_summary_empty(self, action_log_session):
        from sis.services.user_action_log_service import get_action_summary
        summary = get_action_summary(days=30)
        assert summary["total"] == 0
        assert summary["by_type"] == {}
        assert summary["by_user"] == {}

    def test_summary_counts(self, action_log_session):
        from sis.services.user_action_log_service import (
            log_action, get_action_summary,
            ACTION_ANALYSIS_RUN, ACTION_CHAT_QUERY,
        )
        log_action(ACTION_ANALYSIS_RUN, user_name="alice")
        log_action(ACTION_ANALYSIS_RUN, user_name="alice")
        log_action(ACTION_CHAT_QUERY, user_name="bob")
        summary = get_action_summary(days=30)
        assert summary["total"] == 3
        assert summary["by_type"]["analysis_run"] == 2
        assert summary["by_type"]["chat_query"] == 1
        assert summary["by_user"]["alice"] == 2
        assert summary["by_user"]["bob"] == 1
