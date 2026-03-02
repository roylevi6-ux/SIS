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
    """Group metadata files by account name extracted from filenames."""
    groups: dict[str, list[Path]] = {}
    for f in meta_files:
        account = _extract_account_name(f.name)
        if account:
            groups.setdefault(account, []).append(f)
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
    """List all accounts in the local Drive folder.

    Supports both nested (sub-folders) and flat (account name in filenames)
    layouts.

    Returns:
        List of dicts: [{"name": str, "path": str, "call_count": int}, ...]
        sorted alphabetically by name.
    """
    root = Path(drive_path).expanduser()
    try:
        root = root.resolve(strict=True)
    except (OSError, FileNotFoundError):
        raise FileNotFoundError(f"Drive path not found: {root}")

    try:
        if _is_flat_layout(root):
            return _list_accounts_flat(root)
        return _list_accounts_nested(root)
    except PermissionError:
        raise PermissionError(
            f"Permission denied reading {root}. "
            "On macOS, grant Full Disk Access to your terminal app: "
            "System Settings → Privacy & Security → Full Disk Access."
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

    # Filter by account name if provided (flat layout)
    if account_name:
        all_json = [
            f for f in all_json
            if _extract_account_name(f.name) == account_name
            or _extract_account_name(
                f.name.replace("-transcript.json", ".json").replace("_transcript.json", ".json")
            ) == account_name
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
