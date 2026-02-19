"""Test all agents (1-8) against the Xtools account.

Runs Agent 1 first, then Agents 2-8 sequentially (parallel requires asyncio, coming later).
Prints structured output for each agent.

Run: python scripts/test_all_agents.py

Requires: VPN connected (for Riskified LLM proxy)
"""

import json
import logging
import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from config import MODEL_AGENTS_1_9, ANTHROPIC_BASE_URL
from preprocessor import load_account_calls, estimate_tokens

# Override transcript budget for faster runs through the proxy (60s timeout).
# 3K per transcript × 2 transcripts + 3.4K timeline + ~2K system = ~11.5K input.
# Gives ~45s headroom for 3.5K output tokens at ~20ms/token.
TEST_TOKENS_PER_TRANSCRIPT = 3_000
from agents.stage_classifier import run_stage_classifier
from agents.relationship import run_relationship
from agents.commercial import run_commercial
from agents.momentum import run_momentum
from agents.technical import run_technical
from agents.economic_buyer import run_economic_buyer
from agents.msp_next_steps import run_msp_next_steps
from agents.competitive import run_competitive

XTOOLS_DIR = Path(__file__).parent.parent / "data" / "transcripts" / "xtools"

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")


def main():
    print("=" * 70)
    print("SIS Pipeline Test — Agents 1-8 — Xtools Account")
    print(f"Model: {MODEL_AGENTS_1_9}")
    print(f"Proxy: {ANTHROPIC_BASE_URL}")
    print("=" * 70)

    # Load all calls
    calls = load_account_calls(XTOOLS_DIR)
    print(f"\nLoaded {len(calls)} calls ({calls[0].metadata.date} to {calls[-1].metadata.date})")

    # Build context: 1 most recent transcript (60s proxy timeout constrains total tokens).
    # Ultra-compact timeline: just dates, titles, and participant names (~500 tokens for 10 calls).
    timeline_entries = []
    for c in calls:
        int_names = [s.name for s in c.speakers if s.affiliation == "Internal"]
        ext_names = [s.name for s in c.speakers if s.affiliation != "Internal"]
        tl = f"[{c.metadata.date}] {c.metadata.title} ({c.metadata.duration_minutes}min)"
        if ext_names:
            tl += f" — External: {', '.join(ext_names[:3])}"
        if int_names:
            tl += f" — Internal: {', '.join(int_names[:2])}"
        timeline_entries.append(tl)
    recent_calls = calls[-1:]
    transcript_texts = [c.to_agent_text(max_tokens=TEST_TOKENS_PER_TRANSCRIPT) for c in recent_calls]

    print(f"\nContext: {len(timeline_entries)} timeline entries + {len(transcript_texts)} full transcripts")
    timeline_tokens = sum(estimate_tokens(t) for t in timeline_entries)
    transcript_tokens = sum(estimate_tokens(t) for t in transcript_texts)
    total_tokens = timeline_tokens + transcript_tokens
    print(f"Token estimate (CJK-aware): {timeline_tokens:,} timeline + {transcript_tokens:,} transcripts = {total_tokens:,} total")

    pipeline_start = time.time()
    total_input_tokens = 0
    total_output_tokens = 0
    results = {}

    # ── Step 1: Agent 1 (Stage Classifier) ──
    print("\n" + "=" * 70)
    print("STEP 1: Agent 1 — Stage & Progress")
    print("=" * 70)

    try:
        result_1 = run_stage_classifier(transcript_texts, timeline_entries)
        output_1 = result_1.output
        total_input_tokens += result_1.input_tokens
        total_output_tokens += result_1.output_tokens
        results["agent_1"] = result_1

        print(f"  Stage: {output_1.inferred_stage} — {output_1.stage_name} ({output_1.confidence:.0%})")
        if output_1.secondary_stage:
            print(f"  Secondary: {output_1.secondary_stage} — {output_1.secondary_stage_name}")
        print(f"  Tokens: {result_1.input_tokens:,} in / {result_1.output_tokens:,} out | {result_1.elapsed_seconds:.1f}s")
    except Exception as e:
        print(f"  FAILED: {type(e).__name__}: {e}")
        sys.exit(1)

    # Build stage context for downstream agents
    stage_context = {
        "inferred_stage": output_1.inferred_stage,
        "stage_name": output_1.stage_name,
        "confidence": output_1.confidence,
        "reasoning": output_1.reasoning,
    }

    # ── Step 2: Agents 2-8 (Sequential for now, parallel later) ──
    print("\n" + "=" * 70)
    print("STEP 2: Agents 2-8 — Parallel Analysis Layer (running sequentially)")
    print("=" * 70)

    agent_runners = [
        ("agent_2", "Relationship & Power Map", run_relationship),
        ("agent_3", "Commercial & Risk", run_commercial),
        ("agent_4", "Momentum & Engagement", run_momentum),
        ("agent_5", "Technical Validation", run_technical),
        ("agent_6", "Economic Buyer", run_economic_buyer),
        ("agent_7", "MSP & Next Steps", run_msp_next_steps),
        ("agent_8", "Competitive Displacement", run_competitive),
    ]

    for agent_id, agent_name, runner_fn in agent_runners:
        print(f"\n  {'─' * 60}")
        print(f"  Running {agent_name}...")

        try:
            result = runner_fn(transcript_texts, stage_context, timeline_entries)
            output = result.output
            total_input_tokens += result.input_tokens
            total_output_tokens += result.output_tokens
            results[agent_id] = result

            # Print summary based on agent type
            summary = _get_agent_summary(agent_id, output)
            print(f"  Result: {summary}")
            print(f"  Tokens: {result.input_tokens:,} in / {result.output_tokens:,} out | {result.elapsed_seconds:.1f}s")

        except Exception as e:
            print(f"  FAILED: {type(e).__name__}: {e}")
            results[agent_id] = None

    # ── Summary ──
    pipeline_elapsed = time.time() - pipeline_start
    print("\n" + "=" * 70)
    print("PIPELINE SUMMARY")
    print("=" * 70)
    print(f"  Total elapsed: {pipeline_elapsed:.1f}s")
    print(f"  Total tokens: {total_input_tokens:,} in / {total_output_tokens:,} out")
    est_cost = (total_input_tokens * 0.80 / 1_000_000) + (total_output_tokens * 4.00 / 1_000_000)
    print(f"  Estimated cost: ~${est_cost:.2f} (Haiku pricing)")
    print(f"  Agents completed: {sum(1 for v in results.values() if v is not None)}/{len(results)}")

    failed = [k for k, v in results.items() if v is None]
    if failed:
        print(f"  Failed agents: {', '.join(failed)}")

    # Save all results to JSON
    output_path = Path(__file__).parent.parent / "data" / "test_output_all_agents.json"
    all_outputs = {}
    for agent_id, result in results.items():
        if result is not None:
            all_outputs[agent_id] = {
                "output": result.output.model_dump(),
                "input_tokens": result.input_tokens,
                "output_tokens": result.output_tokens,
                "elapsed_seconds": result.elapsed_seconds,
                "model": result.model,
                "attempts": result.attempts,
            }

    with open(output_path, "w") as f:
        json.dump(all_outputs, f, indent=2, ensure_ascii=False)
    print(f"\n  Full output saved to: {output_path}")


def _get_agent_summary(agent_id: str, output) -> str:
    """Get a one-line summary for each agent's output."""
    if agent_id == "agent_2":
        champ = output.champion
        return f"Stakeholders: {len(output.stakeholders)} | Champion: {champ.name or 'None'} ({champ.strength or 'N/A'}) | Threading: {output.multithreading_depth}"
    elif agent_id == "agent_3":
        return f"Pricing: {output.pricing_status} | Readiness: {output.commercial_readiness} | Objections: {len(output.active_objections)} active, {len(output.resolved_objections)} resolved"
    elif agent_id == "agent_4":
        return f"Momentum: {output.momentum_direction} ({output.momentum_confidence:.0%}) | Cadence: {output.call_cadence_assessment} | Buyer Engagement: {output.buyer_engagement_quality}"
    elif agent_id == "agent_5":
        return f"Integration: {output.integration_readiness} | Tech Champion: {output.technical_champion_present} | POC: {output.poc_status or 'N/A'} | Blockers: {len(output.blockers)}"
    elif agent_id == "agent_6":
        return f"EB Confirmed: {output.eb_confirmed} ({output.eb_name or 'N/A'}) | Access Risk: {output.eb_access_risk} | Budget: {output.budget_status}"
    elif agent_id == "agent_7":
        return f"MSP: {output.msp_exists} | Go-live: {output.go_live_date_confirmed} | Specificity: {output.next_step_specificity} | Structure: {output.structural_advancement}"
    elif agent_id == "agent_8":
        return f"Status Quo: {output.status_quo_solution or 'Unknown'} | Displacement: {output.displacement_readiness} | No-Decision Risk: {output.no_decision_risk}"
    return str(output)[:100]


if __name__ == "__main__":
    main()
