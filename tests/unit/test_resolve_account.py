"""Tests for fuzzy account name resolution."""
from __future__ import annotations

import pytest
from sis.db.models import Account
from sis.services.account_service import resolve_account_by_name


class TestResolveAccountByName:

    def test_exact_match(self, seeded_db, mock_get_session):
        result = resolve_account_by_name("HealthyCorp")
        assert result is not None
        assert result["account_name"] == "HealthyCorp"

    def test_case_insensitive(self, seeded_db, mock_get_session):
        result = resolve_account_by_name("healthycorp")
        assert result is not None
        assert result["account_name"] == "HealthyCorp"

    def test_underscore_to_space(self, seeded_db, mock_get_session):
        """The original bug: users type spaces, DB has underscores."""
        mock_get_session.add(Account(
            id="underscore-test", account_name="Rakuten_Ichiba",
            cp_estimate=70000, deal_type="new_logo",
        ))
        mock_get_session.flush()

        result = resolve_account_by_name("Rakuten Ichiba")
        assert result is not None
        assert result["account_name"] == "Rakuten_Ichiba"

    def test_partial_match(self, seeded_db, mock_get_session):
        result = resolve_account_by_name("Healthy")
        assert result is not None
        assert result["account_name"] == "HealthyCorp"

    def test_no_match_returns_none(self, seeded_db, mock_get_session):
        result = resolve_account_by_name("NonExistentDeal")
        assert result is None

    def test_multi_word_match(self, seeded_db, mock_get_session):
        mock_get_session.add(Account(
            id="multi-word-test", account_name="We_Love_Holidays",
            cp_estimate=30000, deal_type="new_logo",
        ))
        mock_get_session.flush()

        result = resolve_account_by_name("love holidays")
        assert result is not None
        assert result["account_name"] == "We_Love_Holidays"

    def test_prefers_longest_match(self, seeded_db, mock_get_session):
        result = resolve_account_by_name("AtRiskCo")
        assert result is not None
        assert result["account_name"] == "AtRiskCo"

    def test_visible_user_ids_scoping(self, seeded_db, mock_get_session):
        """Respects role-based scoping."""
        ae1_id = seeded_db["user_ids"]["ae1"]
        result = resolve_account_by_name("CriticalInc", visible_user_ids={ae1_id})
        assert result is None
