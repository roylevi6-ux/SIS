"""Data models for parsed Gong call transcripts."""

from __future__ import annotations

import re
from dataclasses import dataclass, field


# CJK / non-Latin character ranges that consume ~2-3 BPE tokens per character
_CJK_RE = re.compile(
    r"[\u3000-\u303f"  # CJK Symbols and Punctuation
    r"\u3040-\u309f"   # Hiragana
    r"\u30a0-\u30ff"   # Katakana
    r"\u3400-\u4dbf"   # CJK Extension A
    r"\u4e00-\u9fff"   # CJK Unified Ideographs
    r"\uf900-\ufaff"   # CJK Compatibility Ideographs
    r"\uff00-\uffef"   # Fullwidth Forms
    r"\uac00-\ud7af"   # Korean Hangul
    r"\u0590-\u05ff"   # Hebrew
    r"\u0600-\u06ff"   # Arabic
    r"]"
)


def estimate_tokens(text: str) -> int:
    """Estimate token count with CJK / non-Latin awareness.

    English text: ~1 token per 4 characters.
    CJK (Chinese, Japanese, Korean) + Hebrew + Arabic: ~2.5 tokens per character.
    """
    cjk_chars = len(_CJK_RE.findall(text))
    latin_chars = len(text) - cjk_chars
    return int(cjk_chars * 2.5 + latin_chars * 0.25)


@dataclass
class Speaker:
    """A resolved speaker in a call."""

    id: str
    name: str
    affiliation: str  # "Internal", "External", "Unknown"
    title: str = ""
    email: str = ""
    talk_time_seconds: float = 0.0
    talk_time_pct: float = 0.0
    is_mapped: bool = False  # True if confidently mapped from Gong speakers array


@dataclass
class TranscriptTurn:
    """A single speaker turn in the transcript."""

    speaker: Speaker
    text: str
    start_ms: int = 0
    end_ms: int = 0
    topic: str | None = None


@dataclass
class GongEnrichment:
    """Supplementary intelligence from Gong's own analysis."""

    brief: str = ""
    key_points: list[str] = field(default_factory=list)
    topics: list[dict] = field(default_factory=list)  # [{"name": str, "duration": int}]
    trackers: list[dict] = field(default_factory=list)  # [{"name": str, "count": int, "type": str}]
    classifications: dict[str, bool] = field(default_factory=dict)
    call_outcome: str | None = None


@dataclass
class CallMetadata:
    """Metadata about a single call."""

    call_id: str
    title: str
    date: str  # YYYY-MM-DD
    started: str  # ISO timestamp
    duration_minutes: int
    language: str  # Gong language code: "eng", "chi", "jpn", "fre", "spa", "heb", "und"
    direction: str  # "Conference", "Inbound", "Outbound"
    system: str  # "Zoom", "Teams", etc.
    scope: str  # "External", "Internal"
    call_url: str = ""


@dataclass
class ParsedCall:
    """A fully parsed and speaker-mapped Gong call, ready for agents."""

    metadata: CallMetadata
    speakers: list[Speaker]
    turns: list[TranscriptTurn]
    enrichment: GongEnrichment
    participants_raw: list[dict] = field(default_factory=list)  # Original participant list for agent context

    @property
    def has_transcript(self) -> bool:
        return len(self.turns) > 0

    @property
    def internal_speakers(self) -> list[Speaker]:
        return [s for s in self.speakers if s.affiliation == "Internal"]

    @property
    def external_speakers(self) -> list[Speaker]:
        return [s for s in self.speakers if s.affiliation != "Internal"]

    def to_agent_text(self, max_tokens: int = 0) -> str:
        """Format the call as text ready for agent consumption.

        Returns a header block with metadata + participant context + Gong enrichment,
        followed by the transcript body with speaker labels.
        """
        lines = []

        # Header
        lines.append(f"CALL: {self.metadata.title}")
        lines.append(f"DATE: {self.metadata.date} | DURATION: {self.metadata.duration_minutes} min | LANGUAGE: {self.metadata.language}")
        lines.append(f"TYPE: {_classify_call(self.enrichment.classifications)}")
        lines.append("")

        # Transcript speakers (those who spoke)
        lines.append("SPEAKERS (identified in transcript):")
        for s in self.speakers:
            role = f" — {s.title}" if s.title else ""
            tag = f" [{s.affiliation}]"
            conf = " [confirmed]" if s.is_mapped else " [voice-matched, may be inaccurate]"
            lines.append(f"  {s.name}{role}{tag}{conf} ({s.talk_time_pct:.0f}% talk time)")
        lines.append("")

        # Full participant list from Gong (includes attendees who may not be individually identified in transcript)
        non_speaker_participants = self._get_non_speaker_participants()
        if non_speaker_participants:
            lines.append("OTHER ATTENDEES (present but not individually identified in transcript):")
            for p in non_speaker_participants:
                name = p.get("name", p.get("email", "Unknown"))
                title = f" — {p['title']}" if p.get("title") else ""
                aff = f" [{p.get('affiliation', 'Unknown')}]"
                lines.append(f"  {name}{title}{aff}")
            lines.append("")

        # Speaker attribution confidence note
        unmapped_with_talk = [s for s in self.speakers if not s.is_mapped and s.talk_time_pct > 5]
        if unmapped_with_talk:
            names = ", ".join(s.name for s in unmapped_with_talk)
            lines.append(f"NOTE: Speaker attribution for {names} is inferred from talk-time matching and may be inaccurate. Cross-reference with dialogue context.")
            lines.append("")

        # Gong enrichment
        if self.enrichment.brief:
            lines.append(f"GONG BRIEF: {self.enrichment.brief.strip()}")
            lines.append("")

        if self.enrichment.key_points:
            lines.append("KEY POINTS (from Gong analysis):")
            for i, kp in enumerate(self.enrichment.key_points, 1):
                lines.append(f"  {i}. {kp.strip()}")
            lines.append("")

        if self.enrichment.topics:
            topic_strs = [f"{t['name']} ({t['duration']}s)" for t in self.enrichment.topics]
            lines.append(f"TOPICS: {', '.join(topic_strs)}")
            lines.append("")

        if self.enrichment.trackers:
            tracker_strs = [f"{t['name']}({t['count']})" for t in self.enrichment.trackers]
            lines.append(f"SIGNALS: {', '.join(tracker_strs)}")
            lines.append("")

        if self.enrichment.call_outcome:
            lines.append(f"CALL OUTCOME: {self.enrichment.call_outcome}")
            lines.append("")

        # Transcript body
        lines.append("--- TRANSCRIPT ---")
        for turn in self.turns:
            topic_tag = f" [{turn.topic}]" if turn.topic else ""
            lines.append(f"{turn.speaker.name}{topic_tag}: {turn.text}")

        result = "\n".join(lines)

        if max_tokens > 0:
            result = _truncate_to_budget(result, max_tokens)

        return result

    def to_timeline_entry(self, compact: bool = False) -> str:
        """Summary for cross-call context.

        Args:
            compact: If True, skip key_points (which are expensive for CJK calls).
                     Use compact=True for Agents 1-8 to save tokens.
                     Use compact=False for Agent 9 (Adversarial) which needs full detail.
        """
        lines = []
        m = self.metadata
        e = self.enrichment

        lines.append(f"[{m.date}] {m.title} ({m.duration_minutes} min, {m.language})")
        lines.append(f"  Type: {_classify_call(e.classifications)}")

        # Participant summary (compact)
        internal = [s.name for s in self.speakers if s.affiliation == "Internal"]
        external = [s.name for s in self.speakers if s.affiliation != "Internal"]
        all_attendees = self._get_non_speaker_participants()
        ext_attendees = [p.get("name", p.get("email", "?")) for p in all_attendees if p.get("affiliation") != "Internal"]
        external.extend(ext_attendees)

        if internal:
            lines.append(f"  Internal: {', '.join(internal)}")
        if external:
            lines.append(f"  External: {', '.join(external)}")

        # Brief
        if e.brief:
            lines.append(f"  Summary: {e.brief.strip()}")

        # Key points — skip in compact mode (expensive for CJK)
        if not compact and e.key_points:
            lines.append("  Key points:")
            for kp in e.key_points:
                lines.append(f"    - {kp.strip()}")

        # Trackers
        if e.trackers:
            tracker_strs = [f"{t['name']}({t['count']})" for t in e.trackers]
            lines.append(f"  Signals: {', '.join(tracker_strs)}")

        if e.call_outcome:
            lines.append(f"  Outcome: {e.call_outcome}")

        return "\n".join(lines)

    def _get_non_speaker_participants(self) -> list[dict]:
        """Get participants who attended but aren't mapped to a transcript speaker."""
        speaker_names = {s.name.lower() for s in self.speakers}
        speaker_emails = {s.email.lower() for s in self.speakers if s.email}
        result = []
        for p in self.participants_raw:
            name = p.get("name", "")
            email = p.get("email", "")
            # Skip if already a speaker
            if name.lower() in speaker_names or (email and email.lower() in speaker_emails):
                continue
            # Skip Gong placeholder names (Mk12345)
            if name.startswith("Mk") and name[2:].isdigit():
                continue
            # Skip entries with only email and no name
            if not name and email:
                result.append(p)
                continue
            if name:
                result.append(p)
        return result


def _classify_call(classifications: dict[str, bool]) -> str:
    """Produce a human-readable call type from Gong classifications."""
    active = [k.replace("is_", "").replace("_", " ").title() for k, v in classifications.items() if v]
    return ", ".join(active) if active else "General"


def _truncate_to_budget(text: str, max_tokens: int) -> str:
    """Truncate text to stay within token budget.

    Uses CJK-aware token estimation. Preserves the header and truncates
    from the middle of the transcript, keeping the beginning and end
    (most important for deal trajectory).
    """
    est = estimate_tokens(text)
    if est <= max_tokens:
        return text

    marker = "--- TRANSCRIPT ---"
    if marker not in text:
        # No transcript section — truncate proportionally
        ratio = max_tokens / est
        return text[: int(len(text) * ratio)]

    header, transcript = text.split(marker, 1)
    header_with_marker = header + marker

    header_tokens = estimate_tokens(header_with_marker)
    remaining_tokens = max_tokens - header_tokens - 20  # buffer for truncation notice

    if remaining_tokens <= 0:
        return header_with_marker + "\n[Transcript truncated — token budget exceeded]"

    # Compute how many characters we can keep, proportional to token ratio
    transcript_tokens = estimate_tokens(transcript)
    ratio = remaining_tokens / transcript_tokens
    char_budget = int(len(transcript) * ratio)

    # Keep first 60% and last 40% (beginning = context, end = latest state)
    first_part = int(char_budget * 0.6)
    last_part = char_budget - first_part

    tokens_dropped = transcript_tokens - remaining_tokens
    truncated = (
        transcript[:first_part]
        + f"\n\n[... ~{tokens_dropped:,} tokens truncated for budget ...]\n\n"
        + transcript[-last_part:]
    )

    return header_with_marker + truncated
