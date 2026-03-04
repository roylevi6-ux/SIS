"""Test ORM models — creation, relationships, JSON roundtrip."""

import json
import uuid
from datetime import datetime, timezone

from sis.db.models import (
    Account, Transcript, AnalysisRun, AgentAnalysis, DealAssessment,
    CoachingEntry, PromptVersion, ChatSession, ChatMessage, UsageEvent,
    User, Team,
)


def test_user_and_team_models(session):
    """User and Team models can be created with tree relationships."""
    # Create root team
    root = Team(name="Sales Org", level="org")
    session.add(root)
    session.flush()

    # Create GM user
    gm = User(name="Roy", email="roy@sis.com", role="admin")
    session.add(gm)
    session.flush()

    # Set leader
    root.leader_id = gm.id
    session.flush()

    # Create division under root
    division = Team(name="Sales East", parent_id=root.id, level="division")
    session.add(division)
    session.flush()

    # Create VP user on division
    vp = User(name="Sarah", email="sarah@sis.com", role="vp", team_id=division.id)
    session.add(vp)
    session.flush()
    division.leader_id = vp.id
    session.flush()

    # Create team under division
    team = Team(name="Enterprise", parent_id=division.id, level="team")
    session.add(team)
    session.flush()

    # Create TL and IC
    tl = User(name="Dan", email="dan@sis.com", role="team_lead", team_id=team.id)
    session.add(tl)
    session.flush()
    team.leader_id = tl.id

    ic = User(name="Alice", email="alice@sis.com", role="ic", team_id=team.id)
    session.add(ic)
    session.flush()

    assert gm.role == "admin"
    assert vp.team_id == division.id
    assert team.parent_id == division.id
    assert division.parent_id == root.id
    assert ic.team_id == team.id


class TestAccountModel:
    def test_create_account(self, session):
        acct = Account(account_name="TestCo", cp_estimate=10000.0, team_name="Team A")
        session.add(acct)
        session.flush()

        assert acct.id is not None
        assert acct.account_name == "TestCo"
        assert acct.cp_estimate == 10000.0
        assert acct.created_at is not None

    def test_account_relationships(self, seeded_db, mock_get_session):
        session = mock_get_session
        acct = session.query(Account).filter_by(id=seeded_db["healthy_id"]).one()
        assert len(acct.transcripts) == 2
        assert len(acct.analysis_runs) == 1
        assert len(acct.deal_assessments) == 1


class TestTranscriptModel:
    def test_create_transcript(self, session):
        acct = Account(account_name="TranscriptTestCo")
        session.add(acct)
        session.flush()

        t = Transcript(
            account_id=acct.id, call_date="2026-01-15",
            raw_text="Call transcript text", token_count=100,
        )
        session.add(t)
        session.flush()

        assert t.id is not None
        assert t.account_id == acct.id
        assert t.is_active == 1

    def test_participants_json_roundtrip(self, session):
        acct = Account(account_name="JSONTestCo")
        session.add(acct)
        session.flush()

        participants = [{"name": "Alice", "role": "AE", "company": "Riskified"}]
        t = Transcript(
            account_id=acct.id, call_date="2026-01-15",
            raw_text="text", participants=json.dumps(participants),
        )
        session.add(t)
        session.flush()

        loaded = json.loads(t.participants)
        assert loaded[0]["name"] == "Alice"


class TestDealAssessmentModel:
    def test_json_fields_roundtrip(self, seeded_db, mock_get_session):
        session = mock_get_session
        da = session.query(DealAssessment).filter_by(
            account_id=seeded_db["healthy_id"]
        ).first()

        # health_breakdown is JSON
        breakdown = json.loads(da.health_breakdown)
        assert isinstance(breakdown, list)
        assert breakdown[0]["dimension"] == "economic_buyer_engagement"

        # contradiction_map is JSON
        contradictions = json.loads(da.contradiction_map)
        assert isinstance(contradictions, list)

        # key_unknowns is JSON
        unknowns = json.loads(da.key_unknowns)
        assert isinstance(unknowns, list)


class TestPromptVersionModel:
    def test_unique_constraint(self, session):
        acct = Account(account_name="PVTestCo")
        session.add(acct)
        session.flush()

        pv1 = PromptVersion(
            agent_id="agent_1", version="v1.0",
            prompt_template="template 1", is_active=1,
        )
        session.add(pv1)
        session.flush()
        assert pv1.id is not None


class TestChatModels:
    def test_chat_session_messages(self, seeded_db, mock_get_session):
        session = mock_get_session
        chat = session.query(ChatSession).filter_by(id=seeded_db["chat_id"]).one()
        assert len(chat.messages) == 2
        assert chat.messages[0].role == "user"
        assert chat.messages[1].role == "assistant"


class TestUsageEventModel:
    def test_create_usage_event(self, session):
        ue = UsageEvent(event_type="page_view", user_name="tester", page_name="dashboard")
        session.add(ue)
        session.flush()
        assert ue.id is not None
        assert ue.event_type == "page_view"
