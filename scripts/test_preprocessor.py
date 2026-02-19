"""Test the Gong preprocessor against the Xtools account data.

Run: python scripts/test_preprocessor.py
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from preprocessor import load_account_calls

XTOOLS_DIR = Path(__file__).parent.parent / "data" / "transcripts" / "xtools"


def main():
    print("=" * 70)
    print("SIS Preprocessor Test — Xtools Account")
    print("=" * 70)

    calls = load_account_calls(XTOOLS_DIR)
    print(f"\nLoaded {len(calls)} calls\n")

    for i, call in enumerate(calls, 1):
        m = call.metadata
        print(f"--- Call {i}: {m.title[:55]} ---")
        print(f"  Date: {m.date} | Duration: {m.duration_minutes} min | Language: {m.language}")
        print(f"  Has transcript: {call.has_transcript} | Turns: {len(call.turns)}")

        # Speaker mapping summary
        print(f"  Speakers ({len(call.speakers)}):")
        for s in call.speakers:
            mapped = "mapped" if s.is_mapped else "inferred"
            print(f"    {s.name:25s} [{s.affiliation:8s}] {s.talk_time_pct:5.1f}% ({mapped})")

        # Enrichment summary
        e = call.enrichment
        if e.brief:
            print(f"  Gong brief: {e.brief[:80].strip()}...")
        if e.trackers:
            print(f"  Trackers: {', '.join(t['name'] for t in e.trackers[:4])}")
        if e.classifications:
            active = [k for k, v in e.classifications.items() if v]
            if active:
                print(f"  Classifications: {', '.join(active)}")

        # Agent text output preview
        agent_text = call.to_agent_text()
        char_count = len(agent_text)
        est_tokens = char_count // 4
        print(f"  Agent text: {char_count:,} chars (~{est_tokens:,} tokens)")

        # Show first 5 turns as sample
        if call.turns:
            print(f"  Sample turns:")
            for turn in call.turns[:3]:
                topic = f" [{turn.topic}]" if turn.topic else ""
                text_preview = turn.text[:80] + ("..." if len(turn.text) > 80 else "")
                print(f"    {turn.speaker.name}{topic}: {text_preview}")

        print()

    # Summary stats
    total_turns = sum(len(c.turns) for c in calls)
    total_chars = sum(len(c.to_agent_text()) for c in calls)
    languages = set(c.metadata.language for c in calls)
    all_speakers = set()
    for c in calls:
        for s in c.speakers:
            if s.is_mapped:
                all_speakers.add(s.name)

    print("=" * 70)
    print("SUMMARY")
    print(f"  Calls: {len(calls)}")
    print(f"  Total turns: {total_turns}")
    print(f"  Total agent text: {total_chars:,} chars (~{total_chars // 4:,} est. tokens)")
    print(f"  Languages: {', '.join(sorted(languages))}")
    print(f"  Mapped speakers: {', '.join(sorted(all_speakers))}")

    # Test token budget truncation
    print("\n--- Token Budget Test ---")
    longest = max(calls, key=lambda c: len(c.to_agent_text()))
    full = len(longest.to_agent_text())
    truncated = len(longest.to_agent_text(max_tokens=8000))
    print(f"  Longest call: {longest.metadata.title[:40]}")
    print(f"  Full: {full:,} chars | Truncated to 8K tokens: {truncated:,} chars")
    print(f"  Reduction: {(1 - truncated / full) * 100:.0f}%")

    print("\nPreprocessor test complete.")


if __name__ == "__main__":
    main()
