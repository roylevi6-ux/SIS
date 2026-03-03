"""Tests for the chat tool-use agentic loop."""
from __future__ import annotations

import json
from unittest.mock import patch, MagicMock
import pytest
from sis.services.query_service import query


def _make_text_response(text: str):
    """Mock a Claude response with just text (no tool use)."""
    msg = MagicMock()
    block = MagicMock()
    block.type = "text"
    block.text = text
    msg.content = [block]
    msg.stop_reason = "end_turn"
    msg.usage = MagicMock(input_tokens=100, output_tokens=50)
    return msg


def _make_tool_use_response(tool_name: str, tool_input: dict, tool_use_id: str = "tool_1"):
    """Mock a Claude response that requests a tool call."""
    msg = MagicMock()
    block = MagicMock()
    block.type = "tool_use"
    block.name = tool_name
    block.input = tool_input
    block.id = tool_use_id
    msg.content = [block]
    msg.stop_reason = "tool_use"
    msg.usage = MagicMock(input_tokens=100, output_tokens=50)
    return msg


_MOCK_OVERVIEW = {"total_deals": 1, "summary": {
    "healthy_count": 1, "total_mrr_healthy": 50000,
    "neutral_count": 0, "total_mrr_neutral": 0,
    "needs_attention_count": 0, "total_mrr_needs_attention": 0,
}}
_MOCK_ACCOUNTS = [
    {"account_name": "TestCo", "health_score": 80, "id": "1",
     "momentum_direction": "Improving", "ai_forecast_category": "Commit",
     "sf_forecast_category": "Commit", "inferred_stage": 5,
     "stage_name": "Negotiate", "cp_estimate": 50000,
     "team_lead": "TL", "ae_owner": "AE", "divergence_flag": False},
]


class TestQueryToolLoop:

    @patch("sis.services.query_service.get_client")
    @patch("sis.services.query_service.list_accounts")
    @patch("sis.services.query_service.get_pipeline_overview")
    @patch("sis.services.query_service.get_divergence_report")
    @patch("sis.services.query_service.get_team_rollup")
    def test_simple_question_no_tools(
        self, mock_rollup, mock_div, mock_overview, mock_accounts, mock_client
    ):
        """Simple pipeline question answered without tools."""
        mock_accounts.return_value = _MOCK_ACCOUNTS
        mock_overview.return_value = _MOCK_OVERVIEW
        mock_div.return_value = []
        mock_rollup.return_value = []

        client = MagicMock()
        mock_client.return_value = client
        client.messages.create.return_value = _make_text_response("You have 1 deal.")

        result = query("How many deals?")
        assert result == "You have 1 deal."

    @patch("sis.services.query_service.execute_tool")
    @patch("sis.services.query_service.get_client")
    @patch("sis.services.query_service.list_accounts")
    @patch("sis.services.query_service.get_pipeline_overview")
    @patch("sis.services.query_service.get_divergence_report")
    @patch("sis.services.query_service.get_team_rollup")
    def test_tool_use_round_trip(
        self, mock_rollup, mock_div, mock_overview, mock_accounts,
        mock_client, mock_exec_tool
    ):
        """Claude calls a tool, gets results, then answers."""
        mock_accounts.return_value = _MOCK_ACCOUNTS
        mock_overview.return_value = _MOCK_OVERVIEW
        mock_div.return_value = []
        mock_rollup.return_value = []

        client = MagicMock()
        mock_client.return_value = client

        tool_response = _make_tool_use_response(
            "get_deal_assessment", {"account_name": "TestCo"}
        )
        text_response = _make_text_response("TestCo health is 80.")

        client.messages.create.side_effect = [tool_response, text_response]
        mock_exec_tool.return_value = json.dumps({"health_score": 80})

        result = query("How is TestCo?")
        assert result == "TestCo health is 80."
        assert mock_exec_tool.call_count == 1

    @patch("sis.services.query_service.execute_tool")
    @patch("sis.services.query_service.get_client")
    @patch("sis.services.query_service.list_accounts")
    @patch("sis.services.query_service.get_pipeline_overview")
    @patch("sis.services.query_service.get_divergence_report")
    @patch("sis.services.query_service.get_team_rollup")
    def test_max_tool_rounds_enforced(
        self, mock_rollup, mock_div, mock_overview, mock_accounts,
        mock_client, mock_exec_tool
    ):
        """Tool loop stops after MAX_TOOL_ROUNDS."""
        mock_accounts.return_value = _MOCK_ACCOUNTS
        mock_overview.return_value = _MOCK_OVERVIEW
        mock_div.return_value = []
        mock_rollup.return_value = []

        client = MagicMock()
        mock_client.return_value = client

        tool_resp = _make_tool_use_response("get_deal_assessment", {"account_name": "X"})
        mock_exec_tool.return_value = json.dumps({"error": "not found"})

        # 3 tool rounds + the forced final text
        client.messages.create.side_effect = [
            tool_resp, tool_resp, tool_resp,
            _make_text_response("Gave up.")
        ]

        result = query("Tell me everything")
        assert mock_exec_tool.call_count == 3
