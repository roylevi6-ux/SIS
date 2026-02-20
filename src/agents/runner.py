"""Agent runner — thin function that calls the LLM and parses structured output.

Per Technical Architecture: "Each agent is a module, not a class hierarchy.
An agent is: a prompt template, a Pydantic output model, and a thin runner function."

All 10 agents use this shared runner. It handles:
- LLM API calls via the Riskified proxy (streaming SSE to avoid 60s proxy timeout)
- Sync and async execution (async enables parallel Agents 2-8)
- Retry with exponential backoff (3 attempts)
- JSON extraction from LLM response (bracket-counting for nested objects)
- Pydantic validation of output
- Token/latency tracking via AgentResult wrapper
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from dataclasses import dataclass
from typing import Generic, TypeVar

import anthropic
from pydantic import BaseModel, ValidationError

from config import ANTHROPIC_API_KEY, ANTHROPIC_BASE_URL, MAX_OUTPUT_TOKENS_PER_AGENT, MODEL_AGENTS_1_8

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

# Shared clients (reused across agents for connection pooling)
_client: anthropic.Anthropic | None = None
_async_client: anthropic.AsyncAnthropic | None = None

# Semaphore to limit concurrent proxy requests (adjust if DevOps confirms higher limit)
DEFAULT_MAX_CONCURRENT = 7


def get_client() -> anthropic.Anthropic:
    """Get or create the shared Anthropic client with timeout."""
    global _client
    if _client is None:
        _client = anthropic.Anthropic(
            api_key=ANTHROPIC_API_KEY,
            base_url=ANTHROPIC_BASE_URL,
            timeout=120.0,
            max_retries=0,
        )
    return _client


def get_async_client() -> anthropic.AsyncAnthropic:
    """Get or create the shared async Anthropic client."""
    global _async_client
    if _async_client is None:
        _async_client = anthropic.AsyncAnthropic(
            api_key=ANTHROPIC_API_KEY,
            base_url=ANTHROPIC_BASE_URL,
            timeout=120.0,
            max_retries=0,
        )
    return _async_client


@dataclass
class AgentResult(Generic[T]):
    """Wrapper that pairs agent output with execution metadata."""

    output: T
    input_tokens: int
    output_tokens: int
    elapsed_seconds: float
    model: str
    attempts: int


def build_analysis_prompt(
    transcript_texts: list[str],
    stage_context: dict,
    timeline_entries: list[str] | None,
    instruction: str,
) -> str:
    """Build the shared user prompt used by Agents 2-8.

    All analysis agents receive the same context (timeline + stage + transcripts)
    and differ only in their final instruction line. Centralizing this avoids
    duplicating ~30 lines across 7 agent modules.
    """
    parts = []

    if timeline_entries:
        parts.append("## DEAL TIMELINE (all calls, chronological)")
        parts.append("\n\n".join(timeline_entries))
        parts.append("")

    parts.append("## STAGE CONTEXT (from Agent 1)")
    parts.append(f"Inferred stage: {stage_context.get('inferred_stage')} — {stage_context.get('stage_name')}")
    parts.append(f"Confidence: {stage_context.get('confidence')}")
    parts.append(f"Reasoning: {stage_context.get('reasoning')}")
    parts.append("")

    num_transcripts = len(transcript_texts)
    parts.append(f"## CALL TRANSCRIPTS ({num_transcripts} full transcripts)")
    for i, text in enumerate(transcript_texts, 1):
        parts.append(f"### Call {i} of {num_transcripts}")
        parts.append(text)
        parts.append("")

    parts.append(
        f"{instruction} "
        f"You are analyzing {num_transcripts} full transcripts. Respond with JSON only."
    )

    return "\n".join(parts)


def _enhance_system_prompt(system_prompt: str, output_model: type[BaseModel]) -> str:
    """Build enhanced system prompt with schema injection and conciseness rules."""
    raw_schema = output_model.model_json_schema()
    schema = json.dumps(_strip_schema_descriptions(raw_schema), indent=2)
    return (
        system_prompt
        + "\n\n## Required JSON Schema\n"
        "Your response MUST be a JSON object matching this exact schema. "
        "Use these EXACT field names.\n\n"
        "## CONCISENESS RULES (critical for latency)\n"
        "- narrative: MAX 300 words (2-4 paragraphs). Be analytical, not descriptive.\n"
        "- evidence interpretation: MAX 1 sentence each.\n"
        "- confidence rationale: MAX 2 sentences.\n"
        "- List fields (objections, risks, signals, stakeholders, etc.): "
        "Only the most significant items.\n"
        "- Do NOT pad with qualifiers, hedging, or restating what's obvious.\n"
        "- Every word must earn its place.\n\n"
        f"```json\n{schema}\n```"
    )


def _copy_data_quality_to_confidence(result: BaseModel) -> None:
    """Copy findings.data_quality_notes into confidence.data_gaps if both exist.

    The LLM populates data_quality_notes in findings only. This post-processing
    step merges them into confidence.data_gaps so downstream consumers get a
    unified view. Existing data_gaps from the LLM are preserved (deduped).
    """
    findings = getattr(result, "findings", None)
    confidence = getattr(result, "confidence", None)
    if findings is None or confidence is None:
        return
    notes = getattr(findings, "data_quality_notes", None)
    if not notes:
        return
    existing = set(confidence.data_gaps)
    for note in notes:
        if note not in existing:
            confidence.data_gaps.append(note)


def _process_response(
    agent_name: str,
    response,
    elapsed: float,
    output_model: type[T],
    model: str,
    attempt: int,
    max_output_tokens: int,
) -> AgentResult[T]:
    """Parse and validate an LLM response. Shared between sync/async runners."""
    raw_text = response.content[0].text
    tokens_in = response.usage.input_tokens
    tokens_out = response.usage.output_tokens
    stop_reason = response.stop_reason

    logger.info(
        "[%s] Response in %.1fs — %d in / %d out tokens (stop: %s)",
        agent_name, elapsed, tokens_in, tokens_out, stop_reason,
    )

    if stop_reason == "max_tokens":
        raise AgentError(
            f"Output truncated (hit {max_output_tokens} token limit). "
            "Response is likely incomplete JSON."
        )

    parsed_json = _extract_json(raw_text)
    if parsed_json is None:
        raise AgentError(f"No valid JSON found in response: {raw_text[:200]}...")

    result = output_model.model_validate(parsed_json)

    # Post-processing: copy findings.data_quality_notes -> confidence.data_gaps
    # (single source of truth: LLM writes to findings only, runner copies)
    _copy_data_quality_to_confidence(result)

    return AgentResult(
        output=result,
        input_tokens=tokens_in,
        output_tokens=tokens_out,
        elapsed_seconds=elapsed,
        model=model,
        attempts=attempt,
    )


# ── Sync runner (used for sequential agents: 1, 9, 10) ──────────────────


def run_agent(
    agent_name: str,
    system_prompt: str,
    user_prompt: str,
    output_model: type[T],
    model: str | None = None,
    max_output_tokens: int = MAX_OUTPUT_TOKENS_PER_AGENT,
    max_retries: int = 3,
) -> AgentResult[T]:
    """Run an agent synchronously: send prompt to LLM, parse structured output.

    Args:
        agent_name: Human-readable agent name for logging
        system_prompt: System message with agent identity and instructions
        user_prompt: User message with transcript data and context
        output_model: Pydantic model class to validate the JSON output against
        model: LLM model to use (defaults to config MODEL_AGENTS_1_8)
        max_output_tokens: Max tokens for LLM response
        max_retries: Number of retry attempts

    Returns:
        AgentResult wrapping the validated Pydantic model + execution metadata

    Raises:
        AgentError: If all retries exhausted
    """
    model = model or MODEL_AGENTS_1_8
    client = get_client()
    enhanced_system = _enhance_system_prompt(system_prompt, output_model)

    last_error = None
    current_user_prompt = user_prompt

    for attempt in range(1, max_retries + 1):
        try:
            logger.info("[%s] Attempt %d/%d (model=%s)", agent_name, attempt, max_retries, model)
            start = time.time()

            with client.messages.stream(
                model=model,
                max_tokens=max_output_tokens,
                system=enhanced_system,
                messages=[{"role": "user", "content": current_user_prompt}],
            ) as stream:
                response = stream.get_final_message()

            elapsed = time.time() - start
            return _process_response(
                agent_name, response, elapsed, output_model, model, attempt, max_output_tokens,
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


# ── Async runner (used for parallel agents: 2-8) ────────────────────────


async def run_agent_async(
    agent_name: str,
    system_prompt: str,
    user_prompt: str,
    output_model: type[T],
    model: str | None = None,
    max_output_tokens: int = MAX_OUTPUT_TOKENS_PER_AGENT,
    max_retries: int = 3,
) -> AgentResult[T]:
    """Run an agent asynchronously. Identical logic to run_agent, non-blocking I/O.

    Uses AsyncAnthropic with streaming SSE for proxy timeout avoidance.
    """
    model = model or MODEL_AGENTS_1_8
    client = get_async_client()
    enhanced_system = _enhance_system_prompt(system_prompt, output_model)

    last_error = None
    current_user_prompt = user_prompt

    for attempt in range(1, max_retries + 1):
        try:
            logger.info("[%s] Attempt %d/%d (model=%s)", agent_name, attempt, max_retries, model)
            start = time.time()

            async with client.messages.stream(
                model=model,
                max_tokens=max_output_tokens,
                system=enhanced_system,
                messages=[{"role": "user", "content": current_user_prompt}],
            ) as stream:
                response = await stream.get_final_message()

            elapsed = time.time() - start
            return _process_response(
                agent_name, response, elapsed, output_model, model, attempt, max_output_tokens,
            )

        except anthropic.RateLimitError as e:
            last_error = e
            wait = 2 ** attempt
            logger.warning("[%s] Rate limited, waiting %ds", agent_name, wait)
            await asyncio.sleep(wait)

        except (anthropic.APITimeoutError, anthropic.APIConnectionError) as e:
            last_error = e
            wait = 2 ** attempt
            logger.warning("[%s] API error: %s, retrying in %ds", agent_name, type(e).__name__, wait)
            await asyncio.sleep(wait)

        except ValidationError as e:
            last_error = e
            logger.warning("[%s] Output validation failed: %s", agent_name, e)
            if attempt < max_retries:
                current_user_prompt = (
                    user_prompt
                    + f"\n\n[RETRY — your previous response failed validation: {e}. "
                    "Please respond with valid JSON matching the required schema exactly.]"
                )
                await asyncio.sleep(1)

        except AgentError as e:
            last_error = e
            logger.warning("[%s] %s", agent_name, e)
            if attempt < max_retries:
                await asyncio.sleep(1)

    raise AgentError(f"[{agent_name}] Failed after {max_retries} attempts. Last error: {last_error}")


async def run_agents_parallel(
    tasks: list[dict],
    max_concurrent: int = DEFAULT_MAX_CONCURRENT,
) -> list[AgentResult | Exception]:
    """Run multiple agents concurrently with a concurrency semaphore.

    Args:
        tasks: List of dicts with keys matching run_agent_async params:
               {agent_name, system_prompt, user_prompt, output_model, model?, max_output_tokens?}
        max_concurrent: Max simultaneous proxy requests (default 7 for agents 2-8)

    Returns:
        List of AgentResult or Exception in same order as input tasks.
        Exceptions are returned (not raised) so one failure doesn't kill the batch.
    """
    semaphore = asyncio.Semaphore(max_concurrent)

    async def _safe_run(task: dict) -> AgentResult | Exception:
        async with semaphore:
            try:
                return await run_agent_async(**task)
            except Exception as e:
                return e

    results = await asyncio.gather(*[_safe_run(t) for t in tasks])
    return list(results)


# ── JSON extraction helpers ──────────────────────────────────────────────


def _extract_json(text: str) -> dict | None:
    """Extract JSON object from LLM response text.

    Handles common patterns:
    - Pure JSON response
    - JSON wrapped in ```json ... ``` code blocks
    - JSON embedded in prose (using bracket-counting for arbitrary nesting depth)
    """
    text = text.strip()

    if text.startswith("{"):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

    match = re.search(r"```(?:json)?\s*(\{.+\})\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    json_str = _find_json_object(text)
    if json_str:
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass

    return None


def _find_json_object(text: str) -> str | None:
    """Find the outermost JSON object using bracket counting."""
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


def _strip_schema_descriptions(schema: dict) -> dict:
    """Recursively strip 'description' and 'title' fields from a JSON schema."""
    if not isinstance(schema, dict):
        return schema
    result = {}
    for key, value in schema.items():
        if key in ("description", "title"):
            continue
        if isinstance(value, dict):
            result[key] = _strip_schema_descriptions(value)
        elif isinstance(value, list):
            result[key] = [
                _strip_schema_descriptions(item) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            result[key] = value
    return result


class AgentError(Exception):
    """Raised when an agent fails after all retries."""
