"""Test Agents 9 and 10 using saved agent 1-8 outputs.

Loads agent 1-8 results from data/test_output_all_agents.json and runs
Agents 9 (Open Discovery) and 10 (Synthesis) against them. This avoids
re-running the full pipeline when iterating on agents 9-10.

Run: python scripts/test_agents_9_10.py

Requires: VPN connected (for Riskified LLM proxy)
"""

import json
import logging
import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from config import MODEL_AGENTS_9_10, ANTHROPIC_BASE_URL, MAX_TOKENS_PER_TRANSCRIPT
from preprocessor import load_account_calls, estimate_tokens
from agents.open_discovery import run_open_discovery
from agents.synthesis import run_synthesis

XTOOLS_DIR = Path(__file__).parent.parent / "data" / "transcripts" / "xtools"
SAVED_OUTPUT_PATH = Path(__file__).parent.parent / "data" / "test_output_all_agents.json"

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")


def main():
    print("=" * 70)
    print("SIS Test — Agents 9 & 10 Only (using saved upstream outputs)")
    print(f"Model: {MODEL_AGENTS_9_10}")
    print(f"Proxy: {ANTHROPIC_BASE_URL}")
    print("=" * 70)

    # Load saved agent 1-8 outputs
    if not SAVED_OUTPUT_PATH.exists():
        print(f"\nERROR: No saved outputs found at {SAVED_OUTPUT_PATH}")
        print("Run test_all_agents.py first to generate agent 1-8 outputs.")
        sys.exit(1)

    with open(SAVED_OUTPUT_PATH) as f:
        saved_data = json.load(f)

    upstream_agents = [f"agent_{i}" for i in range(1, 9)]
    missing = [a for a in upstream_agents if a not in saved_data]
    if missing:
        print(f"\nWARNING: Missing agents in saved data: {missing}")
        print("Some upstream outputs are unavailable. Proceeding with what's available.")

    upstream_outputs = {
        agent_id: data["output"]
        for agent_id, data in saved_data.items()
        if agent_id in upstream_agents
    }
    print(f"\nLoaded {len(upstream_outputs)} upstream agent outputs from {SAVED_OUTPUT_PATH}")

    # Load transcripts (Agent 9 needs them)
    calls = load_account_calls(XTOOLS_DIR)
    timeline_entries = [c.to_timeline_entry(compact=True) for c in calls]
    recent_calls = calls[-2:]
    transcript_texts = [c.to_agent_text(max_tokens=MAX_TOKENS_PER_TRANSCRIPT) for c in recent_calls]
    print(f"Loaded {len(transcript_texts)} transcripts for Agent 9")

    # Stage context from Agent 1
    agent_1_output = upstream_outputs.get("agent_1", {})
    findings = agent_1_output.get("findings", {})
    stage_context = {
        "inferred_stage": findings.get("inferred_stage"),
        "stage_name": findings.get("stage_name"),
        "confidence": agent_1_output.get("confidence", {}).get("overall"),
        "reasoning": findings.get("reasoning"),
    }

    total_input_tokens = 0
    total_output_tokens = 0

    # ── Agent 9: Open Discovery ──
    print("\n" + "=" * 70)
    print("Agent 9: Open Discovery / Adversarial Validator")
    print("=" * 70)

    try:
        start_9 = time.time()
        result_9 = run_open_discovery(transcript_texts, stage_context, upstream_outputs, timeline_entries)
        elapsed_9 = time.time() - start_9
        output_9 = result_9.output
        total_input_tokens += result_9.input_tokens
        total_output_tokens += result_9.output_tokens

        f9 = output_9.findings
        print(f"  Novel findings: {len(f9.novel_findings)}")
        for nf in f9.novel_findings:
            print(f"    - [{nf.category}] {nf.finding[:70]}")
        print(f"  Adversarial challenges: {len(f9.adversarial_challenges)}")
        for ch in f9.adversarial_challenges:
            print(f"    - [{ch.severity}] {ch.target_agent_id}: {ch.claim_challenged[:60]}")
        print(f"  Upstream gaps: {len(f9.upstream_gaps_identified)}")
        for gap in f9.upstream_gaps_identified:
            print(f"    - {gap[:70]}")
        print(f"  No additional signals: {f9.no_additional_signals}")
        print(f"  Confidence: {output_9.confidence.overall:.0%} — {output_9.confidence.rationale[:80]}")
        print(f"  Evidence citations: {len(output_9.evidence)}")
        print(f"  Sparse data: {output_9.sparse_data_flag}")
        print(f"  Tokens: {result_9.input_tokens:,} in / {result_9.output_tokens:,} out | {elapsed_9:.1f}s")

        # Add Agent 9 to outputs for Agent 10
        upstream_outputs["agent_9"] = output_9.model_dump()
    except Exception as e:
        print(f"  FAILED: {type(e).__name__}: {e}")
        print("  Cannot run Agent 10 without Agent 9 output.")
        sys.exit(1)

    # ── Agent 10: Synthesis ──
    print("\n" + "=" * 70)
    print("Agent 10: Synthesis (Final Deal Assessment)")
    print("=" * 70)

    try:
        start_10 = time.time()
        result_10 = run_synthesis(upstream_outputs, stage_context)
        elapsed_10 = time.time() - start_10
        output_10 = result_10.output
        total_input_tokens += result_10.input_tokens
        total_output_tokens += result_10.output_tokens

        print(f"  Stage: {output_10.inferred_stage} — {output_10.inferred_stage_name} ({output_10.inferred_stage_confidence:.0%})")
        print(f"\n  HEALTH SCORE: {output_10.health_score}/100")
        for comp in output_10.health_score_breakdown:
            bar = "█" * comp.score + "░" * (comp.max_score - comp.score)
            print(f"    {comp.component:30s} {bar} {comp.score}/{comp.max_score}")

        print(f"\n  Momentum: {output_10.momentum_direction} — {output_10.momentum_trend}")
        print(f"  Forecast: {output_10.forecast_category} — {output_10.forecast_rationale}")

        print(f"\n  Contradictions ({len(output_10.contradiction_map)}):")
        for c in output_10.contradiction_map:
            print(f"    [{c.dimension}] {c.contradiction_detail[:60]}")
            print(f"      Resolution ({c.resolution_confidence:.0%}): {c.resolution[:60]}")

        print(f"\n  Top Positive Signals ({len(output_10.top_positive_signals)}):")
        for s in output_10.top_positive_signals:
            print(f"    + {s.signal[:70]}")

        print(f"\n  Top Risks ({len(output_10.top_risks)}):")
        for r in output_10.top_risks:
            print(f"    ! [{r.severity}] {r.risk[:60]}")

        print(f"\n  Recommended Actions ({len(output_10.recommended_actions)}):")
        for a in output_10.recommended_actions:
            print(f"    [{a.priority}] {a.owner}: {a.action[:60]}")

        print(f"\n  Overall Confidence: {output_10.confidence_interval.overall_confidence:.0%}")
        if output_10.confidence_interval.key_unknowns:
            print(f"  Key unknowns:")
            for u in output_10.confidence_interval.key_unknowns:
                print(f"    ? {u[:70]}")

        print(f"\n  Agents consumed: {', '.join(output_10.agents_consumed)}")
        if output_10.sparse_data_agents:
            print(f"  Sparse data agents (0.8x weight): {', '.join(output_10.sparse_data_agents)}")

        print(f"\n  Tokens: {result_10.input_tokens:,} in / {result_10.output_tokens:,} out | {elapsed_10:.1f}s")

        # Print the deal memo
        print(f"\n  {'─' * 60}")
        print("  DEAL MEMO:")
        print(f"  {'─' * 60}")
        for line in output_10.deal_memo.split("\n"):
            print(f"  {line}")
        print(f"  {'─' * 60}")
    except Exception as e:
        print(f"  FAILED: {type(e).__name__}: {e}")

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"  Total tokens: {total_input_tokens:,} in / {total_output_tokens:,} out")

    # Save combined output
    output_path = Path(__file__).parent.parent / "data" / "test_output_agents_9_10.json"
    combined = {
        "agent_9": {
            "output": result_9.output.model_dump(),
            "input_tokens": result_9.input_tokens,
            "output_tokens": result_9.output_tokens,
            "elapsed_seconds": result_9.elapsed_seconds,
            "model": result_9.model,
        },
    }
    if "result_10" in dir():
        combined["agent_10"] = {
            "output": result_10.output.model_dump(),
            "input_tokens": result_10.input_tokens,
            "output_tokens": result_10.output_tokens,
            "elapsed_seconds": result_10.elapsed_seconds,
            "model": result_10.model,
        }
    with open(output_path, "w") as f:
        json.dump(combined, f, indent=2, ensure_ascii=False)
    print(f"  Saved to: {output_path}")


if __name__ == "__main__":
    main()
