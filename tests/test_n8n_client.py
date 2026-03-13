"""Tests for N8N/Okta webhook client.

Uses unittest.mock to patch httpx.AsyncClient rather than respx
(respx is not in the project's dependencies).

Key behaviour under test:
- 200 with valid Body.results → success=True with parsed counts
- 200 with zero calls → success=True (not an error)
- 200 with inner statusCode != 200 → success=False
- 503 → success=True (fire-and-verify pattern)
- 400/401/4xx → success=False
- httpx timeout → success=False, error="timed_out"
- Malformed JSON response → graceful failure (success=False)
- Missing fields in Body.results → defaults to 0 / empty string
"""

from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from sis.services.n8n_client import N8NExtractResponse, extract_gong_calls


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_response(status_code: int, json_body: dict | None = None, *, raises_json: bool = False) -> MagicMock:
    """Build a mock httpx.Response."""
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    if raises_json:
        resp.json.side_effect = Exception("not valid json")
    elif json_body is not None:
        resp.json.return_value = json_body
    else:
        resp.json.return_value = {}
    return resp


def _make_client_cm(response: MagicMock) -> MagicMock:
    """Build an AsyncMock context manager that yields a mock client posting the given response."""
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=response)

    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=mock_client)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm


FULL_200_BODY = {
    "Body": {
        "statusCode": 200,
        "results": {
            "totalCallsFound": 12,
            "callsProcessed": 10,
            "filesCreated": 20,
            "googleDriveFolder": "Nintendo/calls",
        },
    }
}


# ---------------------------------------------------------------------------
# 200 success cases
# ---------------------------------------------------------------------------


class TestSuccessful200Response:

    async def test_success_flag_is_true(self):
        with patch("httpx.AsyncClient", return_value=_make_client_cm(_mock_response(200, FULL_200_BODY))):
            result = await extract_gong_calls("Nintendo", "2025-01-01", "2026-03-13")
        assert result.success is True

    async def test_status_code_captured(self):
        with patch("httpx.AsyncClient", return_value=_make_client_cm(_mock_response(200, FULL_200_BODY))):
            result = await extract_gong_calls("Nintendo", "2025-01-01", "2026-03-13")
        assert result.status_code == 200

    async def test_total_calls_found_parsed(self):
        with patch("httpx.AsyncClient", return_value=_make_client_cm(_mock_response(200, FULL_200_BODY))):
            result = await extract_gong_calls("Nintendo", "2025-01-01", "2026-03-13")
        assert result.total_calls_found == 12

    async def test_calls_processed_parsed(self):
        with patch("httpx.AsyncClient", return_value=_make_client_cm(_mock_response(200, FULL_200_BODY))):
            result = await extract_gong_calls("Nintendo", "2025-01-01", "2026-03-13")
        assert result.calls_processed == 10

    async def test_files_created_parsed(self):
        with patch("httpx.AsyncClient", return_value=_make_client_cm(_mock_response(200, FULL_200_BODY))):
            result = await extract_gong_calls("Nintendo", "2025-01-01", "2026-03-13")
        assert result.files_created == 20

    async def test_google_drive_folder_parsed(self):
        with patch("httpx.AsyncClient", return_value=_make_client_cm(_mock_response(200, FULL_200_BODY))):
            result = await extract_gong_calls("Nintendo", "2025-01-01", "2026-03-13")
        assert result.google_drive_folder == "Nintendo/calls"

    async def test_no_error_on_success(self):
        with patch("httpx.AsyncClient", return_value=_make_client_cm(_mock_response(200, FULL_200_BODY))):
            result = await extract_gong_calls("Nintendo", "2025-01-01", "2026-03-13")
        assert result.error is None

    async def test_duration_is_non_negative(self):
        with patch("httpx.AsyncClient", return_value=_make_client_cm(_mock_response(200, FULL_200_BODY))):
            result = await extract_gong_calls("Nintendo", "2025-01-01", "2026-03-13")
        assert result.duration_seconds >= 0.0

    async def test_raw_response_stored(self):
        with patch("httpx.AsyncClient", return_value=_make_client_cm(_mock_response(200, FULL_200_BODY))):
            result = await extract_gong_calls("Nintendo", "2025-01-01", "2026-03-13")
        assert result.raw_response == FULL_200_BODY


# ---------------------------------------------------------------------------
# 200 with zero calls — still success, not an error
# ---------------------------------------------------------------------------


class TestZeroCallsResponse:
    ZERO_BODY = {
        "Body": {
            "statusCode": 200,
            "results": {
                "totalCallsFound": 0,
                "callsProcessed": 0,
                "filesCreated": 0,
                "googleDriveFolder": "",
            },
        }
    }

    async def test_zero_calls_is_success(self):
        with patch("httpx.AsyncClient", return_value=_make_client_cm(_mock_response(200, self.ZERO_BODY))):
            result = await extract_gong_calls("EmptyCo", "2025-01-01")
        assert result.success is True

    async def test_zero_calls_no_error(self):
        with patch("httpx.AsyncClient", return_value=_make_client_cm(_mock_response(200, self.ZERO_BODY))):
            result = await extract_gong_calls("EmptyCo", "2025-01-01")
        assert result.error is None

    async def test_zero_calls_counts_are_zero(self):
        with patch("httpx.AsyncClient", return_value=_make_client_cm(_mock_response(200, self.ZERO_BODY))):
            result = await extract_gong_calls("EmptyCo", "2025-01-01")
        assert result.total_calls_found == 0
        assert result.files_created == 0


# ---------------------------------------------------------------------------
# 503 — fire-and-verify: must be treated as success
# ---------------------------------------------------------------------------


class Test503FireAndVerify:

    async def test_503_is_success(self):
        with patch("httpx.AsyncClient", return_value=_make_client_cm(_mock_response(503))):
            result = await extract_gong_calls("Nintendo", "2025-01-01")
        assert result.success is True

    async def test_503_status_code_captured(self):
        with patch("httpx.AsyncClient", return_value=_make_client_cm(_mock_response(503))):
            result = await extract_gong_calls("Nintendo", "2025-01-01")
        assert result.status_code == 503

    async def test_503_no_error(self):
        with patch("httpx.AsyncClient", return_value=_make_client_cm(_mock_response(503))):
            result = await extract_gong_calls("Nintendo", "2025-01-01")
        assert result.error is None

    async def test_503_counts_default_to_zero(self):
        with patch("httpx.AsyncClient", return_value=_make_client_cm(_mock_response(503))):
            result = await extract_gong_calls("Nintendo", "2025-01-01")
        assert result.total_calls_found == 0
        assert result.files_created == 0


# ---------------------------------------------------------------------------
# 4xx error responses
# ---------------------------------------------------------------------------


class Test4xxErrors:

    async def test_400_is_failure(self):
        body = {"error": "Bad Request", "message": "Invalid accountName"}
        with patch("httpx.AsyncClient", return_value=_make_client_cm(_mock_response(400, body))):
            result = await extract_gong_calls("??Bad??", "2025-01-01")
        assert result.success is False

    async def test_400_status_code_captured(self):
        body = {"error": "Bad Request"}
        with patch("httpx.AsyncClient", return_value=_make_client_cm(_mock_response(400, body))):
            result = await extract_gong_calls("??Bad??", "2025-01-01")
        assert result.status_code == 400

    async def test_400_has_error_message(self):
        body = {"error": "Bad Request"}
        with patch("httpx.AsyncClient", return_value=_make_client_cm(_mock_response(400, body))):
            result = await extract_gong_calls("??Bad??", "2025-01-01")
        assert result.error is not None
        assert len(result.error) > 0

    async def test_401_is_failure(self):
        body = {"error": "Unauthorized"}
        with patch("httpx.AsyncClient", return_value=_make_client_cm(_mock_response(401, body))):
            result = await extract_gong_calls("Nintendo", "2025-01-01")
        assert result.success is False

    async def test_401_status_code_captured(self):
        body = {"error": "Unauthorized"}
        with patch("httpx.AsyncClient", return_value=_make_client_cm(_mock_response(401, body))):
            result = await extract_gong_calls("Nintendo", "2025-01-01")
        assert result.status_code == 401

    async def test_4xx_never_raises(self):
        """extract_gong_calls must never raise — even on unexpected status codes."""
        body = {"error": "Gone"}
        with patch("httpx.AsyncClient", return_value=_make_client_cm(_mock_response(410, body))):
            result = await extract_gong_calls("Nintendo", "2025-01-01")
        assert isinstance(result, N8NExtractResponse)
        assert result.success is False


# ---------------------------------------------------------------------------
# Timeout
# ---------------------------------------------------------------------------


class TestTimeout:

    async def _make_timeout_client(self) -> MagicMock:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=httpx.TimeoutException("Request timed out"))
        cm = MagicMock()
        cm.__aenter__ = AsyncMock(return_value=mock_client)
        cm.__aexit__ = AsyncMock(return_value=False)
        return cm

    async def test_timeout_is_failure(self):
        cm = await self._make_timeout_client()
        with patch("httpx.AsyncClient", return_value=cm):
            result = await extract_gong_calls("Nintendo", "2025-01-01")
        assert result.success is False

    async def test_timeout_error_is_timed_out(self):
        cm = await self._make_timeout_client()
        with patch("httpx.AsyncClient", return_value=cm):
            result = await extract_gong_calls("Nintendo", "2025-01-01")
        assert result.error == "timed_out"

    async def test_timeout_does_not_raise(self):
        cm = await self._make_timeout_client()
        with patch("httpx.AsyncClient", return_value=cm):
            result = await extract_gong_calls("Nintendo", "2025-01-01")
        assert isinstance(result, N8NExtractResponse)

    async def test_timeout_duration_is_non_negative(self):
        cm = await self._make_timeout_client()
        with patch("httpx.AsyncClient", return_value=cm):
            result = await extract_gong_calls("Nintendo", "2025-01-01")
        assert result.duration_seconds >= 0.0


# ---------------------------------------------------------------------------
# Malformed JSON response
# ---------------------------------------------------------------------------


class TestMalformedJSON:

    async def test_non_json_4xx_is_failure(self):
        """4xx with non-JSON body is still a failure."""
        with patch(
            "httpx.AsyncClient",
            return_value=_make_client_cm(_mock_response(500, raises_json=True)),
        ):
            result = await extract_gong_calls("Nintendo", "2025-01-01")
        assert result.success is False

    async def test_non_json_does_not_raise(self):
        with patch(
            "httpx.AsyncClient",
            return_value=_make_client_cm(_mock_response(500, raises_json=True)),
        ):
            result = await extract_gong_calls("Nintendo", "2025-01-01")
        assert isinstance(result, N8NExtractResponse)

    async def test_non_json_200_is_success(self):
        """200 with non-JSON body — optimistic success, no structured data."""
        with patch(
            "httpx.AsyncClient",
            return_value=_make_client_cm(_mock_response(200, raises_json=True)),
        ):
            result = await extract_gong_calls("Nintendo", "2025-01-01")
        assert result.success is True

    async def test_non_json_200_has_empty_raw_response(self):
        with patch(
            "httpx.AsyncClient",
            return_value=_make_client_cm(_mock_response(200, raises_json=True)),
        ):
            result = await extract_gong_calls("Nintendo", "2025-01-01")
        assert result.raw_response == {}


# ---------------------------------------------------------------------------
# Missing / partial fields in response body
# ---------------------------------------------------------------------------


class TestMissingFieldsInResponseBody:

    async def test_missing_results_key_defaults_to_zero(self):
        """Body without a results key should succeed with zero counts."""
        body = {"Body": {"statusCode": 200}}
        with patch("httpx.AsyncClient", return_value=_make_client_cm(_mock_response(200, body))):
            result = await extract_gong_calls("Nintendo", "2025-01-01")
        assert result.success is True
        assert result.total_calls_found == 0

    async def test_missing_body_wrapper_defaults_gracefully(self):
        """Response without the outer Body wrapper should still succeed with zero counts."""
        body = {}
        with patch("httpx.AsyncClient", return_value=_make_client_cm(_mock_response(200, body))):
            result = await extract_gong_calls("Nintendo", "2025-01-01")
        assert result.success is True
        assert result.total_calls_found == 0
        assert result.google_drive_folder == ""

    async def test_partial_results_fills_missing_with_defaults(self):
        """Partial results dict (only some keys present) — missing ones default to 0."""
        body = {
            "Body": {
                "statusCode": 200,
                "results": {"totalCallsFound": 5},  # callsProcessed / filesCreated missing
            }
        }
        with patch("httpx.AsyncClient", return_value=_make_client_cm(_mock_response(200, body))):
            result = await extract_gong_calls("Nintendo", "2025-01-01")
        assert result.success is True
        assert result.total_calls_found == 5
        assert result.calls_processed == 0
        assert result.files_created == 0

    async def test_inner_status_code_failure(self):
        """200 outer but inner statusCode != 200 → failure."""
        body = {
            "Body": {
                "statusCode": 500,
                "error": "Workflow internal error",
            }
        }
        with patch("httpx.AsyncClient", return_value=_make_client_cm(_mock_response(200, body))):
            result = await extract_gong_calls("Nintendo", "2025-01-01")
        assert result.success is False
        assert result.error is not None


# ---------------------------------------------------------------------------
# end_date defaulting
# ---------------------------------------------------------------------------


class TestEndDateDefault:

    async def test_end_date_defaults_to_today(self):
        """When end_date is omitted, today's ISO date should be sent to the webhook."""
        captured_payload = {}

        async def capture_post(url, *, json, headers):
            captured_payload.update(json)
            return _mock_response(503)

        mock_client = AsyncMock()
        mock_client.post = capture_post
        cm = MagicMock()
        cm.__aenter__ = AsyncMock(return_value=mock_client)
        cm.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=cm):
            await extract_gong_calls("Nintendo", "2025-01-01")

        assert captured_payload["endDate"] == date.today().isoformat()

    async def test_explicit_end_date_is_forwarded(self):
        """When end_date is provided, it must be forwarded as-is."""
        captured_payload = {}

        async def capture_post(url, *, json, headers):
            captured_payload.update(json)
            return _mock_response(503)

        mock_client = AsyncMock()
        mock_client.post = capture_post
        cm = MagicMock()
        cm.__aenter__ = AsyncMock(return_value=mock_client)
        cm.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=cm):
            await extract_gong_calls("Nintendo", "2025-01-01", "2026-06-30")

        assert captured_payload["endDate"] == "2026-06-30"

    async def test_account_name_forwarded_in_payload(self):
        """accountName must be forwarded verbatim."""
        captured_payload = {}

        async def capture_post(url, *, json, headers):
            captured_payload.update(json)
            return _mock_response(503)

        mock_client = AsyncMock()
        mock_client.post = capture_post
        cm = MagicMock()
        cm.__aenter__ = AsyncMock(return_value=mock_client)
        cm.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=cm):
            await extract_gong_calls("Riskified Inc", "2025-01-01")

        assert captured_payload["accountName"] == "Riskified Inc"


# ---------------------------------------------------------------------------
# Unexpected / generic exception
# ---------------------------------------------------------------------------


class TestGenericException:

    async def test_generic_exception_returns_failure(self):
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=RuntimeError("connection refused"))
        cm = MagicMock()
        cm.__aenter__ = AsyncMock(return_value=mock_client)
        cm.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=cm):
            result = await extract_gong_calls("Nintendo", "2025-01-01")

        assert result.success is False
        assert "connection refused" in result.error

    async def test_generic_exception_never_raises(self):
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=ValueError("unexpected"))
        cm = MagicMock()
        cm.__aenter__ = AsyncMock(return_value=mock_client)
        cm.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=cm):
            result = await extract_gong_calls("Nintendo", "2025-01-01")

        assert isinstance(result, N8NExtractResponse)
