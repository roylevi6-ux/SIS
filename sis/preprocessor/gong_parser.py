"""Gong JSON parser — loads metadata + transcript pairs, maps speakers, normalizes output.

Handles the Gong export format:
  - Metadata file: {call_id}_{title}.json
  - Transcript file: {call_id}_{title}_transcript.json

Speaker mapping uses rank-order talk-time matching:
  1. Gong's speakers[] array has names + talkTime (only Gong-licensed users)
  2. Transcript speakerIds are anonymous numeric IDs
  3. We match by sorting both lists by talk time and pairing them in order
  4. Unmatched speakerIds are labeled from the participants list or as "Speaker N"
"""

from __future__ import annotations

import glob
import json
import logging
from pathlib import Path

from .models import (
    CallMetadata,
    GongEnrichment,
    ParsedCall,
    Speaker,
    TranscriptTurn,
)

logger = logging.getLogger(__name__)


def load_account_calls(account_dir: str | Path) -> list[ParsedCall]:
    """Load all Gong calls from an account directory, sorted by date.

    Expects paired files: metadata .json + _transcript.json
    """
    account_dir = Path(account_dir)
    if not account_dir.exists():
        raise FileNotFoundError(f"Account directory not found: {account_dir}")

    # Find all metadata files (those without _transcript suffix)
    all_json = sorted(account_dir.glob("*.json"))
    meta_files = [f for f in all_json if "_transcript" not in f.name]

    calls = []
    for mf in meta_files:
        try:
            parsed = parse_call(mf)
            calls.append(parsed)
        except Exception as e:
            logger.warning("Failed to parse %s: %s", mf.name, e)

    # Sort chronologically
    calls.sort(key=lambda c: c.metadata.date)
    return calls


def parse_call(metadata_path: str | Path) -> ParsedCall:
    """Parse a single Gong call from its metadata file.

    Automatically finds the companion transcript file.
    """
    metadata_path = Path(metadata_path)

    with open(metadata_path) as f:
        meta_json = json.load(f)

    # Find companion transcript file
    transcript_json = _load_transcript_file(metadata_path)

    # Parse metadata
    call_metadata = _parse_metadata(meta_json["metadata"])

    # Parse enrichment from Gong's content analysis
    enrichment = _parse_enrichment(meta_json.get("content", {}), meta_json.get("classifications", {}))

    # Parse raw participants for agent context
    participants_raw = meta_json.get("participants", [])

    # Map speakers
    gong_speakers = meta_json.get("speakers", [])
    transcript_turns_raw = transcript_json.get("transcript", []) if transcript_json else []

    speakers, turns = _map_speakers_and_build_turns(
        gong_speakers, transcript_turns_raw, participants_raw
    )

    return ParsedCall(
        metadata=call_metadata,
        speakers=speakers,
        turns=turns,
        enrichment=enrichment,
        participants_raw=participants_raw,
    )


def _load_transcript_file(metadata_path: Path) -> dict | None:
    """Find and load the companion transcript file for a metadata file."""
    # Pattern: base_name.json -> base_name_transcript.json
    stem = metadata_path.stem
    transcript_path = metadata_path.parent / f"{stem}_transcript.json"

    if transcript_path.exists():
        with open(transcript_path) as f:
            return json.load(f)

    # Try glob for fuzzy match (handles edge cases in naming)
    pattern = str(metadata_path.parent / f"*{metadata_path.stem.split('_', 3)[-1] if '_' in stem else stem}*_transcript.json")
    candidates = glob.glob(pattern)
    if candidates:
        with open(candidates[0]) as f:
            return json.load(f)

    logger.info("No transcript file found for %s", metadata_path.name)
    return None


def _parse_metadata(meta: dict) -> CallMetadata:
    """Extract CallMetadata from the metadata block."""
    return CallMetadata(
        call_id=str(meta.get("call_id", "")),
        title=meta.get("title", ""),
        date=meta.get("date", ""),
        started=meta.get("started", ""),
        duration_minutes=int(meta.get("duration_minutes", 0)),
        language=meta.get("language", "und"),
        direction=meta.get("direction", ""),
        system=meta.get("system", ""),
        scope=meta.get("scope", ""),
        call_url=meta.get("call_url", ""),
    )


def _parse_enrichment(content: dict, classifications: dict) -> GongEnrichment:
    """Extract Gong's own analysis as enrichment data."""
    return GongEnrichment(
        brief=content.get("brief", ""),
        key_points=[kp["text"] for kp in content.get("key_points", [])],
        topics=[{"name": t["name"], "duration": t.get("duration", 0)} for t in content.get("topics", [])],
        trackers=[
            {"name": t["name"], "count": t.get("count", 0), "type": t.get("type", "")}
            for t in content.get("trackers", [])
        ],
        classifications=classifications,
        call_outcome=content.get("call_outcome"),
    )


def _map_speakers_and_build_turns(
    gong_speakers: list[dict],
    transcript_turns: list[dict],
    participants: list[dict],
) -> tuple[list[Speaker], list[TranscriptTurn]]:
    """Core speaker mapping logic.

    Strategy:
    1. Calculate talk time per speakerId from transcript sentences
    2. Sort Gong speakers by talkTime descending (skip 0% speakers)
    3. Sort transcript speakerIds by talk time descending
    4. Match by rank order (highest-to-highest)
    5. For unmatched IDs, try to assign from external participants list
    """
    if not transcript_turns:
        # No transcript — build speakers from metadata only
        speakers = _speakers_from_participants(participants)
        return speakers, []

    # Step 1: Calculate talk time per speakerId
    speaker_talk_ms: dict[str, int] = {}
    for turn in transcript_turns:
        sid = turn["speakerId"]
        total_ms = sum(s["end"] - s["start"] for s in turn.get("sentences", []))
        speaker_talk_ms[sid] = speaker_talk_ms.get(sid, 0) + total_ms

    total_ms_all = sum(speaker_talk_ms.values()) or 1

    # Step 2: Sort both lists by talk time
    gong_ranked = sorted(
        [s for s in gong_speakers if s.get("talkTime", 0) > 0],
        key=lambda s: -s.get("talkTime", 0),
    )
    transcript_ranked = sorted(speaker_talk_ms.items(), key=lambda x: -x[1])

    # Step 3: Rank-order matching
    sid_to_speaker: dict[str, Speaker] = {}
    used_sids: set[str] = set()

    for gong_s in gong_ranked:
        # Find the best unmatched speakerId by rank
        for sid, ms in transcript_ranked:
            if sid in used_sids:
                continue
            # Match this Gong speaker to this speakerId
            participant_info = _find_participant(gong_s["name"], participants)
            sid_to_speaker[sid] = Speaker(
                id=sid,
                name=gong_s["name"],
                affiliation=participant_info.get("affiliation", "Internal"),
                title=participant_info.get("title", ""),
                email=participant_info.get("email", ""),
                talk_time_seconds=ms / 1000,
                talk_time_pct=ms * 100 / total_ms_all,
                is_mapped=True,
            )
            used_sids.add(sid)
            break

    # Step 4: Label unmatched speakerIds from external participants
    named_externals = [
        p for p in participants
        if p.get("affiliation") in ("External", "Unknown")
        and p.get("name")
        and not p["name"].startswith("Mk")
    ]

    ext_idx = 0
    speaker_num = 1
    for sid, ms in transcript_ranked:
        if sid in used_sids:
            continue

        if ext_idx < len(named_externals):
            p = named_externals[ext_idx]
            sid_to_speaker[sid] = Speaker(
                id=sid,
                name=p.get("name", f"Speaker {speaker_num}"),
                affiliation=p.get("affiliation", "Unknown"),
                title=p.get("title", ""),
                email=p.get("email", ""),
                talk_time_seconds=ms / 1000,
                talk_time_pct=ms * 100 / total_ms_all,
                is_mapped=False,
            )
            ext_idx += 1
        else:
            sid_to_speaker[sid] = Speaker(
                id=sid,
                name=f"Speaker {speaker_num}",
                affiliation="Unknown",
                talk_time_seconds=ms / 1000,
                talk_time_pct=ms * 100 / total_ms_all,
                is_mapped=False,
            )
        speaker_num += 1
        used_sids.add(sid)

    # Build speaker list (sorted by talk time)
    all_speakers = sorted(sid_to_speaker.values(), key=lambda s: -s.talk_time_seconds)

    # Step 5: Build transcript turns
    turns = []
    for turn in transcript_turns:
        sid = turn["speakerId"]
        speaker = sid_to_speaker.get(sid)
        if not speaker:
            continue

        # Merge all sentences in this turn into one text block
        sentences = turn.get("sentences", [])
        text = " ".join(s["text"] for s in sentences).strip()
        if not text:
            continue

        start_ms = sentences[0]["start"] if sentences else 0
        end_ms = sentences[-1]["end"] if sentences else 0

        turns.append(TranscriptTurn(
            speaker=speaker,
            text=text,
            start_ms=start_ms,
            end_ms=end_ms,
            topic=turn.get("topic"),
        ))

    return all_speakers, turns


def _find_participant(name: str, participants: list[dict]) -> dict:
    """Find a participant by name in the participants list."""
    name_lower = name.lower().strip()
    for p in participants:
        p_name = p.get("name", "").lower().strip()
        if p_name == name_lower:
            return p
        # Partial match (e.g., "Sherry.Yan" vs "Sherry Yan")
        if p_name.replace(".", " ") == name_lower.replace(".", " "):
            return p
    return {}


def _speakers_from_participants(participants: list[dict]) -> list[Speaker]:
    """Build speaker list from participants when no transcript exists."""
    speakers = []
    for p in participants:
        name = p.get("name", p.get("email", "Unknown"))
        if name.startswith("Mk"):  # Skip Gong placeholder names
            continue
        speakers.append(Speaker(
            id="",
            name=name,
            affiliation=p.get("affiliation", "Unknown"),
            title=p.get("title", ""),
            email=p.get("email", ""),
        ))
    return speakers
