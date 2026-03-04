"""Tests for Google Drive service — local filesystem approach."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from sis.services.gdrive_service import (
    validate_drive_path,
    list_account_folders,
    get_recent_calls_info,
)


@pytest.fixture
def mock_drive_folder(tmp_path: Path) -> Path:
    """Create a mock Google Drive folder structure with two accounts."""

    # Account 1: Acme Corp — 3 calls
    acme = tmp_path / "Acme Corp"
    acme.mkdir()
    for date, call_id, title in [
        ("2026-01-15", "111", "Acme_Kickoff"),
        ("2026-02-01", "222", "Acme_Followup"),
        ("2026-02-10", "333", "Acme_Review"),
    ]:
        _write_mock_call(acme, date, call_id, title)

    # Account 2: Beta Inc — 7 calls (to test 5-call limit)
    beta = tmp_path / "Beta Inc"
    beta.mkdir()
    for i, date in enumerate([
        "2025-10-01", "2025-11-15", "2025-12-20",
        "2026-01-05", "2026-01-20", "2026-02-01", "2026-02-15",
    ]):
        _write_mock_call(beta, date, str(400 + i), f"Beta_Call_{i}")

    return tmp_path


def _write_mock_call(account_dir: Path, date: str, call_id: str, title: str):
    """Write a minimal pair of Gong JSON files."""
    prefix = f"gong_call_{date}_{call_id}_{title}"

    # Metadata file
    meta = {
        "metadata": {
            "call_id": call_id,
            "title": title.replace("_", " "),
            "date": date,
            "started": f"{date}T10:00:00Z",
            "duration_minutes": 30,
            "language": "eng",
            "direction": "Conference",
            "system": "Zoom",
            "scope": "External",
        },
        "speakers": [],
        "participants": [
            {"name": "Alice", "affiliation": "Internal", "title": "AE"},
            {"name": "Bob", "affiliation": "External", "title": "VP Eng"},
        ],
        "content": {"brief": "Test call"},
        "classifications": {},
    }
    (account_dir / f"{prefix}.json").write_text(json.dumps(meta))

    # Transcript file
    transcript = {
        "transcript": [
            {
                "speakerId": "s1",
                "sentences": [
                    {"start": 0, "end": 5000, "text": "Hello, thanks for joining."},
                ],
            },
            {
                "speakerId": "s2",
                "sentences": [
                    {"start": 5000, "end": 12000, "text": "Thanks for having us."},
                ],
            },
        ]
    }
    (account_dir / f"{prefix}_transcript.json").write_text(json.dumps(transcript))


class TestValidateDrivePath:
    def test_valid_path(self, mock_drive_folder: Path):
        is_valid, msg = validate_drive_path(str(mock_drive_folder))
        assert is_valid
        assert "2 account folder" in msg

    def test_nonexistent_path(self, tmp_path: Path):
        is_valid, msg = validate_drive_path(str(tmp_path / "nonexistent"))
        assert not is_valid
        assert "does not exist" in msg

    def test_empty_directory(self, tmp_path: Path):
        empty = tmp_path / "empty"
        empty.mkdir()
        is_valid, msg = validate_drive_path(str(empty))
        assert not is_valid
        assert "No account sub-folders" in msg

    def test_file_not_directory(self, tmp_path: Path):
        f = tmp_path / "file.txt"
        f.write_text("hello")
        is_valid, msg = validate_drive_path(str(f))
        assert not is_valid
        assert "not a directory" in msg


@pytest.fixture(autouse=False)
def mock_list_accounts():
    """Patch list_accounts to return an empty list so tests don't need a live DB."""
    with patch(
        "sis.services.gdrive_service._enrich_accounts_with_db_status",
        lambda accounts, root: [
            acct.update(
                {"new_count": acct["call_count"], "db_account_id": None, "has_active_analysis": False}
            )
            for acct in accounts
        ],
    ):
        yield


class TestListAccountFolders:
    @pytest.fixture(autouse=True)
    def _patch_db(self, mock_list_accounts):
        """Apply the DB mock to every test in this class."""

    def test_lists_accounts(self, mock_drive_folder: Path):
        accounts = list_account_folders(str(mock_drive_folder))
        assert len(accounts) == 2
        names = [a["name"] for a in accounts]
        assert "Acme Corp" in names
        assert "Beta Inc" in names

    def test_call_counts(self, mock_drive_folder: Path):
        accounts = list_account_folders(str(mock_drive_folder))
        acme = next(a for a in accounts if a["name"] == "Acme Corp")
        beta = next(a for a in accounts if a["name"] == "Beta Inc")
        assert acme["call_count"] == 3
        assert beta["call_count"] == 7

    def test_sorted_alphabetically(self, mock_drive_folder: Path):
        accounts = list_account_folders(str(mock_drive_folder))
        assert accounts[0]["name"] == "Acme Corp"
        assert accounts[1]["name"] == "Beta Inc"

    def test_ignores_hidden_dirs(self, mock_drive_folder: Path):
        (mock_drive_folder / ".hidden").mkdir()
        accounts = list_account_folders(str(mock_drive_folder))
        assert len(accounts) == 2

    def test_nonexistent_raises(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            list_account_folders(str(tmp_path / "nope"))

    def test_enriched_fields_present(self, mock_drive_folder: Path):
        """Each account dict includes new_count, db_account_id, has_active_analysis."""
        accounts = list_account_folders(str(mock_drive_folder))
        for acct in accounts:
            assert "new_count" in acct
            assert "db_account_id" in acct
            assert "has_active_analysis" in acct


class TestGetRecentCallsInfo:
    def test_returns_recent_calls(self, mock_drive_folder: Path):
        acme = mock_drive_folder / "Acme Corp"
        calls = get_recent_calls_info(str(acme), max_calls=5)
        assert len(calls) == 3
        # Most recent first
        assert calls[0]["date"] == "2026-02-10"
        assert calls[1]["date"] == "2026-02-01"
        assert calls[2]["date"] == "2026-01-15"

    def test_limits_to_max_calls(self, mock_drive_folder: Path):
        beta = mock_drive_folder / "Beta Inc"
        calls = get_recent_calls_info(str(beta), max_calls=5)
        assert len(calls) == 5
        # Should be the 5 most recent
        assert calls[0]["date"] == "2026-02-15"
        assert calls[4]["date"] == "2025-12-20"

    def test_has_transcript_flag(self, mock_drive_folder: Path):
        acme = mock_drive_folder / "Acme Corp"
        calls = get_recent_calls_info(str(acme))
        assert all(c["has_transcript"] for c in calls)

    def test_missing_transcript(self, tmp_path: Path):
        account = tmp_path / "NoTranscript"
        account.mkdir()
        meta = {
            "metadata": {"call_id": "1", "title": "Test", "date": "2026-01-01",
                         "started": "", "duration_minutes": 30, "language": "eng",
                         "direction": "", "system": "", "scope": ""},
        }
        (account / "gong_call_2026-01-01_1_Test.json").write_text(json.dumps(meta))
        calls = get_recent_calls_info(str(account))
        assert len(calls) == 1
        assert not calls[0]["has_transcript"]

    def test_empty_folder(self, tmp_path: Path):
        empty = tmp_path / "Empty"
        empty.mkdir()
        calls = get_recent_calls_info(str(empty))
        assert calls == []

    def test_nonexistent_folder(self, tmp_path: Path):
        calls = get_recent_calls_info(str(tmp_path / "nope"))
        assert calls == []

    def test_title_extraction(self, mock_drive_folder: Path):
        acme = mock_drive_folder / "Acme Corp"
        calls = get_recent_calls_info(str(acme))
        # Titles should have underscores replaced with spaces
        assert calls[0]["title"] == "Acme Review"
