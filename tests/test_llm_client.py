"""Test LLM client — singleton, reset, lazy initialization."""

from unittest.mock import patch, MagicMock

from sis.llm.client import LLMClient, get_client, get_async_client


class TestLLMClient:
    def setup_method(self):
        """Reset singleton before each test."""
        LLMClient.reset()

    def teardown_method(self):
        """Clean up singleton after each test."""
        LLMClient.reset()

    def test_singleton_instance(self):
        instance1 = LLMClient.get_instance()
        instance2 = LLMClient.get_instance()
        assert instance1 is instance2

    def test_reset_clears_instance(self):
        instance1 = LLMClient.get_instance()
        LLMClient.reset()
        instance2 = LLMClient.get_instance()
        assert instance1 is not instance2

    @patch("sis.llm.client.anthropic.Anthropic")
    def test_sync_client_lazy_init(self, mock_anthropic):
        mock_anthropic.return_value = MagicMock()
        instance = LLMClient.get_instance()

        # Not created yet
        assert instance._sync_client is None

        # First access creates it
        client = instance.sync_client
        assert client is not None
        mock_anthropic.assert_called_once()

        # Second access reuses
        client2 = instance.sync_client
        assert client is client2
        assert mock_anthropic.call_count == 1

    @patch("sis.llm.client.anthropic.AsyncAnthropic")
    def test_async_client_lazy_init(self, mock_async_anthropic):
        mock_async_anthropic.return_value = MagicMock()
        instance = LLMClient.get_instance()

        # Async client is thread-local, not an instance attribute
        from sis.llm.client import _thread_local
        assert getattr(_thread_local, "async_client", None) is None
        client = instance.async_client
        assert client is not None
        mock_async_anthropic.assert_called_once()

    @patch("sis.llm.client.anthropic.Anthropic")
    def test_get_client_module_function(self, mock_anthropic):
        mock_anthropic.return_value = MagicMock()
        client = get_client()
        assert client is not None

    @patch("sis.llm.client.anthropic.AsyncAnthropic")
    def test_get_async_client_module_function(self, mock_async_anthropic):
        mock_async_anthropic.return_value = MagicMock()
        client = get_async_client()
        assert client is not None
