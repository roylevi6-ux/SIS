"""Tests for get_all_calls_with_status()."""

import json
import uuid
from pathlib import Path
from unittest.mock import patch

import pytest

from sis.services.gdrive_service import get_all_calls_with_status


def _write_call(tmp_path: Path, date: str, call_id: str, title: str) -> None:
    """Write a pair of metadata + transcript JSON files (nested layout)."""
    meta = {
        "metaData": {
            "id": call_id,
            "title": title,
            "date": date,
            "started": f"{date}T10:00:00Z",
            "duration": 1800,
            "language": "English",
            "direction": "Conference",
            "system": "Zoom",
            "scope": "External",
        },
        "parties": [],
        "content": {"trackers": [], "topics": []},
    }
    safe_title = title.replace(" ", "_")
    meta_file = tmp_path / f"gong_call_{date}_001_{safe_title}.json"
    meta_file.write_text(json.dumps(meta))
    transcript_file = tmp_path / f"gong_call_{date}_001_{safe_title}_transcript.json"
    transcript_file.write_text(json.dumps([]))


class TestGetAllCallsWithStatus:

    def test_all_new_when_no_db_account(self, tmp_path):
        _write_call(tmp_path, "2026-03-01", "call_1", "QBR")
        _write_call(tmp_path, "2026-02-15", "call_2", "Discovery")

        result = get_all_calls_with_status(str(tmp_path), db_account_id=None)

        assert len(result["calls"]) == 2
        assert all(c["status"] == "new" for c in result["calls"])
        assert result["calls"][0]["date"] == "2026-03-01"  # sorted desc

    def test_marks_active_and_imported(self, tmp_path):
        _write_call(tmp_path, "2026-03-01", "call_1", "QBR")
        _write_call(tmp_path, "2026-02-15", "call_2", "Discovery")
        _write_call(tmp_path, "2026-01-10", "call_3", "Kickoff")

        fake_account_id = str(uuid.uuid4())

        with patch("sis.services.transcript_service.get_transcripts_by_gong_ids") as mock_lookup:
            mock_lookup.return_value = {
                "call_2": {"is_active": True},
                "call_3": {"is_active": False},
            }
            result = get_all_calls_with_status(str(tmp_path), db_account_id=fake_account_id)

        assert result["calls"][0]["status"] == "new"       # call_1
        assert result["calls"][1]["status"] == "active"     # call_2
        assert result["calls"][2]["status"] == "imported"   # call_3

    def test_returns_gong_call_id(self, tmp_path):
        _write_call(tmp_path, "2026-03-01", "call_abc", "QBR")

        result = get_all_calls_with_status(str(tmp_path), db_account_id=None)
        assert result["calls"][0]["gong_call_id"] == "call_abc"

    def test_empty_folder(self, tmp_path):
        result = get_all_calls_with_status(str(tmp_path), db_account_id=None)
        assert result["calls"] == []

    def test_flat_layout(self, tmp_path):
        meta = {
            "metaData": {
                "id": "flat_1", "title": "Flat Call", "date": "2026-03-01",
                "started": "2026-03-01T10:00:00Z", "duration": 900,
                "language": "English", "direction": "Conference",
                "system": "Zoom", "scope": "External",
            },
            "parties": [], "content": {"trackers": [], "topics": []},
        }
        (tmp_path / "gong_call-Acme-2026-03-01-Flat_Call.json").write_text(json.dumps(meta))
        (tmp_path / "gong_call-Acme-2026-03-01-Flat_Call_transcript.json").write_text("[]")
        (tmp_path / "gong_call-Beta-2026-03-01-Other.json").write_text(json.dumps(meta))

        result = get_all_calls_with_status(str(tmp_path), db_account_id=None, account_name="Acme")
        assert len(result["calls"]) == 1
