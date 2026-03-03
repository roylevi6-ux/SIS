"""Tests for transcript keyword search."""
from __future__ import annotations

import json
import pytest
from sis.db.models import Account, Transcript
from sis.services.transcript_service import search_transcript


@pytest.fixture
def transcript_with_content(mock_get_session):
    """Seed an account with a transcript containing searchable text."""
    session = mock_get_session
    acct = Account(
        id="search-test-acct", account_name="SearchCorp",
        cp_estimate=50000, deal_type="new_logo",
    )
    session.add(acct)
    session.flush()

    text = (
        "SARAH CHEN (Riskified): Let me walk you through our pricing model.\n\n"
        "MIKE JOHNSON (SearchCorp): We have some concerns about the cost.\n"
        "The current budget allocation is tight this quarter.\n\n"
        "SARAH CHEN (Riskified): I understand. Let me address the pricing concern.\n"
        "We can offer a phased approach to reduce upfront cost.\n\n"
        "MIKE JOHNSON (SearchCorp): That sounds reasonable. What about the POC?\n"
        "We need to validate the chargeback reduction value before committing.\n\n"
        "SARAH CHEN (Riskified): Absolutely. The POC timeline would be 4 weeks.\n"
        "We guarantee a 15% reduction in chargebacks during the trial.\n\n"
        "MIKE JOHNSON (SearchCorp): The guarantee is important but we have cost concerns.\n"
        "We might need to exclude the guarantee from the POC scope.\n"
    )
    t = Transcript(
        id="search-test-t1", account_id="search-test-acct",
        call_date="2026-02-15", raw_text=text, preprocessed_text=text,
        token_count=500, call_title="QBR", is_active=1,
        participants=json.dumps([
            {"name": "Sarah Chen", "role": "AE", "company": "Riskified"},
            {"name": "Mike Johnson", "role": "VP", "company": "SearchCorp"},
        ]),
    )
    session.add(t)
    session.flush()
    return {"account_id": "search-test-acct", "transcript_id": "search-test-t1"}


class TestSearchTranscript:

    def test_finds_keyword(self, transcript_with_content, mock_get_session):
        result = search_transcript("search-test-t1", "pricing")
        assert result["total_matches"] > 0
        assert any("pricing" in m["text"].lower() for m in result["matches"])

    def test_case_insensitive(self, transcript_with_content, mock_get_session):
        result = search_transcript("search-test-t1", "POC")
        assert result["total_matches"] > 0

    def test_returns_metadata(self, transcript_with_content, mock_get_session):
        result = search_transcript("search-test-t1", "pricing")
        assert result["call_title"] == "QBR"
        assert result["call_date"] == "2026-02-15"
        assert result["transcript_id"] == "search-test-t1"

    def test_no_matches(self, transcript_with_content, mock_get_session):
        result = search_transcript("search-test-t1", "kubernetes")
        assert result["total_matches"] == 0
        assert result["matches"] == []

    def test_invalid_transcript_id(self, mock_get_session):
        result = search_transcript("nonexistent", "anything")
        assert result is None

    def test_max_matches_cap(self, transcript_with_content, mock_get_session):
        """Matches capped at 10."""
        result = search_transcript("search-test-t1", "the")
        assert result["total_matches"] <= 10

    def test_multi_word_search(self, transcript_with_content, mock_get_session):
        result = search_transcript("search-test-t1", "chargeback reduction")
        assert result["total_matches"] > 0
