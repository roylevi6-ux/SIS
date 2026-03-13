"""N8N/Okta webhook client for Gong call extraction.

Fire-and-verify pattern: we trigger extraction via webhook, then verify
results by scanning the Google Drive folder (handled by sync_orchestrator).
The webhook commonly returns 503 but files still land — this is expected.

Usage:
    from sis.services.n8n_client import extract_gong_calls

    response = await extract_gong_calls(
        account_name="Nintendo",
        start_date="2025-01-01",
    )
    if response.success:
        # Files are landing in Drive; poll Drive to verify
        ...
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import date

import httpx

from sis.config import N8N_WEBHOOK_URL, N8N_REQUEST_TIMEOUT

logger = logging.getLogger(__name__)


@dataclass
class N8NExtractResponse:
    """Result of a single N8N webhook call.

    success=True does NOT mean all files are ready — Drive polling
    (sync_orchestrator) is the authoritative verification step.
    """

    success: bool
    total_calls_found: int = 0
    calls_processed: int = 0
    files_created: int = 0
    google_drive_folder: str = ""
    raw_response: dict = field(default_factory=dict)
    error: str | None = None
    duration_seconds: float = 0.0
    status_code: int | None = None


async def extract_gong_calls(
    account_name: str,
    start_date: str,
    end_date: str | None = None,
) -> N8NExtractResponse:
    """Trigger Gong call extraction via N8N/Okta webhook.

    Always returns N8NExtractResponse — never raises.

    503 is treated as success (fire-and-verify pattern): the Okta workflow
    gateway times out after ~31 seconds but continues processing, and files
    land in Google Drive regardless.

    Args:
        account_name: Exact account name as used in Google Drive folder names.
        start_date:   ISO date string, e.g. "2025-01-01".
        end_date:     ISO date string; defaults to today if not provided.

    Returns:
        N8NExtractResponse with success=True when 200 (with statusCode=200)
        or 503. success=False for 4xx, timeouts, and unexpected exceptions.
    """
    resolved_end_date = end_date or date.today().isoformat()

    payload = {
        "accountName": account_name,
        "startDate": start_date,
        "endDate": resolved_end_date,
    }

    logger.info(
        "N8N extract starting: account=%r start=%s end=%s url=%s",
        account_name,
        start_date,
        resolved_end_date,
        N8N_WEBHOOK_URL,
    )

    started = time.monotonic()

    try:
        async with httpx.AsyncClient(timeout=N8N_REQUEST_TIMEOUT) as client:
            http_response = await client.post(
                N8N_WEBHOOK_URL,
                json=payload,
                headers={"Content-Type": "application/json"},
            )

        duration = time.monotonic() - started
        status_code = http_response.status_code

        # --- 503: fire-and-verify success -----------------------------------
        # The Okta gateway consistently times out at ~31s but the workflow
        # continues running and deposits files in Drive.
        if status_code == 503:
            logger.info(
                "N8N returned 503 (expected timeout) for %r — treating as success. "
                "Verify via Drive scan. duration=%.1fs",
                account_name,
                duration,
            )
            return N8NExtractResponse(
                success=True,
                status_code=status_code,
                duration_seconds=duration,
                error=None,
            )

        # --- Try to parse JSON body -----------------------------------------
        body: dict = {}
        try:
            body = http_response.json()
        except Exception:
            logger.warning(
                "N8N response for %r was not valid JSON (status=%d)",
                account_name,
                status_code,
            )
            # Non-parseable body — treat as failure unless 2xx without JSON
            if not (200 <= status_code < 300):
                return N8NExtractResponse(
                    success=False,
                    status_code=status_code,
                    duration_seconds=duration,
                    error=f"non_json_response_status_{status_code}",
                    raw_response={},
                )
            # 2xx with non-JSON: optimistic success but no structured data
            return N8NExtractResponse(
                success=True,
                status_code=status_code,
                duration_seconds=duration,
                raw_response={},
            )

        # --- 200: parse structured results ----------------------------------
        if status_code == 200:
            return _parse_200_response(body, duration, status_code, account_name)

        # --- 4xx and other errors -------------------------------------------
        error_msg = _extract_error_message(body) or f"http_{status_code}"
        logger.warning(
            "N8N returned %d for %r: %s (duration=%.1fs)",
            status_code,
            account_name,
            error_msg,
            duration,
        )
        return N8NExtractResponse(
            success=False,
            status_code=status_code,
            duration_seconds=duration,
            error=error_msg,
            raw_response=body,
        )

    except httpx.TimeoutException:
        duration = time.monotonic() - started
        logger.warning(
            "N8N request timed out for %r after %.1fs (timeout=%ds)",
            account_name,
            duration,
            N8N_REQUEST_TIMEOUT,
        )
        return N8NExtractResponse(
            success=False,
            duration_seconds=duration,
            error="timed_out",
        )

    except Exception as exc:
        duration = time.monotonic() - started
        logger.warning(
            "N8N unexpected error for %r after %.1fs: %s",
            account_name,
            duration,
            exc,
        )
        return N8NExtractResponse(
            success=False,
            duration_seconds=duration,
            error=str(exc),
        )


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _parse_200_response(
    body: dict,
    duration: float,
    status_code: int,
    account_name: str,
) -> N8NExtractResponse:
    """Parse a successful 200 response from N8N.

    Expected shape:
        {"Body": {"statusCode": 200, "results": {...}}}

    Handles missing keys gracefully.
    """
    inner_body = body.get("Body", {}) if isinstance(body, dict) else {}
    inner_status = inner_body.get("statusCode") if isinstance(inner_body, dict) else None
    results = inner_body.get("results", {}) if isinstance(inner_body, dict) else {}

    if not isinstance(results, dict):
        results = {}

    # Inner statusCode mismatch → failure
    if inner_status is not None and inner_status != 200:
        error_msg = (
            inner_body.get("error")
            or inner_body.get("message")
            or f"inner_status_{inner_status}"
        )
        logger.warning(
            "N8N 200 outer but inner statusCode=%s for %r: %s",
            inner_status,
            account_name,
            error_msg,
        )
        return N8NExtractResponse(
            success=False,
            status_code=status_code,
            duration_seconds=duration,
            error=str(error_msg),
            raw_response=body,
        )

    total_calls_found = int(results.get("totalCallsFound", 0) or 0)
    calls_processed = int(results.get("callsProcessed", 0) or 0)
    files_created = int(results.get("filesCreated", 0) or 0)
    google_drive_folder = str(results.get("googleDriveFolder", "") or "")

    logger.info(
        "N8N success for %r: total_calls=%d processed=%d files=%d folder=%r duration=%.1fs",
        account_name,
        total_calls_found,
        calls_processed,
        files_created,
        google_drive_folder,
        duration,
    )

    return N8NExtractResponse(
        success=True,
        total_calls_found=total_calls_found,
        calls_processed=calls_processed,
        files_created=files_created,
        google_drive_folder=google_drive_folder,
        raw_response=body,
        duration_seconds=duration,
        status_code=status_code,
    )


def _extract_error_message(body: dict) -> str | None:
    """Pull a human-readable error string from a response body dict."""
    if not isinstance(body, dict):
        return None
    for key in ("error", "message", "detail", "msg"):
        val = body.get(key)
        if val:
            return str(val)
    return None
