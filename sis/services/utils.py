"""Shared service utilities."""

from __future__ import annotations

import json


def safe_json(val, default=None):
    """Parse a JSON string safely, returning default on failure.

    Used by export and scorecard services for DB columns that store
    JSON strings (e.g., health_breakdown, top_risks).
    """
    if default is None:
        default = []
    if not val:
        return default
    try:
        return json.loads(val)
    except (json.JSONDecodeError, TypeError):
        return default
