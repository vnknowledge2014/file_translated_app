"""Tests for app.ollama.client — Async HTTP client for Ollama API."""

import json

import httpx
import pytest

from app.ollama.client import OllamaClient
from app.ollama.exceptions import OllamaConnectionError, OllamaModelError


@pytest.fixture
def mock_transport():
    """Create mock HTTP transport for testing."""

    class MockTransport(httpx.AsyncBaseTransport):
        def __init__(self):
            self.requests: list[httpx.Request] = []
            self.responses: dict[str, tuple[int, dict]] = {}

        def set_response(self, method: str, path: str, status: int, data: dict):
            self.responses[f"{method}:{path}"] = (status, data)

        async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
            self.requests.append(request)
            key = f"{request.method}:{request.url.raw_path.decode()}"
            if key in self.responses:
                status, data = self.responses[key]
                return httpx.Response(status, json=data)
            return httpx.Response(404, json={"error": "not found"})

    return MockTransport()


@pytest.mark.asyncio
class TestOllamaClient:
    """Feature: Async HTTP client for Ollama API."""

    async def test_generate_text(self, mock_transport):
        """Scenario: Generate text completion."""
        mock_transport.set_response("POST", "/api/generate", 200, {"response": "translated text"})
        client = OllamaClient.__new__(OllamaClient)
        client.base_url = "http://mock:11434"
        client.timeout = 120.0
        client._client = httpx.AsyncClient(transport=mock_transport, base_url="http://mock:11434")

        result = await client.generate("gemma4:e4b", "translate this")
        assert result == "translated text"
        await client.close()

    async def test_generate_with_system_prompt(self, mock_transport):
        """Scenario: Pass system prompt to generate."""
        mock_transport.set_response("POST", "/api/generate", 200, {"response": "ok"})
        client = OllamaClient.__new__(OllamaClient)
        client.base_url = "http://mock:11434"
        client.timeout = 120.0
        client._client = httpx.AsyncClient(transport=mock_transport, base_url="http://mock:11434")

        result = await client.generate("model", "user prompt", system="system prompt")
        assert result == "ok"

        # Verify system prompt was sent
        body = json.loads(mock_transport.requests[0].content)
        assert body["system"] == "system prompt"
        await client.close()

    async def test_generate_with_images(self, mock_transport):
        """Scenario: Vision mode with base64 images."""
        mock_transport.set_response("POST", "/api/generate", 200, {"response": "image desc"})
        client = OllamaClient.__new__(OllamaClient)
        client.base_url = "http://mock:11434"
        client.timeout = 120.0
        client._client = httpx.AsyncClient(transport=mock_transport, base_url="http://mock:11434")

        result = await client.generate("model", "describe", images=["base64data"])
        assert result == "image desc"

        body = json.loads(mock_transport.requests[0].content)
        assert body["images"] == ["base64data"]
        await client.close()

    async def test_list_models(self, mock_transport):
        """Scenario: List available models."""
        mock_transport.set_response("GET", "/api/tags", 200, {
            "models": [{"name": "gemma4:e4b"}, {"name": "translategemma:4b"}]
        })
        client = OllamaClient.__new__(OllamaClient)
        client.base_url = "http://mock:11434"
        client.timeout = 120.0
        client._client = httpx.AsyncClient(transport=mock_transport, base_url="http://mock:11434")

        models = await client.list_models()
        assert len(models) == 2
        assert models[0]["name"] == "gemma4:e4b"
        await client.close()

    async def test_health_check_success(self, mock_transport):
        """Scenario: Ollama reachable → True."""
        mock_transport.set_response("GET", "/api/tags", 200, {"models": []})
        client = OllamaClient.__new__(OllamaClient)
        client.base_url = "http://mock:11434"
        client.timeout = 120.0
        client._client = httpx.AsyncClient(transport=mock_transport, base_url="http://mock:11434")

        assert await client.health_check() is True
        await client.close()

    async def test_connection_error(self):
        """Scenario: Ollama unreachable → OllamaConnectionError."""
        client = OllamaClient("http://127.0.0.1:59999", timeout=1.0)
        with pytest.raises(OllamaConnectionError):
            await client.generate("model", "prompt")
        await client.close()
