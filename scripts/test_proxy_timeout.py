"""Test Riskified LiteLLM proxy timeout behavior.

This is the #1 risk for the dashboard build: if the proxy has a gateway
timeout (e.g., 60s idle on the load balancer), streaming won't help if
the proxy buffers SSE events.

Tests:
  1. Streaming Opus call designed to generate >1000 tokens (~60-90s)
  2. Streaming Sonnet call designed to generate ~500 tokens (~30s baseline)
  3. Reports SSE event intervals to detect proxy buffering

Run: python scripts/test_proxy_timeout.py

Requires: VPN connected (for Riskified LLM proxy)
"""

import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "sis"))

from config import ANTHROPIC_API_KEY, ANTHROPIC_BASE_URL, MODEL_AGENT_10, MODEL_AGENTS_2_8, MODEL_AGENT_1

import anthropic


def test_streaming_timeout(model: str, label: str, max_tokens: int, prompt: str):
    """Test a streaming call and report SSE event timing."""
    print(f"\n{'=' * 70}")
    print(f"TEST: {label}")
    print(f"Model: {model}")
    print(f"Max tokens: {max_tokens}")
    print(f"Proxy: {ANTHROPIC_BASE_URL}")
    print(f"{'=' * 70}")

    client = anthropic.Anthropic(
        api_key=ANTHROPIC_API_KEY,
        base_url=ANTHROPIC_BASE_URL,
        timeout=180.0,  # 3 min client timeout — well above proxy limit
        max_retries=0,
    )

    start = time.time()
    first_token_time = None
    last_event_time = start
    event_count = 0
    max_gap = 0.0
    total_text = ""
    event_gaps = []

    try:
        print(f"\n  Connecting... (t=0.0s)")
        with client.messages.stream(
            model=model,
            max_tokens=max_tokens,
            system="You are a helpful assistant. Respond with detailed analysis.",
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            for event in stream:
                now = time.time()
                gap = now - last_event_time

                if hasattr(event, 'type'):
                    if event.type == 'content_block_delta':
                        event_count += 1
                        if first_token_time is None:
                            first_token_time = now
                            print(f"  First token at t={now - start:.1f}s")

                        if gap > max_gap:
                            max_gap = gap
                        event_gaps.append(gap)
                        total_text += event.delta.text if hasattr(event.delta, 'text') else ""

                        # Report progress every 10s
                        elapsed = now - start
                        if int(elapsed) % 10 == 0 and event_count % 50 == 0:
                            print(f"  t={elapsed:.1f}s — {event_count} chunks, max gap={max_gap:.2f}s")

                last_event_time = now

            # Get final message for usage stats
            response = stream.get_final_message()

        elapsed = time.time() - start
        ttft = (first_token_time - start) if first_token_time else 0

        print(f"\n  RESULT: SUCCESS")
        print(f"  Total time: {elapsed:.1f}s")
        print(f"  Time to first token: {ttft:.1f}s")
        print(f"  SSE events (content deltas): {event_count}")
        print(f"  Max gap between events: {max_gap:.2f}s")
        print(f"  Tokens: {response.usage.input_tokens} in / {response.usage.output_tokens} out")
        print(f"  Output length: {len(total_text)} chars")
        print(f"  Stop reason: {response.stop_reason}")

        # Analyze gaps for buffering
        if event_gaps:
            avg_gap = sum(event_gaps) / len(event_gaps)
            gaps_over_5s = sum(1 for g in event_gaps if g > 5.0)
            gaps_over_10s = sum(1 for g in event_gaps if g > 10.0)
            print(f"\n  SSE Gap Analysis:")
            print(f"    Average gap: {avg_gap:.3f}s")
            print(f"    Gaps > 5s: {gaps_over_5s}")
            print(f"    Gaps > 10s: {gaps_over_10s}")
            if max_gap > 30:
                print(f"    WARNING: Max gap {max_gap:.1f}s suggests proxy buffering!")
            elif max_gap > 10:
                print(f"    CAUTION: Max gap {max_gap:.1f}s — monitor in production")
            else:
                print(f"    HEALTHY: Events flowing smoothly (max gap {max_gap:.2f}s)")

        if elapsed > 60:
            print(f"\n  PASSED >60s TIMEOUT TEST: Call completed in {elapsed:.1f}s")
        else:
            print(f"\n  Call completed in {elapsed:.1f}s (under 60s — does not test timeout)")

        return True, elapsed

    except anthropic.APITimeoutError as e:
        elapsed = time.time() - start
        print(f"\n  FAILED: API Timeout at {elapsed:.1f}s")
        print(f"  Error: {e}")
        return False, elapsed

    except anthropic.APIConnectionError as e:
        elapsed = time.time() - start
        print(f"\n  FAILED: Connection Error at {elapsed:.1f}s")
        print(f"  Error: {e}")
        if 55 <= elapsed <= 65:
            print(f"  LIKELY CAUSE: Proxy 60s gateway timeout killed the connection")
        return False, elapsed

    except Exception as e:
        elapsed = time.time() - start
        print(f"\n  FAILED: {type(e).__name__} at {elapsed:.1f}s")
        print(f"  Error: {e}")
        return False, elapsed


def main():
    print("=" * 70)
    print("SIS PROXY TIMEOUT TEST")
    print("=" * 70)
    print(f"Proxy: {ANTHROPIC_BASE_URL}")
    print(f"Purpose: Verify SSE streaming bypasses proxy gateway timeout")
    print(f"Risk: If proxy buffers SSE or has idle timeout, calls >60s will fail")

    results = {}

    # Test 1: Baseline — Haiku, short call (~5-15s)
    ok, elapsed = test_streaming_timeout(
        model=MODEL_AGENT_1,
        label="Baseline: Haiku short call (<30s expected)",
        max_tokens=500,
        prompt="List the top 5 reasons why enterprise SaaS sales cycles are long. Be brief.",
    )
    results["haiku_baseline"] = (ok, elapsed)

    # Test 2: Sonnet, medium call (~30-50s)
    ok, elapsed = test_streaming_timeout(
        model=MODEL_AGENTS_2_8,
        label="Sonnet medium call (30-50s expected)",
        max_tokens=2000,
        prompt=(
            "Write a detailed analysis of the enterprise fraud prevention market. "
            "Cover: market size, key players (Riskified, Signifyd, Forter, Kount), "
            "pricing models, buyer personas, common objections during sales cycles, "
            "integration complexity, and the competitive landscape. "
            "Aim for 1500+ words with specific examples."
        ),
    )
    results["sonnet_medium"] = (ok, elapsed)

    # Test 3: Opus, long call (60-120s) — THE CRITICAL TEST
    ok, elapsed = test_streaming_timeout(
        model=MODEL_AGENT_10,
        label="CRITICAL: Opus long call (60-120s expected — tests >60s timeout)",
        max_tokens=4000,
        prompt=(
            "You are synthesizing a complex enterprise deal assessment. "
            "Write an extremely detailed deal memo covering: "
            "1. Executive summary of deal health (500+ words) "
            "2. Detailed contradiction analysis across 8 dimensions "
            "3. Health score breakdown with rationale per component "
            "4. Momentum analysis with evidence "
            "5. Forecast rationale with what would change the category "
            "6. Top 5 risks with severity and mitigation "
            "7. Top 5 positive signals with supporting evidence "
            "8. Recommended actions with owner, timeline, and priority "
            "9. Confidence interval analysis "
            "10. Key unknowns that could change the assessment "
            "Aim for 3000+ words. Be thorough and analytical."
        ),
    )
    results["opus_long"] = (ok, elapsed)

    # Summary
    print("\n" + "=" * 70)
    print("TIMEOUT TEST SUMMARY")
    print("=" * 70)
    all_passed = True
    for test_name, (ok, elapsed) in results.items():
        status = "PASS" if ok else "FAIL"
        if not ok:
            all_passed = False
        print(f"  [{status}] {test_name}: {elapsed:.1f}s")

    if all_passed:
        print(f"\n  ALL TESTS PASSED — proxy handles streaming correctly.")
        print(f"  Safe to proceed with dashboard implementation.")
    else:
        print(f"\n  SOME TESTS FAILED — proxy timeout risk is REAL.")
        print(f"  Need to investigate proxy configuration before building dashboard.")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
