"""Quick test: Does streaming work through the Riskified LiteLLM proxy?"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "sis"))

import anthropic
from sis.config import ANTHROPIC_API_KEY, ANTHROPIC_BASE_URL, MODEL_AGENTS_1_8

client = anthropic.Anthropic(
    api_key=ANTHROPIC_API_KEY,
    base_url=ANTHROPIC_BASE_URL,
    timeout=120.0,
    max_retries=0,
)

print(f"Model: {MODEL_AGENTS_1_8}")
print(f"Proxy: {ANTHROPIC_BASE_URL}")
print()

# --- Test 1: Basic streaming ---
print("TEST 1: Basic streaming via client.messages.stream()")
print("-" * 50)
start = time.time()
try:
    with client.messages.stream(
        model=MODEL_AGENTS_1_8,
        max_tokens=200,
        system="You are a helpful assistant. Respond briefly.",
        messages=[{"role": "user", "content": "Say hello and count to 10."}],
    ) as stream:
        chunks = 0
        for text in stream.text_stream:
            chunks += 1
            if chunks <= 5:
                print(f"  chunk {chunks}: {text!r}")
        message = stream.get_final_message()

    elapsed = time.time() - start
    print(f"  ... {chunks} total chunks")
    print(f"  Tokens: {message.usage.input_tokens} in / {message.usage.output_tokens} out")
    print(f"  Time: {elapsed:.1f}s")
    print(f"  Stop reason: {message.stop_reason}")
    print("  RESULT: STREAMING WORKS")
except Exception as e:
    print(f"  FAILED: {type(e).__name__}: {e}")

print()

# --- Test 2: Structured outputs via output_config ---
print("TEST 2: Structured outputs via output_config.format")
print("-" * 50)
start = time.time()
try:
    response = client.messages.create(
        model=MODEL_AGENTS_1_8,
        max_tokens=200,
        messages=[{"role": "user", "content": "Extract: John Smith (john@example.com) wants the Enterprise plan."}],
        output_config={
            "format": {
                "type": "json_schema",
                "schema": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "email": {"type": "string"},
                        "plan": {"type": "string"},
                    },
                    "required": ["name", "email", "plan"],
                    "additionalProperties": False,
                },
            }
        },
    )
    elapsed = time.time() - start
    print(f"  Response: {response.content[0].text}")
    print(f"  Tokens: {response.usage.input_tokens} in / {response.usage.output_tokens} out")
    print(f"  Time: {elapsed:.1f}s")
    print(f"  Stop reason: {response.stop_reason}")
    print("  RESULT: STRUCTURED OUTPUTS WORK")
except Exception as e:
    elapsed = time.time() - start
    print(f"  FAILED ({elapsed:.1f}s): {type(e).__name__}: {e}")

print()

# --- Test 3: Streaming + Structured outputs combined ---
print("TEST 3: Streaming + Structured outputs COMBINED")
print("-" * 50)
start = time.time()
try:
    with client.messages.stream(
        model=MODEL_AGENTS_1_8,
        max_tokens=200,
        messages=[{"role": "user", "content": "Extract: Jane Doe (jane@corp.com) interested in Pro tier."}],
        output_config={
            "format": {
                "type": "json_schema",
                "schema": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "email": {"type": "string"},
                        "plan": {"type": "string"},
                    },
                    "required": ["name", "email", "plan"],
                    "additionalProperties": False,
                },
            }
        },
    ) as stream:
        message = stream.get_final_message()

    elapsed = time.time() - start
    print(f"  Response: {message.content[0].text}")
    print(f"  Tokens: {message.usage.input_tokens} in / {message.usage.output_tokens} out")
    print(f"  Time: {elapsed:.1f}s")
    print(f"  Stop reason: {message.stop_reason}")
    print("  RESULT: STREAMING + STRUCTURED OUTPUTS WORK")
except Exception as e:
    elapsed = time.time() - start
    print(f"  FAILED ({elapsed:.1f}s): {type(e).__name__}: {e}")
