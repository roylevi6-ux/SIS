"""Google Drive service — local-mount access to Gong transcript folders.

Reads from the local Google Drive for Desktop sync directory.
Typical path: ~/Library/CloudStorage/GoogleDrive-<email>/My Drive/...

Flow:
1. User provides the local path to the root transcript folder (or it's in .env)
2. Service scans sub-folders to list accounts
3. Finds the 5 most recent calls per account (each call = 2 JSON files)
4. Parses via gong_parser and uploads to DB
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

# Regex to extract date from Gong filenames: gong_call_YYYY-MM-DD_...
_DATE_RE = re.compile(r"gong_call_(\d{4}-\d{2}-\d{2})_")


def validate_drive_path(path: str) -> tuple[bool, str]:
    """Validate that a path exists and looks like a Gong transcripts folder.

    Returns:
        (is_valid, message) tuple.
    """
    p = Path(path).expanduser()
    if not p.exists():
        return False, f"Path does not exist: {p}"
    if not p.is_dir():
        return False, f"Path is not a directory: {p}"

    # Check if it has sub-folders (accounts)
    try:
        sub_dirs = [d for d in p.iterdir() if d.is_dir() and not d.name.startswith(".")]
    except PermissionError:
        return False, (
            f"Permission denied reading {p}. "
            "On macOS, grant Full Disk Access to your terminal app: "
            "System Settings → Privacy & Security → Full Disk Access."
        )
    if not sub_dirs:
        return False, f"No account sub-folders found in: {p}"

    return True, f"Found {len(sub_dirs)} account folder(s)"


def list_account_folders(drive_path: str) -> list[dict]:
    """List all sub-folders (accounts) in the local Drive folder.

    Returns:
        List of dicts: [{"name": str, "path": str, "call_count": int}, ...]
        sorted alphabetically by name.
    """
    root = Path(drive_path).expanduser()
    if not root.exists():
        raise FileNotFoundError(f"Drive path not found: {root}")

    accounts = []
    try:
        entries = sorted(root.iterdir())
    except PermissionError:
        raise PermissionError(
            f"Permission denied reading {root}. "
            "On macOS, grant Full Disk Access to your terminal app: "
            "System Settings → Privacy & Security → Full Disk Access."
        )
    for d in entries:
        if not d.is_dir() or d.name.startswith("."):
            continue

        # Count metadata JSON files (non-transcript)
        json_files = list(d.glob("*.json"))
        meta_count = sum(1 for f in json_files if "_transcript" not in f.name)

        accounts.append({
            "name": d.name,
            "path": str(d),
            "call_count": meta_count,
        })

    return accounts


def get_recent_calls_info(
    account_path: str, max_calls: int = 5
) -> list[dict]:
    """Get info about the most recent calls in an account folder.

    Returns list of dicts with call metadata (name, date, file paths),
    sorted by date descending, limited to max_calls.
    """
    account_dir = Path(account_path)
    if not account_dir.exists():
        return []

    all_json = list(account_dir.glob("*.json"))
    meta_files = [f for f in all_json if "_transcript" not in f.name]
    transcript_files = {f.name: f for f in all_json if "_transcript" in f.name}

    calls = []
    for mf in meta_files:
        date_match = _DATE_RE.search(mf.name)
        call_date = date_match.group(1) if date_match else "0000-00-00"

        # Find companion transcript file
        stem = mf.stem
        transcript_name = f"{stem}_transcript.json"
        tf = transcript_files.get(transcript_name)

        # Clean up title from filename
        title = mf.name
        title_match = re.match(r"gong_call_\d{4}-\d{2}-\d{2}_\d+_(.*?)\.json$", title)
        if title_match:
            title = title_match.group(1).replace("_", " ")

        calls.append({
            "date": call_date,
            "title": title,
            "has_transcript": tf is not None,
            "meta_path": str(mf),
        })

    calls.sort(key=lambda c: c["date"], reverse=True)
    return calls[:max_calls]


def download_and_parse_calls(
    account_path: str, max_calls: int = 5
) -> list:
    """Parse the most recent calls from a local account folder.

    Uses gong_parser.load_account_calls() directly on the local directory,
    then returns only the N most recent.

    Returns:
        List of ParsedCall objects from gong_parser.
    """
    from sis.preprocessor.gong_parser import load_recent_calls

    return load_recent_calls(account_path, max_calls)


def upload_calls_to_db(
    parsed_calls: list,
    account_id: str,
) -> list:
    """Upload parsed calls to the database via transcript_service.

    Args:
        parsed_calls: List of ParsedCall objects from gong_parser
        account_id: SIS account ID to upload to

    Returns:
        List of created Transcript ORM objects.
    """
    from sis.services.transcript_service import upload_transcript

    results = []
    for call in parsed_calls:
        agent_text = call.to_agent_text()
        transcript = upload_transcript(
            account_id=account_id,
            raw_text=agent_text,
            call_date=call.metadata.date,
            participants=[
                {"name": s.name, "affiliation": s.affiliation, "title": s.title}
                for s in call.speakers
            ],
            duration_minutes=call.metadata.duration_minutes or None,
        )
        results.append(transcript)
        logger.info(
            "Uploaded call %s (%s) → transcript %s (%d tokens)",
            call.metadata.title[:40],
            call.metadata.date,
            transcript.id[:8],
            transcript.token_count,
        )

    return results
