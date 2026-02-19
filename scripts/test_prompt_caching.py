"""Test: Does Anthropic prompt caching work through the Riskified LiteLLM proxy?

Prompt caching lets us reuse cached system-prompt prefixes across requests,
saving input tokens and reducing latency. This script verifies whether the
proxy preserves the `cache_control` block metadata that Anthropic needs.

Minimum cacheable prefix: 1,024 tokens (Sonnet), 2,048 tokens (Opus).
Cache TTL: 5 minutes (ephemeral).

Run: python scripts/test_prompt_caching.py

Requires: VPN connected (for Riskified LLM proxy)
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import anthropic
from config import ANTHROPIC_API_KEY, ANTHROPIC_BASE_URL, MODEL_AGENTS_1_8


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def build_large_system_prefix() -> str:
    """Generate a system prompt prefix guaranteed to exceed 1,024 tokens.

    We use a realistic SIS-style context block so the test doubles as a
    sanity check for our actual use case (multi-agent sales analysis).
    Repeating structured content ensures we comfortably clear the minimum
    cacheable threshold regardless of tokenizer variance.
    """
    preamble = (
        "You are a senior enterprise sales analyst. Your role is to analyze "
        "sales call transcripts and produce structured assessments of deal "
        "health, stakeholder engagement, and competitive positioning.\n\n"
        "## Framework: MEDDPICC\n"
        "Use the MEDDPICC framework to evaluate every opportunity:\n"
        "- Metrics: Quantified business outcomes the buyer cares about\n"
        "- Economic Buyer: The person with budget authority and veto power\n"
        "- Decision Criteria: The formal and informal requirements for vendor selection\n"
        "- Decision Process: The steps, timeline, and approvals required to close\n"
        "- Paper Process: Legal, procurement, security review requirements\n"
        "- Implicate the Pain: Connect your solution to the buyer's critical business issues\n"
        "- Champion: An internal advocate who sells on your behalf when you are not in the room\n"
        "- Competition: Known and unknown alternatives the buyer is evaluating\n\n"
    )

    # Each block is ~200 tokens. We need 6+ blocks to safely exceed 1,024.
    stage_block = (
        "## Stage Definitions\n\n"
        "### Stage 1 - Qualification\n"
        "Initial engagement where we determine if the prospect has a genuine need, "
        "budget authority, and timeline. Key signals: discovery call completed, "
        "pain points identified, initial stakeholder map created, ICP fit confirmed. "
        "Exit criteria: Qualified opportunity with identified champion and economic buyer.\n\n"
        "### Stage 2 - Discovery\n"
        "Deep-dive into business requirements, current workflows, pain quantification, "
        "and success metrics definition. Key signals: technical requirements documented, "
        "decision criteria shared, competitive landscape mapped, ROI discussion initiated. "
        "Exit criteria: Mutual action plan agreed with clear next steps and timeline.\n\n"
        "### Stage 3 - Evaluation\n"
        "Hands-on proof of value through demo, POC, or pilot. Technical validation "
        "and stakeholder alignment. Key signals: POC success criteria defined, technical "
        "team engaged, security review initiated, reference calls requested. "
        "Exit criteria: Technical win confirmed, champion actively selling internally.\n\n"
        "### Stage 4 - Proposal\n"
        "Commercial negotiation, legal review, and procurement process. Key signals: "
        "pricing proposal delivered, MSA/DPA in redline, procurement engaged, executive "
        "sponsor briefed, budget allocated. Exit criteria: Verbal commitment received.\n\n"
        "### Stage 5 - Closing\n"
        "Final approvals, contract execution, and handoff to implementation. Key signals: "
        "legal approved, signature obtained, PO issued, implementation kickoff scheduled. "
        "Exit criteria: Closed-won with signed contract and payment terms confirmed.\n\n"
    )

    scoring_rubric = (
        "## Health Scoring Rubric\n\n"
        "Score each dimension on a 0-100 scale:\n\n"
        "### Economic Buyer Engagement (weight: 20%)\n"
        "- 90-100: EB directly expressed commitment, discussed budget, set timeline\n"
        "- 70-89: EB attended meetings, asked strategic questions, delegated evaluation\n"
        "- 50-69: EB mentioned but not directly engaged; champion reports EB support\n"
        "- 30-49: EB identified but no direct engagement; unclear budget authority\n"
        "- 0-29: EB not identified or actively disengaged\n\n"
        "### Champion Strength (weight: 15%)\n"
        "- 90-100: Champion actively selling internally, sharing materials, scheduling meetings\n"
        "- 70-89: Champion engaged, provides intel, introduces stakeholders\n"
        "- 50-69: Internal contact supportive but passive; does not proactively advance deal\n"
        "- 30-49: Contact identified but limited influence or engagement\n"
        "- 0-29: No champion identified; all momentum driven by sales team\n\n"
        "### Technical Path Clarity (weight: 10%)\n"
        "- 90-100: Technical requirements fully validated, integration plan documented\n"
        "- 70-89: Core technical fit confirmed, minor open items being addressed\n"
        "- 50-69: Technical evaluation in progress, some concerns raised\n"
        "- 30-49: Technical requirements unclear or significant blockers identified\n"
        "- 0-29: No technical evaluation started or fundamental misfit detected\n\n"
        "### Competitive Position (weight: 10%)\n"
        "- 90-100: Clearly preferred vendor, competitors eliminated or significantly behind\n"
        "- 70-89: Strong position with differentiated value; competitive but leading\n"
        "- 50-69: Competitive evaluation in progress; no clear leader\n"
        "- 30-49: Behind competitor on key dimensions; need to differentiate\n"
        "- 0-29: At significant disadvantage or unaware of competitive landscape\n\n"
        "### Momentum & Velocity (weight: 15%)\n"
        "- 90-100: Consistent forward motion, meetings happening on schedule, no stalls\n"
        "- 70-89: Good pace with minor delays; buyer responsive within 48 hours\n"
        "- 50-69: Some stalls or delays; meetings rescheduled; gaps between engagements\n"
        "- 30-49: Significant slowdown; buyer unresponsive for 1-2 weeks\n"
        "- 0-29: Deal stalled; no engagement for 2+ weeks; risk of going dark\n\n"
    )

    output_format = (
        "## Output Format\n\n"
        "Always return valid JSON matching this schema:\n"
        "{\n"
        '  "inferred_stage": 1-5,\n'
        '  "stage_name": "string",\n'
        '  "confidence": 0.0-1.0,\n'
        '  "health_score": 0-100,\n'
        '  "reasoning": "string (2-3 sentences)",\n'
        '  "key_risks": ["string"],\n'
        '  "recommended_actions": ["string"],\n'
        '  "stakeholder_map": {\n'
        '    "economic_buyer": {"name": "string", "engagement_level": "string"},\n'
        '    "champion": {"name": "string", "strength": "string"},\n'
        '    "technical_evaluator": {"name": "string", "status": "string"}\n'
        "  }\n"
        "}\n\n"
        "Important rules:\n"
        "- Never hallucinate stakeholder names. Only include names explicitly mentioned.\n"
        "- If a field cannot be determined, use null rather than guessing.\n"
        "- Confidence must reflect data quality: fewer calls = lower confidence ceiling.\n"
        "- Always cite specific call evidence for stage and health assessments.\n"
        "- Flag data quality issues (e.g., missing calls, short transcripts, stale data).\n\n"
    )

    return preamble + stage_block + scoring_rubric + output_format


def format_usage(usage) -> str:
    """Format the usage object, highlighting cache-related fields."""
    parts = [
        f"input_tokens={usage.input_tokens}",
        f"output_tokens={usage.output_tokens}",
    ]
    # Cache fields -- these only appear if caching is active
    cache_creation = getattr(usage, "cache_creation_input_tokens", None)
    cache_read = getattr(usage, "cache_read_input_tokens", None)

    if cache_creation is not None:
        parts.append(f"cache_creation_input_tokens={cache_creation}")
    if cache_read is not None:
        parts.append(f"cache_read_input_tokens={cache_read}")

    return ", ".join(parts)


def has_cache_fields(usage) -> bool:
    """Return True if usage contains any cache-related token counts."""
    cache_creation = getattr(usage, "cache_creation_input_tokens", None)
    cache_read = getattr(usage, "cache_read_input_tokens", None)
    return (cache_creation is not None and cache_creation > 0) or \
           (cache_read is not None and cache_read > 0)


# ---------------------------------------------------------------------------
# Client setup
# ---------------------------------------------------------------------------

client = anthropic.Anthropic(
    api_key=ANTHROPIC_API_KEY,
    base_url=ANTHROPIC_BASE_URL,
    timeout=120.0,
    max_retries=0,
)

LARGE_PREFIX = build_large_system_prefix()
prefix_char_count = len(LARGE_PREFIX)
prefix_est_tokens = prefix_char_count // 4

print("=" * 70)
print("Prompt Caching Test — Riskified LiteLLM Proxy")
print("=" * 70)
print(f"Model:          {MODEL_AGENTS_1_8}")
print(f"Proxy:          {ANTHROPIC_BASE_URL}")
print(f"SDK version:    {anthropic.__version__}")
print(f"System prefix:  ~{prefix_est_tokens:,} est. tokens ({prefix_char_count:,} chars)")
print()


# ---------------------------------------------------------------------------
# Test 1: First request — should trigger cache creation
# ---------------------------------------------------------------------------

print("TEST 1: Initial request with cache_control (expect cache_creation)")
print("-" * 70)

system_blocks_test1 = [
    {
        "type": "text",
        "text": LARGE_PREFIX,
        "cache_control": {"type": "ephemeral"},
    },
    {
        "type": "text",
        "text": "You are Agent 1: Stage Classifier. Analyze the transcript and classify the deal stage.",
    },
]

start = time.time()
caching_supported = False

try:
    response1 = client.messages.create(
        model=MODEL_AGENTS_1_8,
        max_tokens=150,
        system=system_blocks_test1,
        messages=[
            {
                "role": "user",
                "content": "Transcript: The customer said they want to start a POC next week. "
                           "They asked about pricing and mentioned their VP of Engineering approved the evaluation.",
            }
        ],
    )
    elapsed1 = time.time() - start

    print(f"  Response: {response1.content[0].text[:120]}...")
    print(f"  Usage: {format_usage(response1.usage)}")
    print(f"  Time: {elapsed1:.1f}s")
    print(f"  Stop reason: {response1.stop_reason}")

    if has_cache_fields(response1.usage):
        cache_creation = getattr(response1.usage, "cache_creation_input_tokens", 0) or 0
        print(f"  >> Cache creation tokens: {cache_creation}")
        print("  RESULT: CACHE FIELDS PRESENT -- proxy preserves cache_control")
        caching_supported = True
    else:
        print("  >> No cache fields in usage response.")
        print("  RESULT: CACHING NOT SUPPORTED through this proxy")
        print()
        print("=" * 70)
        print("CONCLUSION: The LiteLLM proxy strips cache_control headers or")
        print("Anthropic does not return cache fields for this model/config.")
        print("Skip prompt caching optimization for now.")
        print("=" * 70)

except Exception as e:
    elapsed1 = time.time() - start
    print(f"  FAILED ({elapsed1:.1f}s): {type(e).__name__}: {e}")
    print()
    print("Cannot proceed with remaining tests.")
    sys.exit(1)

print()


# ---------------------------------------------------------------------------
# Test 2: Second request — same prefix, different suffix (expect cache read)
# ---------------------------------------------------------------------------

if not caching_supported:
    print("TEST 2: SKIPPED (caching not supported)")
    print("TEST 3: SKIPPED (caching not supported)")
    sys.exit(0)

print("TEST 2: Second request — same prefix, different suffix (expect cache_read)")
print("-" * 70)

# Same cached prefix, different agent instruction suffix
system_blocks_test2 = [
    {
        "type": "text",
        "text": LARGE_PREFIX,
        "cache_control": {"type": "ephemeral"},
    },
    {
        "type": "text",
        "text": "You are Agent 2: Champion Identifier. Identify the champion from the transcript.",
    },
]

start = time.time()
try:
    response2 = client.messages.create(
        model=MODEL_AGENTS_1_8,
        max_tokens=150,
        system=system_blocks_test2,
        messages=[
            {
                "role": "user",
                "content": "Transcript: Sarah from engineering has been driving the evaluation internally. "
                           "She set up the technical review and shared our whitepaper with the security team.",
            }
        ],
    )
    elapsed2 = time.time() - start

    print(f"  Response: {response2.content[0].text[:120]}...")
    print(f"  Usage: {format_usage(response2.usage)}")
    print(f"  Time: {elapsed2:.1f}s")
    print(f"  Stop reason: {response2.stop_reason}")

    cache_read = getattr(response2.usage, "cache_read_input_tokens", 0) or 0
    if cache_read > 0:
        print(f"  >> Cache read tokens: {cache_read}")
        savings_pct = (cache_read / response2.usage.input_tokens * 100) if response2.usage.input_tokens > 0 else 0
        print(f"  >> Cache hit ratio: {savings_pct:.0f}% of input tokens served from cache")
        print(f"  >> Latency: {elapsed2:.1f}s (vs {elapsed1:.1f}s for initial request)")
        print("  RESULT: CACHE READ CONFIRMED -- prompt caching is working!")
    else:
        print("  >> cache_read_input_tokens = 0")
        print("  RESULT: Cache was created (Test 1) but not read (Test 2).")
        print("  Possible causes:")
        print("    - The proxy assigns different cache keys per request")
        print("    - The prefix was not identical at the byte level")
        print("    - The model variant does not support prefix caching")

except Exception as e:
    elapsed2 = time.time() - start
    print(f"  FAILED ({elapsed2:.1f}s): {type(e).__name__}: {e}")

print()


# ---------------------------------------------------------------------------
# Test 3: Streaming with cache (confirm compatibility)
# ---------------------------------------------------------------------------

print("TEST 3: Streaming with cached prefix")
print("-" * 70)

system_blocks_test3 = [
    {
        "type": "text",
        "text": LARGE_PREFIX,
        "cache_control": {"type": "ephemeral"},
    },
    {
        "type": "text",
        "text": "You are Agent 3: Momentum Tracker. Assess the deal momentum from the transcript.",
    },
]

start = time.time()
try:
    with client.messages.stream(
        model=MODEL_AGENTS_1_8,
        max_tokens=150,
        system=system_blocks_test3,
        messages=[
            {
                "role": "user",
                "content": "Transcript: We had three meetings this week. The customer responded same-day "
                           "to our follow-up and scheduled the security review for Monday.",
            }
        ],
    ) as stream:
        chunks = 0
        for text in stream.text_stream:
            chunks += 1
        message = stream.get_final_message()

    elapsed3 = time.time() - start

    print(f"  Response: {message.content[0].text[:120]}...")
    print(f"  Chunks: {chunks}")
    print(f"  Usage: {format_usage(message.usage)}")
    print(f"  Time: {elapsed3:.1f}s")
    print(f"  Stop reason: {message.stop_reason}")

    cache_read = getattr(message.usage, "cache_read_input_tokens", 0) or 0
    if cache_read > 0:
        print(f"  >> Cache read tokens: {cache_read}")
        print("  RESULT: STREAMING + CACHING WORKS")
    else:
        print("  >> No cache read tokens in streaming response")
        print("  RESULT: Streaming works but cache fields may not propagate via stream")

except Exception as e:
    elapsed3 = time.time() - start
    print(f"  FAILED ({elapsed3:.1f}s): {type(e).__name__}: {e}")


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

print()
print("=" * 70)
print("SUMMARY")
print("=" * 70)

if caching_supported:
    cache_read_t2 = getattr(response2.usage, "cache_read_input_tokens", 0) or 0
    if cache_read_t2 > 0:
        print("  Prompt caching is FULLY WORKING through the proxy.")
        print()
        print("  Cost implications (Sonnet pricing):")
        print("    - Cache write: 25% premium on first request")
        print("    - Cache read:  90% discount on subsequent requests")
        print("    - Break-even:  ~2 requests with same prefix")
        print()
        print("  Recommendation: Enable prompt caching for the shared system")
        print("  prefix across all 10 agents. Expected savings: ~60-80% of")
        print("  input token costs for agents 2-10 within a single analysis run.")
    else:
        print("  Cache creation works but cache reads returned 0 tokens.")
        print("  Further investigation needed before enabling in production.")
else:
    print("  Prompt caching is NOT SUPPORTED through the current proxy setup.")
    print("  Skip this optimization until the proxy is updated.")
