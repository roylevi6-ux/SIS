"""Tests for watchlist_service — watchlist CRUD, TAM matching, new-calls flag."""

from __future__ import annotations

import csv
import io
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

import pytest

from sis.db.models import (
    Account, WatchlistAccount, TamAccount, AnalysisRun, Transcript,
    DealAssessment,
)


def _uuid() -> str:
    return str(uuid.uuid4())


def _now(days_ago: int = 0) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat()


def _make_csv(rows: list[dict]) -> bytes:
    """Build a CSV bytes payload from a list of row dicts."""
    if not rows:
        return b"account_name\n"
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue().encode("utf-8")


@pytest.fixture
def watchlist_session(session, mock_get_session):
    """Ensure watchlist_service.get_session is patched to the test session.

    mock_get_session from conftest patches registered modules, but only if
    they are already imported. We force-import watchlist_service here and
    patch directly to guarantee coverage regardless of import order.
    """
    import sis.services.watchlist_service  # ensure module is imported

    @contextmanager
    def _test_get_session():
        yield session

    with patch("sis.services.watchlist_service.get_session", _test_get_session):
        yield session


@pytest.fixture
def two_accounts(watchlist_session):
    """Seed two accounts for watchlist tests."""
    acct_a_id = _uuid()
    acct_b_id = _uuid()
    acct_a = Account(id=acct_a_id, account_name="Acme Corp", deal_type="new_logo")
    acct_b = Account(id=acct_b_id, account_name="Beta Inc", deal_type="new_logo")
    watchlist_session.add_all([acct_a, acct_b])
    watchlist_session.flush()
    return {"acct_a_id": acct_a_id, "acct_b_id": acct_b_id}


# ── test_add_and_list ─────────────────────────────────────────────────


class TestAddAndList:
    def test_add_and_list(self, two_accounts, watchlist_session):
        from sis.services.watchlist_service import add_to_watchlist, list_watched_accounts

        acct_a_id = two_accounts["acct_a_id"]
        acct_b_id = two_accounts["acct_b_id"]

        added = add_to_watchlist(
            [acct_a_id, acct_b_id],
            sf_account_names={acct_a_id: "Acme Corporation", acct_b_id: "Beta Inc (SF)"},
        )
        assert len(added) == 2

        listed = list_watched_accounts()
        names = {a["account_name"] for a in listed}
        assert "Acme Corp" in names
        assert "Beta Inc" in names

        # SF names are stored correctly
        sf_names = {a["sf_account_name"] for a in listed}
        assert "Acme Corporation" in sf_names
        assert "Beta Inc (SF)" in sf_names

    def test_list_returns_enriched_fields(self, two_accounts, watchlist_session):
        from sis.services.watchlist_service import add_to_watchlist, list_watched_accounts

        add_to_watchlist([two_accounts["acct_a_id"]])
        listed = list_watched_accounts()
        assert len(listed) == 1
        entry = listed[0]

        assert "account_id" in entry
        assert "account_name" in entry
        assert "sf_account_name" in entry
        assert "has_new_calls" in entry
        assert "health_score" in entry
        assert "last_analyzed" in entry
        assert "transcript_count" in entry
        assert "added_at" in entry


# ── test_add_duplicate_idempotent ─────────────────────────────────────


class TestAddDuplicateIdempotent:
    def test_add_duplicate_idempotent(self, two_accounts, watchlist_session):
        from sis.services.watchlist_service import add_to_watchlist, list_watched_accounts

        acct_a_id = two_accounts["acct_a_id"]

        # Add once
        first = add_to_watchlist([acct_a_id])
        assert len(first) == 1

        # Add again — should be skipped, no error
        second = add_to_watchlist([acct_a_id])
        assert len(second) == 0

        # Still only one entry in watchlist
        listed = list_watched_accounts()
        assert len(listed) == 1


# ── test_remove ───────────────────────────────────────────────────────


class TestRemove:
    def test_remove(self, two_accounts, watchlist_session):
        from sis.services.watchlist_service import add_to_watchlist, remove_from_watchlist, list_watched_accounts

        acct_a_id = two_accounts["acct_a_id"]
        acct_b_id = two_accounts["acct_b_id"]

        add_to_watchlist([acct_a_id, acct_b_id])
        assert len(list_watched_accounts()) == 2

        removed = remove_from_watchlist(acct_a_id)
        assert removed is True

        remaining = list_watched_accounts()
        assert len(remaining) == 1
        assert remaining[0]["account_id"] == acct_b_id

    def test_remove_not_found_returns_false(self, watchlist_session):
        from sis.services.watchlist_service import remove_from_watchlist

        result = remove_from_watchlist(_uuid())
        assert result is False


# ── test_update_sf_name ───────────────────────────────────────────────


class TestUpdateSFName:
    def test_update_sf_name(self, two_accounts, watchlist_session):
        from sis.services.watchlist_service import add_to_watchlist, update_sf_name

        acct_a_id = two_accounts["acct_a_id"]
        add_to_watchlist([acct_a_id], sf_account_names={acct_a_id: "Old Name"})

        result = update_sf_name(acct_a_id, "New SF Name")
        assert result["sf_account_name"] == "New SF Name"

        # Verify persisted
        entry = watchlist_session.query(WatchlistAccount).filter_by(account_id=acct_a_id).first()
        assert entry.sf_account_name == "New SF Name"

    def test_update_sf_name_not_on_watchlist_raises(self, watchlist_session):
        from sis.services.watchlist_service import update_sf_name

        with pytest.raises(ValueError, match="not on the watchlist"):
            update_sf_name(_uuid(), "Some Name")


# ── test_add_all_accounts ─────────────────────────────────────────────


class TestAddAllAccounts:
    def test_add_all_accounts(self, two_accounts, watchlist_session):
        from sis.services.watchlist_service import add_all_accounts_to_watchlist, list_watched_accounts

        added = add_all_accounts_to_watchlist(added_by=None)
        assert len(added) == 2

        listed = list_watched_accounts()
        assert len(listed) == 2

    def test_add_all_accounts_idempotent(self, two_accounts, watchlist_session):
        from sis.services.watchlist_service import add_all_accounts_to_watchlist

        first = add_all_accounts_to_watchlist()
        assert len(first) == 2

        # Second call: all already on watchlist
        second = add_all_accounts_to_watchlist()
        assert len(second) == 0


# ── compute_new_calls tests ───────────────────────────────────────────


class TestComputeNewCallsFlag:
    def test_no_transcripts_returns_false(self, two_accounts, watchlist_session):
        from sis.services.watchlist_service import compute_new_calls_flag

        acct_a_id = two_accounts["acct_a_id"]
        result = compute_new_calls_flag(acct_a_id)
        assert result is False

        acct = watchlist_session.query(Account).filter_by(id=acct_a_id).first()
        assert acct.has_new_calls == 0

    def test_transcripts_no_analysis_returns_true(self, two_accounts, watchlist_session):
        from sis.services.watchlist_service import compute_new_calls_flag

        acct_a_id = two_accounts["acct_a_id"]

        # Add a transcript, no analysis run
        t = Transcript(
            id=_uuid(), account_id=acct_a_id, call_date="2026-01-01",
            raw_text="call text", is_active=1, created_at=_now(5),
        )
        watchlist_session.add(t)
        watchlist_session.flush()

        result = compute_new_calls_flag(acct_a_id)
        assert result is True

        acct = watchlist_session.query(Account).filter_by(id=acct_a_id).first()
        assert acct.has_new_calls == 1

    def test_newer_transcript_after_analysis_returns_true(self, two_accounts, watchlist_session):
        from sis.services.watchlist_service import compute_new_calls_flag

        acct_a_id = two_accounts["acct_a_id"]
        run_started = _now(3)  # analysis 3 days ago

        # Analysis run completed 3 days ago
        run = AnalysisRun(
            id=_uuid(), account_id=acct_a_id,
            started_at=run_started,
            completed_at=_now(3),
            status="completed",
        )
        watchlist_session.add(run)
        watchlist_session.flush()

        # Transcript uploaded 1 day ago (newer than the run)
        t = Transcript(
            id=_uuid(), account_id=acct_a_id, call_date="2026-01-05",
            raw_text="new call", is_active=1, created_at=_now(1),
        )
        watchlist_session.add(t)
        watchlist_session.flush()

        result = compute_new_calls_flag(acct_a_id)
        assert result is True

    def test_no_new_transcripts_after_analysis_returns_false(self, two_accounts, watchlist_session):
        from sis.services.watchlist_service import compute_new_calls_flag

        acct_a_id = two_accounts["acct_a_id"]

        # Transcript uploaded 5 days ago
        t = Transcript(
            id=_uuid(), account_id=acct_a_id, call_date="2026-01-01",
            raw_text="old call", is_active=1, created_at=_now(5),
        )
        watchlist_session.add(t)
        watchlist_session.flush()

        # Analysis run completed 3 days ago (more recent than transcript)
        run = AnalysisRun(
            id=_uuid(), account_id=acct_a_id,
            started_at=_now(3),
            completed_at=_now(3),
            status="completed",
        )
        watchlist_session.add(run)
        watchlist_session.flush()

        result = compute_new_calls_flag(acct_a_id)
        assert result is False

        acct = watchlist_session.query(Account).filter_by(id=acct_a_id).first()
        assert acct.has_new_calls == 0


# ── test_clear_flag ───────────────────────────────────────────────────


class TestClearFlag:
    def test_clear_flag(self, two_accounts, watchlist_session):
        from sis.services.watchlist_service import clear_new_calls_flag

        acct_a_id = two_accounts["acct_a_id"]

        # Set has_new_calls = 1 directly
        acct = watchlist_session.query(Account).filter_by(id=acct_a_id).first()
        acct.has_new_calls = 1
        watchlist_session.flush()

        # Clear it
        clear_new_calls_flag(acct_a_id)

        watchlist_session.expire(acct)
        acct = watchlist_session.query(Account).filter_by(id=acct_a_id).first()
        assert acct.has_new_calls == 0


# ── test_upload_tam_list ──────────────────────────────────────────────


class TestUploadTamList:
    def test_upload_tam_list(self, watchlist_session):
        from sis.services.watchlist_service import upload_tam_list

        csv_content = _make_csv([
            {"account_name": "Acme Corp", "account_owner": "Alice", "business_sub_region": "EMEA", "business_structure": "Enterprise"},
            {"account_name": "Beta Inc", "account_owner": "Bob", "business_sub_region": "NA", "business_structure": "Mid-Market"},
            {"account_name": "Gamma LLC", "account_owner": "Carol", "business_sub_region": "APAC", "business_structure": "SMB"},
        ])

        result = upload_tam_list(csv_content)
        assert result["count"] == 3

        entries = watchlist_session.query(TamAccount).all()
        assert len(entries) == 3
        names = {e.account_name for e in entries}
        assert "Acme Corp" in names

    def test_upload_tam_list_replaces_existing(self, watchlist_session):
        from sis.services.watchlist_service import upload_tam_list

        # First upload
        upload_tam_list(_make_csv([
            {"account_name": "Old Corp"},
            {"account_name": "Also Old"},
        ]))
        assert watchlist_session.query(TamAccount).count() == 2

        # Replace with new list
        result = upload_tam_list(_make_csv([{"account_name": "New Corp"}]))
        assert result["count"] == 1
        assert watchlist_session.query(TamAccount).count() == 1
        entry = watchlist_session.query(TamAccount).first()
        assert entry.account_name == "New Corp"


# ── test_suggest_sf_name_from_tam ─────────────────────────────────────


class TestSuggestSFNameFromTam:
    def _seed_tam(self, session, names: list[str]):
        for name in names:
            session.add(TamAccount(id=_uuid(), account_name=name))
        session.flush()

    def test_exact_match(self, watchlist_session):
        from sis.services.watchlist_service import suggest_sf_name_from_tam

        self._seed_tam(watchlist_session, ["Acme Corp", "Beta Inc", "Gamma LLC"])
        result = suggest_sf_name_from_tam("Acme Corp")
        assert result == "Acme Corp"

    def test_fuzzy_match_above_threshold(self, watchlist_session):
        from sis.services.watchlist_service import suggest_sf_name_from_tam

        self._seed_tam(watchlist_session, ["Acme Corporation", "Beta Industries"])
        # "Acme Corp" is close enough to "Acme Corporation"
        result = suggest_sf_name_from_tam("Acme Corp")
        assert result == "Acme Corporation"

    def test_no_match_below_threshold(self, watchlist_session):
        from sis.services.watchlist_service import suggest_sf_name_from_tam

        self._seed_tam(watchlist_session, ["Completely Different Name"])
        result = suggest_sf_name_from_tam("XYZ")
        assert result is None

    def test_empty_tam_returns_none(self, watchlist_session):
        from sis.services.watchlist_service import suggest_sf_name_from_tam

        # No TAM entries
        result = suggest_sf_name_from_tam("Anything")
        assert result is None


# ── test_import_watchlist_csv ─────────────────────────────────────────


class TestImportWatchlistCsv:
    def test_import_csv_matches_known_accounts(self, two_accounts, watchlist_session):
        from sis.services.watchlist_service import import_watchlist_csv

        csv_content = _make_csv([
            {"account_name": "Acme Corp"},
            {"account_name": "Beta Inc"},
        ])

        result = import_watchlist_csv(csv_content)
        assert len(result["matched"]) == 2
        assert len(result["unmatched"]) == 0

        matched_names = {m["account_name"] for m in result["matched"]}
        assert "Acme Corp" in matched_names
        assert "Beta Inc" in matched_names

    def test_import_csv_unmatched_names(self, two_accounts, watchlist_session):
        from sis.services.watchlist_service import import_watchlist_csv

        csv_content = _make_csv([
            {"account_name": "Totally Unknown Company XYZ 12345"},
        ])

        result = import_watchlist_csv(csv_content)
        assert len(result["matched"]) == 0
        assert len(result["unmatched"]) == 1
        assert "Totally Unknown Company XYZ 12345" in result["unmatched"]

    def test_import_csv_fuzzy_match(self, two_accounts, watchlist_session):
        from sis.services.watchlist_service import import_watchlist_csv

        # "Acme Corporation" should fuzzy-match to "Acme Corp"
        csv_content = _make_csv([
            {"account_name": "Acme Corporation"},
        ])

        result = import_watchlist_csv(csv_content)
        # Should match to "Acme Corp" via fuzzy
        assert len(result["matched"]) == 1
        assert result["matched"][0]["account_name"] == "Acme Corp"
        assert result["matched"][0]["sf_name"] == "Acme Corporation"

    def test_import_csv_bytes_input(self, two_accounts, watchlist_session):
        from sis.services.watchlist_service import import_watchlist_csv

        csv_bytes = b"account_name\nAcme Corp\n"
        result = import_watchlist_csv(csv_bytes)
        assert len(result["matched"]) == 1
