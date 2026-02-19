"""Agent runner — thin function that calls the LLM and parses structured output.

Per Technical Architecture: "Each agent is a module, not a class hierarchy.
An agent is: a prompt template, a Pydantic output model, and a thin runner function."

All 10 agents use this shared runner. It handles:
- LLM API calls via the Riskified proxy
- Retry with exponential backoff (3 attempts)
- JSON extraction from LLM response (bracket-counting for nested objects)
- Pydantic validation of output
- Token/latency tracking via AgentResult wrapper
"""

from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass
from typing import Generic, TypeVar

import anthropic
from pydantic import BaseModel, ValidationError

from config import ANTHROPIC_API_KEY, ANTHROPIC_BASE_URL, MAX_OUTPUT_TOKENS_PER_AGENT

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

# Shared client (reused across agents for connection pooling)
_client: anthropic.Anthropic | None = None


def get_client() -> anthropic.Anthropic:
    """Get or create the shared Anthropic client with timeout."""
    global _client
    if _client is None:
        _client = anthropic.Anthropic(
            api_key=ANTHROPIC_API_KEY,
            base_url=ANTHROPIC_BASE_URL,
            timeout=120.0,
        )
    return _client


@dataclass
class AgentResult(Generic[T]):
    """Wrapper that pairs agent output with execution metadata."""

    output: T
    input_tokens: int
    output_tokens: int
    elapsed_seconds: float
    model: str
    attempts: int


def run_agent(
    agent_name: str,
    system_prompt: str,
    user_prompt: str,
    output_model: type[T],
    model: str | None = None,
    max_output_tokens: int = MAX_OUTPUT_TOKENS_PER_AGENT,
    max_retries: int = 3,
) -> AgentResult[T]:
    """Run an agent: send prompt to LLM, parse and validate structured output.

    Args:
        agent_name: Human-readable agent name for logging
        system_prompt: System message with agent identity and instructions
        user_prompt: User message with transcript data and context
        output_model: Pydantic model class to validate the JSON output against
        model: LLM model to use (defaults to config MODEL_AGENTS_1_9)
        max_output_tokens: Max tokens for LLM response
        max_retries: Number of retry attempts

    Returns:
        AgentResult wrapping the validated Pydantic model + execution metadata

    Raises:
        AgentError: If all retries exhausted
    """
    from config import MODEL_AGENTS_1_9

    model = model or MODEL_AGENTS_1_9
    client = get_client()

    last_error = None
    current_user_prompt = user_prompt

    for attempt in range(1, max_retries + 1):
        try:
            logger.info("[%s] Attempt %d/%d (model=%s)", agent_name, attempt, max_retries, model)
            start = time.time()

            response = client.messages.create(
                model=model,
                max_tokens=max_output_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": current_user_prompt}],
            )

            elapsed = time.time() - start
            raw_text = response.content[0].text
            tokens_in = response.usage.input_tokens
            tokens_out = response.usage.output_tokens
            stop_reason = response.stop_reason

            logger.info(
                "[%s] Response in %.1fs — %d in / %d out tokens (stop: %s)",
                agent_name, elapsed, tokens_in, tokens_out, stop_reason,
            )

            # Check for truncated output
            if stop_reason == "max_tokens":
                raise AgentError(
                    f"Output truncated (hit {max_output_tokens} token limit). "
                    "Response is likely incomplete JSON."
                )

            # Parse JSON from response
            parsed_json = _extract_json(raw_text)
            if parsed_json is None:
                raise AgentError(f"No valid JSON found in response: {raw_text[:200]}...")

            # Validate against Pydantic model
            result = output_model.model_validate(parsed_json)
            return AgentResult(
                output=result,
                input_tokens=tokens_in,
                output_tokens=tokens_out,
                elapsed_seconds=elapsed,
                model=model,
                attempts=attempt,
            )

        except anthropic.RateLimitError as e:
            last_error = e
            wait = 2 ** attempt
            logger.warning("[%s] Rate limited, waiting %ds", agent_name, wait)
            time.sleep(wait)

        except (anthropic.APITimeoutError, anthropic.APIConnectionError) as e:
            last_error = e
            wait = 2 ** attempt
            logger.warning("[%s] API error: %s, retrying in %ds", agent_name, type(e).__name__, wait)
            time.sleep(wait)

        except ValidationError as e:
            last_error = e
            logger.warning("[%s] Output validation failed: %s", agent_name, e)
            if attempt < max_retries:
                # Smart retry: append correction hint so the model can fix its output
                current_user_prompt = (
                    user_prompt
                    + f"\n\n[RETRY — your previous response failed validation: {e}. "
                    "Please respond with valid JSON matching the required schema exactly.]"
                )
                time.sleep(1)

        except AgentError as e:
            last_error = e
            logger.warning("[%s] %s", agent_name, e)
            if attempt < max_retries:
                time.sleep(1)

    raise AgentError(f"[{agent_name}] Failed after {max_retries} attempts. Last error: {last_error}")


def _extract_json(text: str) -> dict | None:
    """Extract JSON object from LLM response text.

    Handles common patterns:
    - Pure JSON response
    - JSON wrapped in ```json ... ``` code blocks
    - JSON embedded in prose (using bracket-counting for arbitrary nesting depth)
    """
    text = text.strip()

    # Try direct parse first (most common — prompt asks for JSON only)
    if text.startswith("{"):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

    # Try extracting from code block
    match = re.search(r"```(?:json)?\s*(\{.+\})\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # Bracket-counting fallback for JSON embedded in prose
    json_str = _find_json_object(text)
    if json_str:
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass

    return None


def _find_json_object(text: str) -> str | None:
    """Find the outermost JSON object using bracket counting.

    Handles arbitrary nesting depth (arrays of objects, nested dicts, etc.)
    unlike regex which fails beyond one level.
    """
    start = text.find("{")
    if start == -1:
        return None

    depth = 0
    in_string = False
    escape = False

    for i in range(start, len(text)):
        ch = text[i]
        if escape:
            escape = False
            continue
        if ch == "\\" and in_string:
            escape = True
            continue
        if ch == '"' and not escape:
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]

    return None


class AgentError(Exception):
    """Raised when an agent fails after all retries."""
