"""Shared test fixtures — in-memory SQLite, seeded data, mock LLM clients.

All tests use transactional sessions that roll back after each test.
No LLM API calls are made — everything is mocked.
"""

from __future__ import annotations

import json
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, AsyncMock, patch

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session

from sis.db.models import (
    Base, Account, Transcript, AnalysisRun, AgentAnalysis, DealAssessment,
    ScoreFeedback, CoachingEntry, CalibrationLog, PromptVersion,
    ChatSession, ChatMessage, UsageEvent,
)


def _uuid() -> str:
    return str(uuid.uuid4())


def _now(days_ago: int = 0) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat()


# ── Engine & session fixtures ──────────────────────────────────────────


@pytest.fixture(scope="session")
def engine():
    """In-memory SQLite engine with FK pragmas. Shared across all tests."""
    eng = create_engine("sqlite:///:memory:", echo=False, future=True)

    @event.listens_for(eng, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(eng)
    return eng


@pytest.fixture
def session_factory(engine):
    """Session factory bound to test engine."""
    return sessionmaker(bind=engine, expire_on_commit=False)


@pytest.fixture
def session(session_factory):
    """Transactional session that rolls back after each test."""
    sess = session_factory()
    yield sess
    sess.rollback()
    sess.close()


@pytest.fixture
def mock_get_session(session):
    """Patch sis.db.session.get_session to use the test session."""
    @contextmanager
    def _test_get_session():
        yield session

    with patch("sis.db.session.get_session", _test_get_session):
        yield session


# ── Seeded data fixture ────────────────────────────────────────────────


@pytest.fixture
def seeded_db(mock_get_session):
    """Seed 3 accounts (healthy/at_risk/critical) with full related data.

    Returns a dict with all created IDs for assertions.
    """
    session = mock_get_session

    # Accounts
    healthy_id = _uuid()
    at_risk_id = _uuid()
    critical_id = _uuid()

    accounts = [
        Account(id=healthy_id, account_name="HealthyCorp", mrr_estimate=50000.0,
                team_lead="TL One", ae_owner="AE One", team_name="Team Alpha",
                ic_forecast_category="Commit", created_at=_now(30), updated_at=_now(1)),
        Account(id=at_risk_id, account_name="AtRiskCo", mrr_estimate=25000.0,
                team_lead="TL One", ae_owner="AE Two", team_name="Team Alpha",
                ic_forecast_category="Pipeline", created_at=_now(30), updated_at=_now(1)),
        Account(id=critical_id, account_name="CriticalInc", mrr_estimate=10000.0,
                team_lead="TL Two", ae_owner="AE Three", team_name="Team Beta",
                ic_forecast_category="At Risk", created_at=_now(30), updated_at=_now(1)),
    ]
    for a in accounts:
        session.add(a)
    session.flush()

    # Transcripts (2 per account)
    transcript_ids = {}
    for acct_id, name in [(healthy_id, "healthy"), (at_risk_id, "atrisk"), (critical_id, "critical")]:
        t_ids = []
        for i in range(1, 3):
            t_id = _uuid()
            session.add(Transcript(
                id=t_id, account_id=acct_id,
                call_date=(datetime.now(timezone.utc) - timedelta(days=10 * i)).strftime("%Y-%m-%d"),
                participants=json.dumps([{"name": "Rep", "role": "AE", "company": "Riskified"}]),
                duration_minutes=30 + i * 5,
                raw_text=f"Transcript {i} for {name}: discovery call content here.",
                preprocessed_text=f"Transcript {i} for {name}: discovery call content here.",
                token_count=500, upload_source="test", is_active=1, created_at=_now(10 * i),
            ))
            t_ids.append(t_id)
        transcript_ids[acct_id] = t_ids
    session.flush()

    # Analysis runs
    run_ids = {}
    for acct_id, name in [(healthy_id, "healthy"), (at_risk_id, "atrisk"), (critical_id, "critical")]:
        run_id = _uuid()
        session.add(AnalysisRun(
            id=run_id, account_id=acct_id, started_at=_now(2), completed_at=_now(2),
            status="completed", trigger="test",
            transcript_ids=json.dumps(transcript_ids[acct_id]),
            total_input_tokens=30000, total_output_tokens=8000, total_cost_usd=0.25,
            model_versions=json.dumps({"agent_1": "haiku", "agent_10": "opus"}),
            prompt_config_version="v1.0",
        ))
        run_ids[acct_id] = run_id
    session.flush()

    # Agent analyses (9 per run, agents 1-9)
    agent_names = {
        "agent_1": "Stage & Progress", "agent_2": "Relationship", "agent_3": "Commercial",
        "agent_4": "Momentum", "agent_5": "Technical", "agent_6": "Economic Buyer",
        "agent_7": "MSP & Next Steps", "agent_8": "Competitive", "agent_9": "Open Discovery",
    }
    for acct_id in [healthy_id, at_risk_id, critical_id]:
        for agent_num in range(1, 10):
            agent_id = f"agent_{agent_num}"
            session.add(AgentAnalysis(
                id=_uuid(), analysis_run_id=run_ids[acct_id], account_id=acct_id,
                agent_id=agent_id, agent_name=agent_names[agent_id],
                transcript_count_analyzed=2,
                narrative=f"Analysis by {agent_id}.",
                findings=json.dumps({"key": f"value_{agent_num}"}),
                evidence=json.dumps([{"quote": "evidence quote", "interpretation": "interpretation"}]),
                confidence_overall=0.75, confidence_rationale="Based on transcript signals",
                data_gaps=json.dumps([]), sparse_data_flag=0,
                input_tokens=3000, output_tokens=800, cost_usd=0.02,
                model_used="anthropic/claude-sonnet-4-20250514", retries=0,
                status="completed", created_at=_now(2),
            ))
    session.flush()

    # Deal assessments
    assessment_ids = {}
    health_scores = {healthy_id: 82, at_risk_id: 55, critical_id: 35}
    forecasts = {healthy_id: "Commit", at_risk_id: "Pipeline", critical_id: "At Risk"}
    momenta = {healthy_id: "Improving", at_risk_id: "Stable", critical_id: "Declining"}

    for acct_id in [healthy_id, at_risk_id, critical_id]:
        da_id = _uuid()
        session.add(DealAssessment(
            id=da_id, analysis_run_id=run_ids[acct_id], account_id=acct_id,
            deal_memo=f"Deal memo for account {acct_id[:8]}.",
            contradiction_map=json.dumps([
                {"agents": ["agent_2", "agent_4"], "issue": "Engagement mismatch",
                 "resolution": "Async communication explains lower cadence"}
            ]),
            inferred_stage=3, stage_name="Evaluation", stage_confidence=0.80,
            stage_reasoning="Transcript signals align with Evaluation stage.",
            health_score=health_scores[acct_id],
            health_breakdown=json.dumps([
                {"dimension": "economic_buyer_engagement", "score": 70, "weight": 20, "weighted_contribution": 14.0},
            ]),
            overall_confidence=0.75, confidence_rationale="Based on 2 transcripts.",
            key_unknowns=json.dumps(["Budget timeline"]),
            momentum_direction=momenta[acct_id],
            momentum_trend=f"{momenta[acct_id]} trend",
            ai_forecast_category=forecasts[acct_id],
            forecast_confidence=0.75,
            forecast_rationale=f"Health {health_scores[acct_id]} supports {forecasts[acct_id]}.",
            top_positive_signals=json.dumps([{"signal": "Active engagement", "strength": "strong"}]),
            top_risks=json.dumps([{"risk": "Budget uncertain", "severity": "medium"}]),
            recommended_actions=json.dumps([{"action": "Schedule exec briefing", "priority": "high"}]),
            divergence_flag=0, divergence_explanation=None, created_at=_now(2),
        ))
        assessment_ids[acct_id] = da_id
    session.flush()

    # Score feedback (2 entries)
    fb1_id = _uuid()
    session.add(ScoreFeedback(
        id=fb1_id, account_id=healthy_id, deal_assessment_id=assessment_ids[healthy_id],
        author="AE One", feedback_date=_now(1), health_score_at_time=82,
        disagreement_direction="too_high", reason_category="off_channel",
        free_text="Score doesn't capture recent meeting", off_channel_activity=1,
        resolution="pending", created_at=_now(1),
    ))
    fb2_id = _uuid()
    session.add(ScoreFeedback(
        id=fb2_id, account_id=critical_id, deal_assessment_id=assessment_ids[critical_id],
        author="AE Three", feedback_date=_now(1), health_score_at_time=35,
        disagreement_direction="too_low", reason_category="recent_change",
        free_text="New stakeholder engaged", off_channel_activity=0,
        resolution="accepted", resolution_notes="Valid", resolved_at=_now(0),
        resolved_by="TL Two", created_at=_now(1),
    ))
    session.flush()

    # Coaching entries (2)
    session.add(CoachingEntry(
        id=_uuid(), account_id=healthy_id, rep_name="AE One", coach_name="TL One",
        dimension="economic_buyer_engagement", coaching_date=_now(5),
        feedback_text="Excellent EB engagement.", dimension_score_at_time=85,
        health_score_at_time=82, incorporated=1, incorporated_at=_now(2),
        incorporated_notes="Applied", created_at=_now(5),
    ))
    session.add(CoachingEntry(
        id=_uuid(), account_id=critical_id, rep_name="AE Three", coach_name="TL Two",
        dimension="momentum_quality", coaching_date=_now(5),
        feedback_text="Need to re-engage.", dimension_score_at_time=30,
        health_score_at_time=35, incorporated=0, created_at=_now(5),
    ))
    session.flush()

    # Prompt versions (2)
    session.add(PromptVersion(
        id=_uuid(), agent_id="agent_1", version="v1.0",
        prompt_template="System prompt for agent_1", calibration_config_version="v1.0",
        change_notes="Initial", is_active=1, created_at=_now(30),
    ))
    session.add(PromptVersion(
        id=_uuid(), agent_id="agent_10", version="v1.0",
        prompt_template="System prompt for agent_10", calibration_config_version="v1.0",
        change_notes="Initial", is_active=1, created_at=_now(30),
    ))
    session.flush()

    # Chat session + messages
    chat_id = _uuid()
    session.add(ChatSession(
        id=chat_id, user_name="tester", started_at=_now(1), last_message_at=_now(0),
    ))
    msg1_id = _uuid()
    session.add(ChatMessage(
        id=msg1_id, session_id=chat_id, role="user", content="Test question",
        tokens_used=10, created_at=_now(1),
    ))
    msg2_id = _uuid()
    session.add(ChatMessage(
        id=msg2_id, session_id=chat_id, role="assistant", content="Test answer",
        tokens_used=20, model_used="anthropic/claude-sonnet-4-20250514", created_at=_now(0),
    ))
    session.flush()

    # Usage events (3)
    for i, et in enumerate(["page_view", "chat_query", "analysis_run"]):
        session.add(UsageEvent(
            id=_uuid(), event_type=et, user_name="tester",
            account_id=healthy_id, page_name="dashboard",
            event_metadata=json.dumps({"test": True}), created_at=_now(i),
        ))
    session.flush()

    return {
        "healthy_id": healthy_id,
        "at_risk_id": at_risk_id,
        "critical_id": critical_id,
        "run_ids": run_ids,
        "assessment_ids": assessment_ids,
        "transcript_ids": transcript_ids,
        "feedback_ids": [fb1_id, fb2_id],
        "chat_id": chat_id,
    }


# ── Mock Anthropic client ─────────────────────────────────────────────


@pytest.fixture
def mock_anthropic_client():
    """Mocked sync/async Anthropic clients returning deterministic responses."""
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text='{"agent_id": "test", "narrative": "test output"}')]
    mock_response.usage.input_tokens = 1000
    mock_response.usage.output_tokens = 500
    mock_response.stop_reason = "end_turn"

    # Sync client mock
    sync_client = MagicMock()
    stream_ctx = MagicMock()
    stream_ctx.__enter__ = MagicMock(return_value=stream_ctx)
    stream_ctx.__exit__ = MagicMock(return_value=False)
    stream_ctx.get_final_message.return_value = mock_response
    sync_client.messages.stream.return_value = stream_ctx

    # Async client mock
    async_client = AsyncMock()
    async_stream_ctx = AsyncMock()
    async_stream_ctx.__aenter__ = AsyncMock(return_value=async_stream_ctx)
    async_stream_ctx.__aexit__ = AsyncMock(return_value=False)
    async_stream_ctx.get_final_message = AsyncMock(return_value=mock_response)
    async_client.messages.stream.return_value = async_stream_ctx

    return {
        "sync": sync_client,
        "async": async_client,
        "response": mock_response,
    }
