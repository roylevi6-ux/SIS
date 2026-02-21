"""LLM client abstraction — singleton Anthropic client management.

Extracted from sis/agents/runner.py to centralize client lifecycle.
Provides both sync and async clients with shared configuration.
"""

from __future__ import annotations

import anthropic

from sis.config import ANTHROPIC_API_KEY, ANTHROPIC_BASE_URL


class LLMClient:
    """Singleton wrapper around sync + async Anthropic clients.

    Lazy-initializes clients on first access. Config sourced from sis.config.
    """

    _instance: LLMClient | None = None

    def __init__(self) -> None:
        self._sync_client: anthropic.Anthropic | None = None
        self._async_client: anthropic.AsyncAnthropic | None = None

    @classmethod
    def get_instance(cls) -> LLMClient:
        """Get or create the singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset the singleton (closes existing clients). Used in testing."""
        if cls._instance is not None:
            if cls._instance._sync_client is not None:
                cls._instance._sync_client.close()
            if cls._instance._async_client is not None:
                cls._instance._async_client.close()
            cls._instance = None

    @property
    def sync_client(self) -> anthropic.Anthropic:
        """Lazy-initialized sync Anthropic client."""
        if self._sync_client is None:
            self._sync_client = anthropic.Anthropic(
                api_key=ANTHROPIC_API_KEY,
                base_url=ANTHROPIC_BASE_URL,
                timeout=120.0,
                max_retries=0,
            )
        return self._sync_client

    @property
    def async_client(self) -> anthropic.AsyncAnthropic:
        """Lazy-initialized async Anthropic client."""
        if self._async_client is None:
            self._async_client = anthropic.AsyncAnthropic(
                api_key=ANTHROPIC_API_KEY,
                base_url=ANTHROPIC_BASE_URL,
                timeout=120.0,
                max_retries=0,
            )
        return self._async_client


def get_client() -> anthropic.Anthropic:
    """Drop-in replacement for runner.py's get_client()."""
    return LLMClient.get_instance().sync_client


def get_async_client() -> anthropic.AsyncAnthropic:
    """Drop-in replacement for runner.py's get_async_client()."""
    return LLMClient.get_instance().async_client
