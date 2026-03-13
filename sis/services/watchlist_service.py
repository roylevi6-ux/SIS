"""Watchlist service — manages the list of accounts being tracked for Gong sync."""

from __future__ import annotations

import csv
import io
import logging
from difflib import SequenceMatcher

from sis.db.session import get_session
from sis.db.models import (
    Account, WatchlistAccount, TamAccount, DealAssessment,
    Transcript, AnalysisRun,
)

logger = logging.getLogger(__name__)

# Fuzzy match threshold for TAM name suggestions and CSV imports
_FUZZY_THRESHOLD = 0.8


# ── Internal helpers ────────────────────────────────────────────────────


def _humanize_account_name(name: str) -> str:
    """Convert Gong Drive folder name to readable form.

    '_http___cex_io_cex_io_' → 'cex io cex io'
    'Ace_Money_Transfer'     → 'Ace Money Transfer'
    """
    import re
    # Strip leading/trailing underscores
    cleaned = name.strip("_")
    # Remove common URL prefixes embedded as underscores
    cleaned = re.sub(r'^https?_+', '', cleaned, flags=re.IGNORECASE)
    # Replace underscores with spaces, collapse multiple spaces
    cleaned = re.sub(r'_+', ' ', cleaned).strip()
    # Title-case if the result is all lowercase
    if cleaned == cleaned.lower():
        cleaned = cleaned.title()
    return cleaned


def _fuzzy_ratio(a: str, b: str) -> float:
    """Return SequenceMatcher ratio between two strings (case-insensitive)."""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def _decode_bytes(content: str | bytes) -> str:
    """Decode bytes to str using utf-8 with latin-1 fallback."""
    if isinstance(content, str):
        return content
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError:
        return content.decode("latin-1")


# ── Public API ──────────────────────────────────────────────────────────


def list_watched_accounts() -> list[dict]:
    """List all watched accounts with enriched data.

    Returns list of dicts with: account_id, account_name, sf_account_name,
    has_new_calls, health_score, last_analyzed, transcript_count, added_at.
    """
    with get_session() as session:
        watchlist = session.query(WatchlistAccount).all()
        result = []
        for entry in watchlist:
            account = session.query(Account).filter_by(id=entry.account_id).first()
            if not account:
                continue

            latest_assessment = (
                session.query(DealAssessment)
                .filter_by(account_id=entry.account_id)
                .order_by(DealAssessment.created_at.desc())
                .first()
            )

            transcript_count = (
                session.query(Transcript)
                .filter_by(account_id=entry.account_id, is_active=1)
                .count()
            )

            result.append({
                "account_id": entry.account_id,
                "account_name": account.account_name,
                "sf_account_name": entry.sf_account_name,
                "has_new_calls": bool(account.has_new_calls),
                "health_score": latest_assessment.health_score if latest_assessment else None,
                "last_analyzed": latest_assessment.created_at if latest_assessment else None,
                "transcript_count": transcript_count,
                "added_at": entry.added_at,
            })
        return result


def add_to_watchlist(
    account_ids: list[str],
    sf_account_names: dict[str, str] | None = None,
    added_by: str | None = None,
) -> list[dict]:
    """Add accounts to watchlist. Idempotent — skips already-watched.

    If sf_account_names not provided for an account, tries TAM fuzzy match,
    then falls back to account.account_name.
    Returns list of added watchlist entries.
    """
    added = []
    with get_session() as session:
        for acct_id in account_ids:
            # Skip if already on watchlist
            existing = (
                session.query(WatchlistAccount)
                .filter_by(account_id=acct_id)
                .first()
            )
            if existing:
                logger.debug("Account %s already on watchlist, skipping", acct_id)
                continue

            account = session.query(Account).filter_by(id=acct_id).first()
            if not account:
                logger.warning("Account not found: %s, skipping", acct_id)
                continue

            # Resolve SF account name
            if sf_account_names and acct_id in sf_account_names:
                sf_name = sf_account_names[acct_id]
            else:
                # Try TAM fuzzy match, fall back to humanized account name
                sf_name = suggest_sf_name_from_tam(account.account_name) or _humanize_account_name(account.account_name)

            entry = WatchlistAccount(
                account_id=acct_id,
                sf_account_name=sf_name,
                added_by=added_by,
            )
            session.add(entry)
            session.flush()
            added.append({
                "account_id": acct_id,
                "account_name": account.account_name,
                "sf_account_name": sf_name,
                "added_at": entry.added_at,
            })

    return added


def remove_from_watchlist(account_id: str) -> bool:
    """Remove account from watchlist. Returns True if found and removed."""
    with get_session() as session:
        entry = (
            session.query(WatchlistAccount)
            .filter_by(account_id=account_id)
            .first()
        )
        if not entry:
            return False
        session.delete(entry)
        return True


def update_sf_name(account_id: str, sf_account_name: str) -> dict:
    """Update the Salesforce name for a watched account."""
    with get_session() as session:
        entry = (
            session.query(WatchlistAccount)
            .filter_by(account_id=account_id)
            .first()
        )
        if not entry:
            raise ValueError(f"Account {account_id} is not on the watchlist")
        entry.sf_account_name = sf_account_name
        session.flush()
        return {
            "account_id": account_id,
            "sf_account_name": entry.sf_account_name,
        }


def add_all_accounts_to_watchlist(added_by: str | None = None) -> list[dict]:
    """Pre-seed watchlist with ALL current SIS accounts. Idempotent."""
    with get_session() as session:
        all_accounts = session.query(Account).all()
        account_ids = [a.id for a in all_accounts]

    return add_to_watchlist(account_ids, added_by=added_by)


def import_watchlist_csv(file_content: str | bytes) -> dict:
    """Parse CSV with columns: account_name (required).

    Fuzzy-match account_name against SIS accounts.
    Returns: {matched: [{account_id, account_name, sf_name}], unmatched: [str]}
    """
    text = _decode_bytes(file_content)
    reader = csv.DictReader(io.StringIO(text))

    matched = []
    unmatched = []

    with get_session() as session:
        all_accounts = session.query(Account).all()
        account_name_map = {a.account_name.lower(): a for a in all_accounts}
        account_names = list(account_name_map.keys())

        for row in reader:
            # Support both 'account_name' and 'Account Name' column headers
            raw_name = row.get("account_name") or row.get("Account Name") or row.get("Account name") or ""
            raw_name = raw_name.strip()
            if not raw_name:
                continue

            # Exact match first
            norm = raw_name.lower()
            if norm in account_name_map:
                acct = account_name_map[norm]
                matched.append({
                    "account_id": acct.id,
                    "account_name": acct.account_name,
                    "sf_name": raw_name,
                })
                continue

            # Fuzzy match
            best_ratio = 0.0
            best_acct = None
            for candidate_lower in account_names:
                ratio = _fuzzy_ratio(norm, candidate_lower)
                if ratio > best_ratio:
                    best_ratio = ratio
                    best_acct = account_name_map[candidate_lower]

            if best_ratio >= _FUZZY_THRESHOLD and best_acct:
                matched.append({
                    "account_id": best_acct.id,
                    "account_name": best_acct.account_name,
                    "sf_name": raw_name,
                })
            else:
                unmatched.append(raw_name)

    return {"matched": matched, "unmatched": unmatched}


def upload_tam_list(file_content: str | bytes) -> dict:
    """Upload/replace the TAM reference list. Returns {count: int}."""
    text = _decode_bytes(file_content)
    reader = csv.DictReader(io.StringIO(text))

    rows = list(reader)

    with get_session() as session:
        # Full replace — clear existing records
        session.query(TamAccount).delete()
        session.flush()

        count = 0
        seen_names: set[str] = set()
        for row in rows:
            # Support multiple common header variations
            name = (
                row.get("account_name")
                or row.get("Account Name")
                or row.get("Account name")
                or row.get("name")
                or row.get("Name")
                or ""
            ).strip()

            if not name or name.lower() in seen_names:
                continue
            seen_names.add(name.lower())

            entry = TamAccount(
                account_name=name,
                account_owner=(
                    row.get("account_owner")
                    or row.get("Account Owner")
                    or row.get("owner")
                    or None
                ),
                business_sub_region=(
                    row.get("business_sub_region")
                    or row.get("Business Sub Region")
                    or row.get("sub_region")
                    or None
                ),
                business_structure=(
                    row.get("business_structure")
                    or row.get("Business Structure")
                    or row.get("structure")
                    or None
                ),
            )
            session.add(entry)
            count += 1

        session.flush()

    return {"count": count}


def suggest_sf_name_from_tam(account_name: str) -> str | None:
    """Exact (case-insensitive) match of account name against TAM list.

    Returns the TAM name if found, None otherwise. No fuzzy matching —
    unmatched accounts should be presented to the user for manual selection.
    """
    humanized = _humanize_account_name(account_name)
    with get_session() as session:
        tam_accounts = session.query(TamAccount).all()
        if not tam_accounts:
            return None

        for tam in tam_accounts:
            if tam.account_name.lower() == account_name.lower():
                return tam.account_name
            if tam.account_name.lower() == humanized.lower():
                return tam.account_name
        return None


def suggest_closest_tam_match(account_name: str) -> dict | None:
    """Find the closest TAM match for an account name (for manual review).

    Returns {"suggestion": name, "score": float} or None if no TAM data.
    """
    humanized = _humanize_account_name(account_name)
    with get_session() as session:
        tam_accounts = session.query(TamAccount).all()
        if not tam_accounts:
            return None

        best_ratio = 0.0
        best_name = None

        for tam in tam_accounts:
            for candidate in [account_name, humanized]:
                ratio = _fuzzy_ratio(candidate, tam.account_name)
                if ratio > best_ratio:
                    best_ratio = ratio
                    best_name = tam.account_name

        if best_name:
            return {"suggestion": best_name, "score": round(best_ratio, 2)}
        return None


def get_sf_name_suggestions() -> list[dict]:
    """Return closest TAM suggestions for watchlist accounts without exact TAM matches.

    Returns list of {account_id, account_name, current_sf_name, suggestion, score}.
    Only includes accounts that don't have an exact TAM match.
    """
    with get_session() as session:
        watchlist = session.query(WatchlistAccount).all()
        tam_accounts = session.query(TamAccount).all()

        if not tam_accounts:
            return []

        # Build TAM lookup
        tam_names_lower = {t.account_name.lower(): t.account_name for t in tam_accounts}

        suggestions = []
        for entry in watchlist:
            # Skip accounts that already exactly match a TAM name
            if entry.sf_account_name.lower() in tam_names_lower:
                continue

            account = session.query(Account).filter_by(id=entry.account_id).first()
            if not account:
                continue

            # Find closest match
            humanized = _humanize_account_name(account.account_name)
            best_ratio = 0.0
            best_name = None

            for tam in tam_accounts:
                for candidate in [account.account_name, humanized, entry.sf_account_name]:
                    ratio = _fuzzy_ratio(candidate, tam.account_name)
                    if ratio > best_ratio:
                        best_ratio = ratio
                        best_name = tam.account_name

            suggestions.append({
                "account_id": entry.account_id,
                "account_name": account.account_name,
                "current_sf_name": entry.sf_account_name,
                "suggestion": best_name,
                "score": round(best_ratio, 2),
            })

        # Sort by score descending (best matches first)
        suggestions.sort(key=lambda x: x["score"], reverse=True)
        return suggestions


def compute_new_calls_flag(account_id: str) -> bool:
    """Compute whether account has new calls since last analysis.

    Logic:
    - Condition A: Account has transcripts but NO completed analysis → True
    - Condition B: Account has transcripts uploaded AFTER the latest completed analysis → True
    - Otherwise: False

    Also updates accounts.has_new_calls in the DB.
    """
    with get_session() as session:
        account = session.query(Account).filter_by(id=account_id).first()
        if not account:
            raise ValueError(f"Account not found: {account_id}")

        # Check for any active transcripts
        transcripts = (
            session.query(Transcript)
            .filter_by(account_id=account_id, is_active=1)
            .all()
        )

        if not transcripts:
            # No transcripts at all — no new calls
            account.has_new_calls = 0
            session.flush()
            return False

        # Get latest completed analysis run
        latest_run = (
            session.query(AnalysisRun)
            .filter_by(account_id=account_id, status="completed")
            .order_by(AnalysisRun.started_at.desc())
            .first()
        )

        if not latest_run:
            # Has transcripts but no completed analysis — new calls!
            account.has_new_calls = 1
            session.flush()
            return True

        # Condition B: any transcript created_at is AFTER the latest completed run
        run_started_at = latest_run.started_at
        has_newer = any(
            t.created_at > run_started_at
            for t in transcripts
        )

        flag_value = 1 if has_newer else 0
        account.has_new_calls = flag_value
        session.flush()
        return bool(flag_value)


def clear_new_calls_flag(account_id: str) -> None:
    """Set has_new_calls=0. Called after analysis completes."""
    with get_session() as session:
        account = session.query(Account).filter_by(id=account_id).first()
        if account:
            account.has_new_calls = 0
            session.flush()
        else:
            logger.warning("clear_new_calls_flag: account not found: %s", account_id)
