"""Test Agent 1 (Stage Classifier) against the Xtools account.

Runs the stage classifier on the most recent calls and prints the structured output.
Tests both single-call and multi-call analysis.

Run: python scripts/test_agent_1.py

Requires: VPN connected (for Riskified LLM proxy)
"""

import json
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "sis"))

from config import MODEL_AGENTS_1_8, ANTHROPIC_BASE_URL, MAX_TOKENS_PER_TRANSCRIPT
from preprocessor import load_account_calls
from agents.stage_classifier import run_stage_classifier

XTOOLS_DIR = Path(__file__).parent.parent / "data" / "transcripts" / "xtools"

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")


def main():
    print("=" * 70)
    print("Agent 1: Stage & Progress — Xtools Account Test")
    print(f"Model: {MODEL_AGENTS_1_8}")
    print(f"Proxy: {ANTHROPIC_BASE_URL}")
    print("=" * 70)

    # Load all calls
    calls = load_account_calls(XTOOLS_DIR)
    print(f"\nLoaded {len(calls)} calls ({calls[0].metadata.date} to {calls[-1].metadata.date})")

    # Build timeline entries (compact cross-call context)
    timeline_entries = [c.to_timeline_entry() for c in calls]

    # For Agent 1, send the 3 most recent calls as full transcripts
    # plus timeline entries for all 10 calls
    recent_calls = calls[-3:]
    transcript_texts = [c.to_agent_text(max_tokens=MAX_TOKENS_PER_TRANSCRIPT) for c in recent_calls]

    print(f"\nSending to Agent 1:")
    print(f"  Timeline entries: {len(timeline_entries)} calls")
    print(f"  Full transcripts: {len(transcript_texts)} most recent calls")
    for c in recent_calls:
        print(f"    - {c.metadata.date}: {c.metadata.title[:50]}")

    total_chars = sum(len(t) for t in timeline_entries) + sum(len(t) for t in transcript_texts)
    print(f"  Total input: ~{total_chars:,} chars (~{total_chars // 4:,} est. tokens)")

    print("\nRunning Agent 1...")
    print("-" * 70)

    try:
        agent_result = run_stage_classifier(transcript_texts, timeline_entries)
    except Exception as e:
        print(f"\nERROR: {type(e).__name__}: {e}")
        sys.exit(1)

    # Unwrap AgentResult
    output = agent_result.output

    # Print execution metadata
    print("\n" + "=" * 70)
    print("EXECUTION METADATA")
    print("=" * 70)
    print(f"  Model: {agent_result.model}")
    print(f"  Tokens: {agent_result.input_tokens:,} in / {agent_result.output_tokens:,} out")
    print(f"  Elapsed: {agent_result.elapsed_seconds:.1f}s")
    print(f"  Attempts: {agent_result.attempts}")

    # Print results
    print("\n" + "=" * 70)
    print("AGENT 1 OUTPUT")
    print("=" * 70)
    print(f"\nInferred Stage: {output.inferred_stage} — {output.stage_name}")
    print(f"Confidence: {output.confidence:.0%}")

    if output.secondary_stage:
        print(f"Secondary Stage: {output.secondary_stage} — {output.secondary_stage_name}")

    print(f"Calls Analyzed: {output.calls_analyzed}")

    print(f"\nReasoning:\n  {output.reasoning}")
    print(f"\nProgression Narrative:\n  {output.progression_narrative}")

    print("\nMilestones:")
    for m in output.milestones:
        status = "ACHIEVED" if m.achieved else "NOT MET"
        print(f"  [{status:8s}] {m.milestone}")
        print(f"             Evidence: {m.evidence}")

    if output.stage_risk_signals:
        print("\nRisk Signals:")
        for signal in output.stage_risk_signals:
            print(f"  - {signal}")

    if output.data_quality_notes:
        print("\nData Quality Notes:")
        for note in output.data_quality_notes:
            print(f"  - {note}")

    # Print raw JSON for inspection
    print("\n" + "-" * 70)
    print("Raw JSON output:")
    print(json.dumps(output.model_dump(), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
