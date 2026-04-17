"""Tests for app.ollama.model_manager — Model switching."""

from unittest.mock import AsyncMock

import pytest

from app.ollama.model_manager import ModelManager


@pytest.fixture
def mock_ollama_client():
    """Mock OllamaClient for unit testing."""
    client = AsyncMock()
    client.generate = AsyncMock(return_value="ok")
    client.list_models = AsyncMock(return_value=[
        {"name": "gemma4:e4b"},
        {"name": "translategemma:4b"},
    ])
    return client


@pytest.mark.asyncio
class TestModelManager:
    """Feature: Switch between gemma4 and translategemma models."""

    async def test_ensure_model_loaded(self, mock_ollama_client):
        """Scenario: Request model → loads if not loaded."""
        mgr = ModelManager(mock_ollama_client)
        await mgr.ensure_model("gemma4:e4b")
        assert mgr.current_model == "gemma4:e4b"
        # Verify generate was called (warm-up request)
        mock_ollama_client.generate.assert_called_once()

    async def test_no_reload_if_same(self, mock_ollama_client):
        """Scenario: Same model requested → no reload."""
        mgr = ModelManager(mock_ollama_client)
        await mgr.ensure_model("gemma4:e4b")
        assert mock_ollama_client.generate.call_count == 1
        await mgr.ensure_model("gemma4:e4b")
        # Should not have called generate again
        assert mock_ollama_client.generate.call_count == 1

    async def test_switch_model(self, mock_ollama_client):
        """Scenario: Different model → swap."""
        mgr = ModelManager(mock_ollama_client)
        await mgr.ensure_model("gemma4:e4b")
        assert mgr.current_model == "gemma4:e4b"
        await mgr.ensure_model("translategemma:4b")
        assert mgr.current_model == "translategemma:4b"
        assert mock_ollama_client.generate.call_count == 2

    async def test_get_current_model_initially_none(self, mock_ollama_client):
        """Scenario: Fresh manager → None."""
        mgr = ModelManager(mock_ollama_client)
        assert await mgr.get_current_model() is None

    async def test_get_current_model_after_load(self, mock_ollama_client):
        """Scenario: After loading → returns model name."""
        mgr = ModelManager(mock_ollama_client)
        await mgr.ensure_model("translategemma:4b")
        assert await mgr.get_current_model() == "translategemma:4b"
