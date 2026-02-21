"""Retry logic — configurable retry with exponential backoff per Technical Architecture Section 3.3.

Wraps agent execution with retry logic:
- Configurable max retries per agent tier (Haiku: 3, Sonnet: 2, Opus: 1)
- Exponential backoff with jitter
- Distinct handling for retryable vs non-retryable errors
"""

from __future__ import annotations

import asyncio
import logging
import random
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


# Retryable error indicators (substrings in error messages)
RETRYABLE_ERRORS = [
    "overloaded",
    "rate_limit",
    "timeout",
    "529",
    "503",
    "500",
    "connection",
    "temporary",
]

# Non-retryable errors (always fail immediately)
NON_RETRYABLE_ERRORS = [
    "invalid_api_key",
    "authentication",
    "permission",
    "invalid_request",
    "context_length",
]


@dataclass
class RetryConfig:
    """Per-agent retry configuration."""

    max_retries: int = 2
    base_delay_seconds: float = 1.0
    max_delay_seconds: float = 30.0
    backoff_factor: float = 2.0
    jitter: bool = True


# Default configs by model tier
TIER_CONFIGS: dict[str, RetryConfig] = {
    "haiku": RetryConfig(max_retries=3, base_delay_seconds=0.5),
    "sonnet": RetryConfig(max_retries=2, base_delay_seconds=1.0),
    "opus": RetryConfig(max_retries=1, base_delay_seconds=2.0),
}


def get_retry_config(model: str) -> RetryConfig:
    """Get retry config based on model name."""
    model_lower = model.lower()
    if "haiku" in model_lower:
        return TIER_CONFIGS["haiku"]
    if "opus" in model_lower:
        return TIER_CONFIGS["opus"]
    return TIER_CONFIGS["sonnet"]


def is_retryable(error: Exception) -> bool:
    """Determine if an error is worth retrying."""
    error_str = str(error).lower()

    for pattern in NON_RETRYABLE_ERRORS:
        if pattern in error_str:
            return False

    for pattern in RETRYABLE_ERRORS:
        if pattern in error_str:
            return True

    # Default: retry unknown errors once
    return True


def compute_delay(attempt: int, config: RetryConfig) -> float:
    """Compute backoff delay for a given attempt number."""
    delay = config.base_delay_seconds * (config.backoff_factor ** attempt)
    delay = min(delay, config.max_delay_seconds)

    if config.jitter:
        delay = delay * (0.5 + random.random())

    return delay


async def retry_async(coro_factory, config: RetryConfig | None = None, agent_id: str = ""):
    """Execute an async callable with retry logic.

    Args:
        coro_factory: Callable that returns a coroutine (called fresh each attempt).
        config: Retry configuration. Uses default sonnet config if None.
        agent_id: Agent identifier for logging.

    Returns:
        The result of the coroutine on success.

    Raises:
        The last exception if all retries are exhausted.
    """
    if config is None:
        config = TIER_CONFIGS["sonnet"]

    last_error = None
    for attempt in range(config.max_retries + 1):
        try:
            return await coro_factory()
        except Exception as e:
            last_error = e
            if attempt >= config.max_retries:
                logger.error(
                    "[%s] All %d retries exhausted: %s",
                    agent_id, config.max_retries + 1, e,
                )
                raise

            if not is_retryable(e):
                logger.error("[%s] Non-retryable error: %s", agent_id, e)
                raise

            delay = compute_delay(attempt, config)
            logger.warning(
                "[%s] Attempt %d/%d failed: %s. Retrying in %.1fs",
                agent_id, attempt + 1, config.max_retries + 1, e, delay,
            )
            await asyncio.sleep(delay)

    raise last_error  # Should never reach here
