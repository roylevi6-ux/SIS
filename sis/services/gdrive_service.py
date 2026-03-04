"""Google Drive service — local-mount access to Gong transcript folders.

Reads from the local Google Drive for Desktop sync directory.
Typical path: ~/Library/CloudStorage/GoogleDrive-<email>/My Drive/...

Supports two folder layouts:
  A) Nested: sub-folders per account, each containing call JSON files
  B) Flat: all call JSON files in one directory, account name in filename

Flow:
1. User provides the local path to the root transcript folder (or it's in .env)
2. Service scans sub-folders (or parses filenames) to list accounts
3. Finds the 5 most recent calls per account (each call = 2 JSON files)
4. Parses via gong_parser and uploads to DB
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

# Regex to extract date from Gong filenames.
# Supports both formats:
#   gong_call_YYYY-MM-DD_...           (underscore-separated)
#   gong_call-Account-YYYY-MM-DD-...   (hyphen-separated)
_DATE_RE = re.compile(r"gong_call[_-](?:.*?[_-])?(\d{4}-\d{2}-\d{2})[_-]")

# Regex to extract account name from flat-layout Gong filenames.
# Pattern: gong_call-{AccountName}-YYYY-MM-DD-...
_ACCOUNT_NAME_RE = re.compile(r"gong_call-(.+?)-\d{4}-\d{2}-\d{2}")


# ── Helpers ──────────────────────────────────────────────────────────


def _is_transcript(name: str) -> bool:
    """Check if a filename is a transcript file (vs. metadata).

    Handles Google Drive duplicate naming like '-transcript (1).json'.
    """
    return bool(re.search(r"[-_]transcript(\s*\(\d+\))?\.json$", name))


def _is_flat_layout(root: Path) -> bool:
    """Check if directory has flat gong_call files rather than account sub-folders."""
    has_subdirs = any(
        d.is_dir() and not d.name.startswith(".")
        for d in root.iterdir()
    )
    if has_subdirs:
        return False
    return any(f.name.startswith("gong_call") for f in root.glob("*.json"))


def _extract_account_name(filename: str) -> str | None:
    """Extract account name from a flat Gong filename."""
    m = _ACCOUNT_NAME_RE.match(filename)
    return m.group(1) if m else None


def _is_gdrive_duplicate(name: str) -> bool:
    """Check if filename is a Google Drive duplicate like 'file (1).json'."""
    return bool(re.search(r"\s+\(\d+\)\.json$", name))


def _get_meta_files(directory: Path, account_name: str | None = None) -> list[Path]:
    """Get metadata (non-transcript) JSON files, optionally filtered by account.

    Excludes transcript files and Google Drive duplicate files.
    """
    all_json = list(directory.glob("*.json"))
    meta = [
        f for f in all_json
        if not _is_transcript(f.name) and not _is_gdrive_duplicate(f.name)
    ]
    if account_name:
        target = account_name.lower()
        meta = [f for f in meta if (_extract_account_name(f.name) or "").lower() == target]
    return meta


def _group_by_account(meta_files: list[Path]) -> dict[str, list[Path]]:
    """Group metadata files by account name extracted from filenames.

    Uses lowercase normalization so 'Uphold' and 'uphold' merge into one group.
    """
    groups: dict[str, list[Path]] = {}
    for f in meta_files:
        account = _extract_account_name(f.name)
        if account:
            groups.setdefault(account.lower(), []).append(f)
    return groups


# ── Public API ───────────────────────────────────────────────────────


def validate_drive_path(path: str) -> tuple[bool, str]:
    """Validate that a path exists and looks like a Gong transcripts folder.

    Accepts either nested (sub-folders per account) or flat (all files at root
    with account names in filenames) layouts.

    Returns:
        (is_valid, message) tuple.
    """
    p = Path(path).expanduser()
    # resolve() follows symlinks (including Google Drive shortcuts)
    try:
        p = p.resolve(strict=True)
    except (OSError, FileNotFoundError):
        return False, f"Path does not exist: {p}"
    if not p.is_dir():
        return False, f"Path is not a directory: {p}"

    try:
        if _is_flat_layout(p):
            meta_files = _get_meta_files(p)
            accounts = _group_by_account(meta_files)
            if not accounts:
                return False, f"No Gong call files found in: {p}"
            total_calls = sum(len(v) for v in accounts.values())
            return True, f"Found {len(accounts)} account(s) ({total_calls} calls)"

        # Nested layout — check for sub-folders
        sub_dirs = [d for d in p.iterdir() if d.is_dir() and not d.name.startswith(".")]
        if not sub_dirs:
            return False, f"No account sub-folders or Gong call files found in: {p}"
        return True, f"Found {len(sub_dirs)} account folder(s)"

    except PermissionError:
        return False, (
            f"Permission denied reading {p}. "
            "On macOS, grant Full Disk Access to your terminal app: "
            "System Settings → Privacy & Security → Full Disk Access."
        )


def list_account_folders(drive_path: str) -> list[dict]:
    """List all accounts in the local Drive folder with DB status enrichment.

    Supports both nested (sub-folders) and flat (account name in filenames)
    layouts.

    Returns:
        List of dicts:
            [{"name", "path", "call_count", "new_count", "db_account_id",
              "has_active_analysis"}, ...]
        Sorted: accounts with new calls first, then alphabetically.
    """
    root = Path(drive_path).expanduser()
    try:
        root = root.resolve(strict=True)
    except (OSError, FileNotFoundError):
        raise FileNotFoundError(f"Drive path not found: {root}")

    try:
        if _is_flat_layout(root):
            accounts = _list_accounts_flat(root)
        else:
            accounts = _list_accounts_nested(root)
    except PermissionError:
        raise PermissionError(
            f"Permission denied reading {root}. "
            "On macOS, grant Full Disk Access to your terminal app: "
            "System Settings → Privacy & Security → Full Disk Access."
        )

    # Enrich with DB status (new_count, db_account_id, has_active_analysis)
    _enrich_accounts_with_db_status(accounts, root)

    # Sort: accounts with new calls first, then alphabetically
    accounts.sort(key=lambda a: (a["new_count"] == 0, a["name"].lower()))
    return accounts


def _enrich_accounts_with_db_status(accounts: list[dict], root: Path) -> None:
    """Mutate each account dict to add new_count, db_account_id, has_active_analysis.

    new_count only counts unimported calls that are NEWER than the oldest
    active (analyzed) call.  Older unimported calls are ignored — they don't
    represent fresh intelligence the user hasn't seen.

    For accounts not yet in the DB, all calls count as new.

    Degrades gracefully if the DB is unavailable — all enrichment fields fall
    back to safe defaults (new_count = call_count, no db link).
    """
    import json as _json

    # Apply defaults first so partial failures leave accounts in a valid state
    for acct in accounts:
        acct["new_count"] = acct["call_count"]
        acct["db_account_id"] = None
        acct["has_active_analysis"] = False

    try:
        from sis.services.account_service import list_accounts
        from sis.services.transcript_service import get_transcripts_by_gong_ids

        db_accounts = list_accounts()
        # Build a lowercase-name → db account dict for O(1) lookup
        db_by_name: dict[str, dict] = {
            a["account_name"].lower(): a for a in db_accounts
        }
    except Exception:
        logger.warning(
            "DB unavailable during list_account_folders enrichment — "
            "using defaults (new_count = call_count)"
        )
        return

    flat = _is_flat_layout(root)

    for acct in accounts:
        db_match = db_by_name.get(acct["name"].lower())
        if db_match is None:
            # Account not in DB — all calls are new
            continue

        acct["db_account_id"] = db_match["id"]
        acct["has_active_analysis"] = db_match.get("health_score") is not None

        # Collect gong_call_ids + dates from local metadata files
        try:
            if flat:
                meta_files = _get_meta_files(root, account_name=acct["name"])
            else:
                account_dir = Path(acct["path"])
                meta_files = _get_meta_files(account_dir)

            # gong_id → date extracted from filename
            call_dates: dict[str, str] = {}
            for mf in meta_files:
                try:
                    with open(mf) as fh:
                        data = _json.load(fh)
                    gong_id = str(data.get("metadata", {}).get("call_id", "")) or None
                    if gong_id:
                        date_match = _DATE_RE.search(mf.name)
                        call_dates[gong_id] = date_match.group(1) if date_match else "0000-00-00"
                except Exception:
                    logger.warning("Failed to read gong_call_id from %s", mf.name)

            if not call_dates:
                acct["new_count"] = 0
                continue

            db_lookup = get_transcripts_by_gong_ids(acct["db_account_id"], list(call_dates.keys()))
            imported_ids = set(db_lookup.keys())

            # Find the oldest active call date as the cutoff.
            # Only unimported calls newer than this cutoff count as "new".
            active_dates = [
                info["call_date"] for info in db_lookup.values()
                if info["is_active"] and info["call_date"]
            ]

            if active_dates:
                cutoff = min(active_dates)
                acct["new_count"] = sum(
                    1 for gid, date in call_dates.items()
                    if gid not in imported_ids and date > cutoff
                )
            else:
                # No active analysis yet — all unimported calls are new
                acct["new_count"] = sum(1 for gid in call_dates if gid not in imported_ids)

        except Exception:
            logger.warning(
                "Failed to compute new_count for account '%s' — defaulting to call_count",
                acct["name"],
            )


def _list_accounts_flat(root: Path) -> list[dict]:
    """List accounts from flat directory by parsing filenames."""
    meta_files = _get_meta_files(root)
    groups = _group_by_account(meta_files)

    accounts = []
    for name, files in sorted(groups.items()):
        accounts.append({
            "name": name,
            "path": str(root),
            "call_count": len(files),
        })
    return accounts


def _list_accounts_nested(root: Path) -> list[dict]:
    """List accounts from nested sub-folder structure."""
    accounts = []
    for d in sorted(root.iterdir()):
        if not d.is_dir() or d.name.startswith("."):
            continue

        json_files = list(d.glob("*.json"))
        meta_count = sum(1 for f in json_files if not _is_transcript(f.name))

        accounts.append({
            "name": d.name,
            "path": str(d),
            "call_count": meta_count,
        })
    return accounts


def get_recent_calls_info(
    account_path: str, max_calls: int = 5, account_name: str | None = None
) -> list[dict]:
    """Get info about the most recent calls for an account.

    For nested layout, account_path points to the account sub-folder.
    For flat layout, account_path is the root folder and account_name
    is used to filter files.

    Returns list of dicts with call metadata (name, date, file paths),
    sorted by date descending, limited to max_calls.
    """
    account_dir = Path(account_path)
    if not account_dir.exists():
        return []

    all_json = list(account_dir.glob("*.json"))

    # Filter by account name if provided (flat layout, case-insensitive)
    if account_name:
        target = account_name.lower()
        all_json = [
            f for f in all_json
            if (_extract_account_name(f.name) or "").lower() == target
            or (_extract_account_name(
                f.name.replace("-transcript.json", ".json").replace("_transcript.json", ".json")
            ) or "").lower() == target
        ]

    meta_files = [
        f for f in all_json
        if not _is_transcript(f.name) and not _is_gdrive_duplicate(f.name)
    ]
    transcript_names = {f.name for f in all_json if _is_transcript(f.name)}

    calls = []
    for mf in meta_files:
        date_match = _DATE_RE.search(mf.name)
        call_date = date_match.group(1) if date_match else "0000-00-00"

        # Find companion transcript file (try both hyphen and underscore conventions)
        stem = mf.stem
        has_transcript = any(
            t.startswith(f"{stem}-transcript") or t.startswith(f"{stem}_transcript")
            for t in transcript_names
        )

        # Clean up title from filename — handle both formats
        title = mf.name
        # Format: gong_call-Account-YYYY-MM-DD-Title.json  (hyphen-separated)
        title_match = re.match(
            r"gong_call-.+?-\d{4}-\d{2}-\d{2}-(.*?)\.json$", title
        )
        if not title_match:
            # Format: gong_call_YYYY-MM-DD_NNN_Title.json  (underscore-separated)
            title_match = re.match(
                r"gong_call_\d{4}-\d{2}-\d{2}_\d+_(.*?)\.json$", title
            )
        if title_match:
            title = title_match.group(1).replace("_", " ").replace("-", " ")

        calls.append({
            "date": call_date,
            "title": title,
            "has_transcript": has_transcript,
            "meta_path": str(mf),
        })

    calls.sort(key=lambda c: c["date"], reverse=True)
    return calls[:max_calls]


def get_all_calls_with_status(
    account_path: str,
    db_account_id: str | None,
    account_name: str | None = None,
) -> dict:
    """Get ALL calls for an account with their DB import status.

    Cross-references drive folder contents against the Transcript table.

    Args:
        account_path: Path to account folder (nested) or root folder (flat).
        db_account_id: SIS account UUID, or None if account not in DB.
        account_name: Required for flat layout to filter by account.

    Returns:
        {"calls": [{"date", "title", "gong_call_id", "has_transcript", "status"}, ...]}
        Status is "new", "active", or "imported". Sorted by date descending.
    """
    import json as _json

    account_dir = Path(account_path)
    if not account_dir.exists():
        return {"calls": []}

    all_json = list(account_dir.glob("*.json"))

    # Filter by account name if provided (flat layout, case-insensitive)
    if account_name:
        target = account_name.lower()
        all_json = [
            f for f in all_json
            if (_extract_account_name(f.name) or "").lower() == target
            or (_extract_account_name(
                f.name.replace("-transcript.json", ".json").replace("_transcript.json", ".json")
            ) or "").lower() == target
        ]

    meta_files = [
        f for f in all_json
        if not _is_transcript(f.name) and not _is_gdrive_duplicate(f.name)
    ]
    transcript_names = {f.name for f in all_json if _is_transcript(f.name)}

    # Build call list with gong_call_id from metadata JSON
    calls = []
    for mf in meta_files:
        date_match = _DATE_RE.search(mf.name)
        call_date = date_match.group(1) if date_match else "0000-00-00"

        # Read gong_call_id from metadata file
        gong_call_id = None
        try:
            with open(mf) as fh:
                meta_data = _json.load(fh)
            gong_call_id = str(meta_data.get("metadata", {}).get("call_id", "")) or None
        except Exception:
            logger.warning("Failed to read metadata from %s", mf.name)

        # Check for companion transcript file
        stem = mf.stem
        has_transcript = any(
            t.startswith(f"{stem}-transcript") or t.startswith(f"{stem}_transcript")
            for t in transcript_names
        )

        # Title extraction (same logic as get_recent_calls_info)
        title = mf.name
        title_match = re.match(r"gong_call-.+?-\d{4}-\d{2}-\d{2}-(.*?)\.json$", title)
        if not title_match:
            title_match = re.match(r"gong_call_\d{4}-\d{2}-\d{2}_\d+_(.*?)\.json$", title)
        if title_match:
            title = title_match.group(1).replace("_", " ").replace("-", " ")

        calls.append({
            "date": call_date,
            "title": title,
            "gong_call_id": gong_call_id,
            "has_transcript": has_transcript,
            "status": "new",
        })

    # Cross-reference with DB if account exists
    if db_account_id:
        gong_ids = [c["gong_call_id"] for c in calls if c["gong_call_id"]]
        if gong_ids:
            from sis.services.transcript_service import get_transcripts_by_gong_ids
            db_lookup = get_transcripts_by_gong_ids(db_account_id, gong_ids)
            for call in calls:
                if call["gong_call_id"] in db_lookup:
                    info = db_lookup[call["gong_call_id"]]
                    call["status"] = "active" if info["is_active"] else "imported"

    calls.sort(key=lambda c: c["date"], reverse=True)
    return {"calls": calls}


def download_and_parse_calls(
    account_path: str, max_calls: int = 5, account_name: str | None = None
) -> list:
    """Parse the most recent calls from a local folder.

    For nested layout, reads all files in account_path.
    For flat layout, filters files in account_path by account_name.

    Returns:
        List of ParsedCall objects from gong_parser.
    """
    if account_name:
        # Flat layout — filter files by account name, pass to parser
        from sis.preprocessor.gong_parser import load_calls_from_files

        root = Path(account_path)
        meta_files = _get_meta_files(root, account_name=account_name)
        all_calls = load_calls_from_files(meta_files)
        all_calls.sort(key=lambda c: c.metadata.date, reverse=True)
        return all_calls[:max_calls]
    else:
        # Nested layout — parser handles the whole directory
        from sis.preprocessor.gong_parser import load_recent_calls

        return load_recent_calls(account_path, max_calls)


def upload_calls_to_db(
    parsed_calls: list,
    account_id: str,
) -> dict:
    """Upload parsed calls to the database via transcript_service, with dedup.

    Args:
        parsed_calls: List of ParsedCall objects from gong_parser
        account_id: SIS account ID to upload to

    Returns:
        Dict with 'imported' (list of Transcript objects) and 'skipped' (list of call_ids).
    """
    from sis.services.transcript_service import upload_transcript, transcript_exists, normalize_active_transcripts

    imported = []
    skipped = []
    for call in parsed_calls:
        gong_call_id = call.metadata.call_id

        # Dedup: skip if this call was already imported for this account
        if gong_call_id and transcript_exists(account_id, gong_call_id):
            skipped.append(gong_call_id)
            logger.info(
                "Skipped duplicate call %s (%s) — already imported",
                call.metadata.title[:40],
                gong_call_id,
            )
            continue

        agent_text = call.to_agent_text()

        # Extract business topics via Haiku (falls back to Gong topics)
        from sis.preprocessor.topic_extractor import extract_business_topics
        ai_topics = extract_business_topics(agent_text, call_title=call.metadata.title)
        if ai_topics is None and call.enrichment.topics:
            # Fallback: use Gong's top 2 topics by duration
            ai_topics = sorted(call.enrichment.topics, key=lambda t: -t.get("duration", 0))[:2]

        transcript = upload_transcript(
            account_id=account_id,
            raw_text=agent_text,
            call_date=call.metadata.date,
            participants=[
                {"name": s.name, "affiliation": s.affiliation, "title": s.title}
                for s in call.speakers
            ],
            duration_minutes=call.metadata.duration_minutes or None,
            gong_call_id=gong_call_id,
            call_title=call.metadata.title or None,
            call_topics=ai_topics,
        )
        imported.append(transcript)
        logger.info(
            "Uploaded call %s (%s) → transcript %s (%d tokens)",
            call.metadata.title[:40],
            call.metadata.date,
            transcript.id[:8],
            transcript.token_count,
        )

    # After bulk import, normalize so the N most recent by date are active
    if imported:
        normalize_active_transcripts(account_id)

    return {"imported": imported, "skipped": skipped}
