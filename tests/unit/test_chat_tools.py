"""Tests for chat tool definitions and executor."""
from __future__ import annotations

import json
import pytest
from sis.services.query_service import TOOL_DEFINITIONS, execute_tool


class TestToolDefinitions:

    def test_all_tools_defined(self):
        names = {t["name"] for t in TOOL_DEFINITIONS}
        assert names == {
            "get_deal_assessment",
            "get_agent_analysis",
            "get_all_agent_evidence",
            "list_deal_transcripts",
            "search_transcript",
        }

    def test_all_tools_have_required_fields(self):
        for tool in TOOL_DEFINITIONS:
            assert "name" in tool
            assert "description" in tool
            assert "input_schema" in tool
            assert tool["input_schema"]["type"] == "object"

    def test_account_name_required_on_deal_tools(self):
        for tool in TOOL_DEFINITIONS:
            if tool["name"] != "search_transcript":
                assert "account_name" in tool["input_schema"]["properties"]
                assert "account_name" in tool["input_schema"]["required"]


class TestExecuteTool:

    def test_get_deal_assessment(self, seeded_db, mock_get_session):
        result = execute_tool("get_deal_assessment", {"account_name": "HealthyCorp"})
        parsed = json.loads(result)
        assert parsed["account_name"] == "HealthyCorp"
        assert "health_score" in parsed
        assert "deal_memo" in parsed

    def test_get_agent_analysis(self, seeded_db, mock_get_session):
        result = execute_tool("get_agent_analysis", {
            "account_name": "HealthyCorp",
            "agent_name": "agent_2",
        })
        parsed = json.loads(result)
        assert parsed["agent_id"] == "agent_2"
        assert "narrative" in parsed
        assert "evidence" in parsed
        assert "findings" in parsed

    def test_get_all_agent_evidence(self, seeded_db, mock_get_session):
        result = execute_tool("get_all_agent_evidence", {"account_name": "HealthyCorp"})
        parsed = json.loads(result)
        assert parsed["account_name"] == "HealthyCorp"
        assert "by_agent" in parsed
        assert len(parsed["by_agent"]) > 0

    def test_list_deal_transcripts(self, seeded_db, mock_get_session):
        result = execute_tool("list_deal_transcripts", {"account_name": "HealthyCorp"})
        parsed = json.loads(result)
        assert parsed["transcript_count"] > 0
        assert "transcripts" in parsed

    def test_search_transcript(self, seeded_db, mock_get_session):
        t_id = seeded_db["transcript_ids"][seeded_db["healthy_id"]][0]
        result = execute_tool("search_transcript", {
            "transcript_id": t_id,
            "search_query": "discovery",
        })
        parsed = json.loads(result)
        assert parsed["total_matches"] > 0

    def test_unknown_tool_returns_error(self, seeded_db, mock_get_session):
        result = execute_tool("nonexistent_tool", {})
        parsed = json.loads(result)
        assert "error" in parsed

    def test_unresolved_account_returns_error(self, seeded_db, mock_get_session):
        result = execute_tool("get_deal_assessment", {"account_name": "FakeCo"})
        parsed = json.loads(result)
        assert "error" in parsed
