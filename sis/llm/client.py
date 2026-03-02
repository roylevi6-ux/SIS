"""LLM client abstraction — singleton Anthropic client management.

Extracted from sis/agents/runner.py to centralize client lifecycle.
Provides both sync and async clients with shared configuration.

The sync client is a true singleton (thread-safe for httpx sync).
The async client is thread-local — each pipeline thread creates its own
event loop, and httpx async connections are bound to the loop they were
established on. Sharing an async client across threads with different
loops causes "Event loop is closed" errors.
"""

from __future__ import annotations

import threading

import anthropic

from sis.config import ANTHROPIC_API_KEY, ANTHROPIC_BASE_URL

# Thread-local storage for async clients — one per thread/event-loop.
_thread_local = threading.local()


class LLMClient:
    """Singleton wrapper around sync + async Anthropic clients.

    Lazy-initializes clients on first access. Config sourced from sis.config.
    The sync client is shared across threads (singleton).
    The async client is per-thread (thread-local) to avoid event loop conflicts.
    """

    _instance: LLMClient | None = None

    def __init__(self) -> None:
        self._sync_client: anthropic.Anthropic | None = None

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
            cls._instance = None
        # Also clear thread-local async client for current thread
        _thread_local.__dict__.pop("async_client", None)

    @classmethod
    def discard_async_client(cls) -> None:
        """Discard this thread's async client so a fresh one is created.

        Called before each pipeline run because each run creates a new event
        loop. The old AsyncAnthropic's httpx connection pool is bound to the
        previous (now-closed) loop and would raise "Event loop is closed".
        """
        _thread_local.__dict__.pop("async_client", None)

    @property
    def sync_client(self) -> anthropic.Anthropic:
        """Lazy-initialized sync Anthropic client (shared singleton)."""
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
        """Lazy-initialized async Anthropic client (per-thread)."""
        client = getattr(_thread_local, "async_client", None)
        if client is None:
            client = anthropic.AsyncAnthropic(
                api_key=ANTHROPIC_API_KEY,
                base_url=ANTHROPIC_BASE_URL,
                timeout=120.0,
                max_retries=0,
            )
            _thread_local.async_client = client
        return client


def get_client() -> anthropic.Anthropic:
    """Drop-in replacement for runner.py's get_client()."""
    return LLMClient.get_instance().sync_client


def get_async_client() -> anthropic.AsyncAnthropic:
    """Drop-in replacement for runner.py's get_async_client()."""
    return LLMClient.get_instance().async_client
