"""Test all agents (1-10) against the Xtools account.

Pipeline execution order:
  1. Agent 1 (Stage Classifier) — sequential
  2. Agents 2-8 — PARALLEL using asyncio
  3. Agent 9 (Open Discovery) — sequential, receives agents 1-8 outputs
  4. Agent 10 (Synthesis) — sequential, receives agents 1-9 outputs

Run: python scripts/test_all_agents.py

Requires: VPN connected (for Riskified LLM proxy)
"""

import asyncio
import json
import logging
import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from config import MODEL_AGENTS_1_8, MODEL_AGENTS_9_10, ANTHROPIC_BASE_URL, MAX_TOKENS_PER_TRANSCRIPT
from preprocessor import load_account_calls, estimate_tokens
from agents.stage_classifier import run_stage_classifier
from agents.runner import run_agents_parallel
from agents.open_discovery import run_open_discovery
from agents.synthesis import run_synthesis

# Import build_call from each agent module for parallel execution
from agents.relationship import build_call as build_call_2
from agents.commercial import build_call as build_call_3
from agents.momentum import build_call as build_call_4
from agents.technical import build_call as build_call_5
from agents.economic_buyer import build_call as build_call_6
from agents.msp_next_steps import build_call as build_call_7
from agents.competitive import build_call as build_call_8

XTOOLS_DIR = Path(__file__).parent.parent / "data" / "transcripts" / "xtools"

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")


AGENT_META = [
    ("agent_2", "Relationship & Power Map", build_call_2),
    ("agent_3", "Commercial & Risk", build_call_3),
    ("agent_4", "Momentum & Engagement", build_call_4),
    ("agent_5", "Technical Validation", build_call_5),
    ("agent_6", "Economic Buyer", build_call_6),
    ("agent_7", "MSP & Next Steps", build_call_7),
    ("agent_8", "Competitive Displacement", build_call_8),
]


def main():
    print("=" * 70)
    print("SIS Pipeline Test — Agents 1-10 — Xtools Account")
    print(f"Model (1-8): {MODEL_AGENTS_1_8}")
    print(f"Model (9-10): {MODEL_AGENTS_9_10}")
    print(f"Proxy: {ANTHROPIC_BASE_URL}")
    print("=" * 70)

    # Load all calls
    calls = load_account_calls(XTOOLS_DIR)
    print(f"\nLoaded {len(calls)} calls ({calls[0].metadata.date} to {calls[-1].metadata.date})")

    # Build context: 2 most recent transcripts at full budget + compact timeline.
    timeline_entries = [c.to_timeline_entry(compact=True) for c in calls]
    recent_calls = calls[-2:]
    transcript_texts = [c.to_agent_text(max_tokens=MAX_TOKENS_PER_TRANSCRIPT) for c in recent_calls]

    print(f"\nContext: {len(timeline_entries)} timeline entries + {len(transcript_texts)} full transcripts")
    timeline_tokens = sum(estimate_tokens(t) for t in timeline_entries)
    transcript_tokens = sum(estimate_tokens(t) for t in transcript_texts)
    total_tokens = timeline_tokens + transcript_tokens
    print(f"Token estimate (CJK-aware): {timeline_tokens:,} timeline + {transcript_tokens:,} transcripts = {total_tokens:,} total")

    pipeline_start = time.time()
    total_input_tokens = 0
    total_output_tokens = 0
    results = {}

    # ── Step 1: Agent 1 (Stage Classifier) — Sequential ──
    print("\n" + "=" * 70)
    print("STEP 1: Agent 1 — Stage & Progress")
    print("=" * 70)

    try:
        result_1 = run_stage_classifier(transcript_texts, timeline_entries)
        output_1 = result_1.output
        total_input_tokens += result_1.input_tokens
        total_output_tokens += result_1.output_tokens
        results["agent_1"] = result_1

        f = output_1.findings
        print(f"  Stage: {f.inferred_stage} — {f.stage_name} (conf: {output_1.confidence.overall:.0%})")
        if f.secondary_stage:
            print(f"  Secondary: {f.secondary_stage} — {f.secondary_stage_name}")
        print(f"  Evidence citations: {len(output_1.evidence)}")
        print(f"  Sparse data: {output_1.sparse_data_flag}")
        print(f"  Tokens: {result_1.input_tokens:,} in / {result_1.output_tokens:,} out | {result_1.elapsed_seconds:.1f}s")
    except Exception as e:
        print(f"  FAILED: {type(e).__name__}: {e}")
        sys.exit(1)

    # Build stage context for downstream agents
    stage_context = {
        "inferred_stage": output_1.findings.inferred_stage,
        "stage_name": output_1.findings.stage_name,
        "confidence": output_1.confidence.overall,
        "reasoning": output_1.findings.reasoning,
    }

    # ── Step 2: Agents 2-8 — PARALLEL ──
    print("\n" + "=" * 70)
    print("STEP 2: Agents 2-8 — Parallel Analysis Layer (7 agents concurrent)")
    print("=" * 70)

    # Build kwargs dicts for all 7 agents
    tasks = []
    for agent_id, agent_name, build_fn in AGENT_META:
        task = build_fn(transcript_texts, stage_context, timeline_entries)
        tasks.append(task)
        print(f"  Prepared: {agent_name}")

    # Run all 7 in parallel
    parallel_start = time.time()
    print(f"\n  Launching {len(tasks)} agents in parallel...")
    parallel_results = asyncio.run(run_agents_parallel(tasks))
    parallel_elapsed = time.time() - parallel_start
    print(f"\n  All agents completed in {parallel_elapsed:.1f}s (parallel wall time)")

    # Process results
    for i, (agent_id, agent_name, _) in enumerate(AGENT_META):
        result = parallel_results[i]
        print(f"\n  {'─' * 60}")
        print(f"  {agent_name}:")

        if isinstance(result, Exception):
            print(f"  FAILED: {type(result).__name__}: {result}")
            results[agent_id] = None
        else:
            output = result.output
            total_input_tokens += result.input_tokens
            total_output_tokens += result.output_tokens
            results[agent_id] = result

            summary = _get_agent_summary(agent_id, output)
            print(f"  Result: {summary}")
            print(f"  Confidence: {output.confidence.overall:.0%} — {output.confidence.rationale[:80]}")
            print(f"  Evidence citations: {len(output.evidence)} | Sparse data: {output.sparse_data_flag}")
            print(f"  Tokens: {result.input_tokens:,} in / {result.output_tokens:,} out | {result.elapsed_seconds:.1f}s | Attempt {result.attempts}")

    # ── Step 3: Agent 9 (Open Discovery) — Sequential ──
    print("\n" + "=" * 70)
    print("STEP 3: Agent 9 — Open Discovery / Adversarial Validator")
    print("=" * 70)

    upstream_outputs = {}
    for agent_id, result in results.items():
        if result is not None:
            upstream_outputs[agent_id] = result.output.model_dump()

    try:
        result_9 = run_open_discovery(transcript_texts, stage_context, upstream_outputs, timeline_entries)
        output_9 = result_9.output
        total_input_tokens += result_9.input_tokens
        total_output_tokens += result_9.output_tokens
        results["agent_9"] = result_9

        f9 = output_9.findings
        print(f"  Novel findings: {len(f9.novel_findings)}")
        print(f"  Adversarial challenges: {len(f9.adversarial_challenges)}")
        for ch in f9.adversarial_challenges:
            print(f"    - [{ch.severity}] {ch.target_agent_id}: {ch.claim_challenged[:60]}")
        print(f"  Upstream gaps: {len(f9.upstream_gaps_identified)}")
        print(f"  No additional signals: {f9.no_additional_signals}")
        print(f"  Confidence: {output_9.confidence.overall:.0%}")
        print(f"  Evidence citations: {len(output_9.evidence)}")
        print(f"  Tokens: {result_9.input_tokens:,} in / {result_9.output_tokens:,} out | {result_9.elapsed_seconds:.1f}s")
    except Exception as e:
        print(f"  FAILED: {type(e).__name__}: {e}")
        results["agent_9"] = None

    # ── Step 4: Agent 10 (Synthesis) — Sequential ──
    print("\n" + "=" * 70)
    print("STEP 4: Agent 10 — Synthesis (Final Deal Assessment)")
    print("=" * 70)

    # Collect all 9 agent outputs
    all_outputs = {}
    for agent_id, result in results.items():
        if result is not None:
            all_outputs[agent_id] = result.output.model_dump()

    try:
        result_10 = run_synthesis(all_outputs, stage_context)
        output_10 = result_10.output
        total_input_tokens += result_10.input_tokens
        total_output_tokens += result_10.output_tokens
        results["agent_10"] = result_10

        print(f"  Stage: {output_10.inferred_stage} — {output_10.inferred_stage_name} ({output_10.inferred_stage_confidence:.0%})")
        print(f"  Health Score: {output_10.health_score}/100")
        for comp in output_10.health_score_breakdown:
            print(f"    {comp.component}: {comp.score}/{comp.max_score} — {comp.rationale[:60]}")
        print(f"  Momentum: {output_10.momentum_direction} — {output_10.momentum_trend[:60]}")
        print(f"  Forecast: {output_10.forecast_category} — {output_10.forecast_rationale[:80]}")
        print(f"  Contradictions: {len(output_10.contradiction_map)}")
        print(f"  Positive signals: {len(output_10.top_positive_signals)} | Risks: {len(output_10.top_risks)}")
        print(f"  Actions: {len(output_10.recommended_actions)}")
        for a in output_10.recommended_actions:
            print(f"    [{a.priority}] {a.owner}: {a.action[:60]}")
        print(f"  Confidence: {output_10.confidence_interval.overall_confidence:.0%}")
        print(f"  Tokens: {result_10.input_tokens:,} in / {result_10.output_tokens:,} out | {result_10.elapsed_seconds:.1f}s")
    except Exception as e:
        print(f"  FAILED: {type(e).__name__}: {e}")
        results["agent_10"] = None

    # ── Summary ──
    pipeline_elapsed = time.time() - pipeline_start
    print("\n" + "=" * 70)
    print("PIPELINE SUMMARY")
    print("=" * 70)
    print(f"  Total elapsed: {pipeline_elapsed:.1f}s")
    print(f"    Agent 1 (sequential): {result_1.elapsed_seconds:.1f}s")
    print(f"    Agents 2-8 (parallel): {parallel_elapsed:.1f}s")

    # Sum individual elapsed times to show sequential equivalent
    sequential_equivalent = sum(
        r.elapsed_seconds for r in parallel_results if not isinstance(r, Exception)
    )
    speedup = sequential_equivalent / parallel_elapsed if parallel_elapsed > 0 else 0
    print(f"    Sequential equivalent: {sequential_equivalent:.1f}s → {speedup:.1f}x speedup")

    if results.get("agent_9") and not isinstance(results["agent_9"], Exception):
        print(f"    Agent 9 (sequential): {results['agent_9'].elapsed_seconds:.1f}s")
    if results.get("agent_10") and not isinstance(results["agent_10"], Exception):
        print(f"    Agent 10 (sequential): {results['agent_10'].elapsed_seconds:.1f}s")

    print(f"  Total tokens: {total_input_tokens:,} in / {total_output_tokens:,} out")
    est_cost_sonnet = (total_input_tokens * 3.00 / 1_000_000) + (total_output_tokens * 15.00 / 1_000_000)
    print(f"  Estimated cost: ~${est_cost_sonnet:.2f} (blended Sonnet/Opus)")
    print(f"  Agents completed: {sum(1 for v in results.values() if v is not None)}/{len(results)}")

    failed = [k for k, v in results.items() if v is None]
    if failed:
        print(f"  Failed agents: {', '.join(failed)}")

    # Save all results to JSON
    output_path = Path(__file__).parent.parent / "data" / "test_output_all_agents.json"
    all_saved = {}
    for agent_id, result in results.items():
        if result is not None:
            all_saved[agent_id] = {
                "output": result.output.model_dump(),
                "input_tokens": result.input_tokens,
                "output_tokens": result.output_tokens,
                "elapsed_seconds": result.elapsed_seconds,
                "model": result.model,
                "attempts": result.attempts,
            }

    with open(output_path, "w") as f:
        json.dump(all_saved, f, indent=2, ensure_ascii=False)
    print(f"\n  Full output saved to: {output_path}")


def _get_agent_summary(agent_id: str, output) -> str:
    """Get a one-line summary for each agent's output."""
    f = output.findings
    if agent_id == "agent_2":
        champ = f.champion
        return f"Stakeholders: {len(f.stakeholders)} | Champion: {champ.name or 'None'} ({champ.strength or 'N/A'}) | Threading: {f.multithreading_depth}"
    elif agent_id == "agent_3":
        return f"Pricing: {f.pricing_status} | Readiness: {f.commercial_readiness} | Objections: {len(f.active_objections)} active, {len(f.resolved_objections)} resolved"
    elif agent_id == "agent_4":
        return f"Momentum: {f.momentum_direction} | Cadence: {f.call_cadence_assessment} | Buyer Engagement: {f.buyer_engagement_quality}"
    elif agent_id == "agent_5":
        return f"Integration: {f.integration_readiness} | Tech Champion: {f.technical_champion_present} | POC: {f.poc_status or 'N/A'} | Blockers: {len(f.blockers)}"
    elif agent_id == "agent_6":
        return f"EB Confirmed: {f.eb_confirmed} ({f.eb_name or 'N/A'}) | Access Risk: {f.eb_access_risk} | Budget: {f.budget_status}"
    elif agent_id == "agent_7":
        return f"MSP: {f.msp_exists} | Go-live: {f.go_live_date_confirmed} | Specificity: {f.next_step_specificity} | Structure: {f.structural_advancement}"
    elif agent_id == "agent_8":
        return f"Status Quo: {f.status_quo_solution or 'Unknown'} | Displacement: {f.displacement_readiness} | No-Decision Risk: {f.no_decision_risk}"
    return str(output)[:100]


if __name__ == "__main__":
    main()
