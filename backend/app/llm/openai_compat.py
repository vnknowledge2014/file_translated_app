"""OpenAI-compatible LLM client for cloud providers.

Supports: OpenRouter, OpenAI, Google Gemini, Anthropic Claude, Ollama Cloud.
All use the /v1/chat/completions format (or close variant).

Usage:
    client = OpenAICompatClient(
        base_url="https://openrouter.ai/api/v1",
        api_key="sk-or-...",
    )
    response = await client.generate(model="google/gemma-2-9b-it", prompt="Hello")
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.llm.base import LLMClient

logger = logging.getLogger(__name__)


class OpenAICompatClient(LLMClient):
    """LLM client using OpenAI-compatible chat/completions API.

    Works with any provider exposing /chat/completions:
    - OpenAI (api.openai.com)
    - OpenRouter (openrouter.ai)
    - Google Gemini (generativelanguage.googleapis.com)
    - Anthropic Claude (api.anthropic.com)
    - Ollama Cloud (api.ollama.com)
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        timeout: float = 600.0,
        auth_header: str = "Authorization",
        extra_headers: dict[str, str] | None = None,
    ):
        """Initialize with provider base URL and API key.

        Args:
            base_url: Provider API base URL (e.g., "https://api.openai.com/v1").
            api_key: API key for authentication.
            timeout: HTTP request timeout in seconds.
            auth_header: Header name for auth. "Authorization" for most,
                         "x-api-key" for Anthropic.
            extra_headers: Additional headers (e.g., anthropic-version).
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.auth_header = auth_header
        self.extra_headers = extra_headers or {}
        self._client: httpx.AsyncClient | None = None

    def _build_headers(self) -> dict[str, str]:
        """Build request headers with auth and extras."""
        headers: dict[str, str] = {"Content-Type": "application/json"}

        if self.auth_header == "Authorization":
            headers["Authorization"] = f"Bearer {self.api_key}"
        else:
            headers[self.auth_header] = self.api_key

        headers.update(self.extra_headers)
        return headers

    async def _get_client(self) -> httpx.AsyncClient:
        """Lazy-init HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                headers=self._build_headers(),
            )
        return self._client

    async def generate(
        self,
        model: str,
        prompt: str,
        system: str | None = None,
        images: list[str] | None = None,
        temperature: float = 0.7,
        num_ctx: int = 8192,
        think: bool | None = None,
        top_k: int | None = None,
        top_p: float | None = None,
        repeat_penalty: float | None = None,
    ) -> str:
        """Generate text via /chat/completions.

        Maps Ollama parameters to OpenAI format:
        - temperature → temperature
        - top_p → top_p
        - repeat_penalty → frequency_penalty (0-2 scale)
        - num_ctx → max_tokens (capped output)
        - top_k → not supported by most providers, ignored
        - think → not supported on cloud, ignored
        """
        messages: list[dict[str, Any]] = []

        if system:
            messages.append({"role": "system", "content": system})

        # Handle vision (images) if provided
        if images:
            content: list[dict] = [{"type": "text", "text": prompt}]
            for img in images:
                content.append(
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{img}"},
                    }
                )
            messages.append({"role": "user", "content": content})
        else:
            messages.append({"role": "user", "content": prompt})

        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "stream": False,
        }

        if top_p is not None:
            payload["top_p"] = top_p

        if repeat_penalty is not None:
            # Map Ollama's repeat_penalty (typically 1.0-1.5) to
            # OpenAI's frequency_penalty (0.0-2.0)
            payload["frequency_penalty"] = max(0.0, min(2.0, repeat_penalty - 1.0))

        # Limit output tokens (use num_ctx as rough guide)
        payload["max_tokens"] = min(num_ctx, 4096)

        try:
            client = await self._get_client()
            url = f"{self.base_url}/chat/completions"
            response = await client.post(url, json=payload)

            if response.status_code == 404:
                raise RuntimeError(f"Model '{model}' not found on provider")

            if response.status_code == 401:
                raise RuntimeError("Invalid API key")

            if response.status_code == 429:
                raise RuntimeError("Rate limited by provider — try again later")

            response.raise_for_status()
            data = response.json()

            # Extract response text
            choices = data.get("choices", [])
            if not choices:
                logger.warning(f"Empty choices from provider: {data}")
                return ""

            message = choices[0].get("message", {})
            content_text = message.get("content", "")

            # Log usage if available
            usage = data.get("usage")
            if usage:
                logger.debug(
                    f"LLM usage: {usage.get('prompt_tokens', '?')} prompt + "
                    f"{usage.get('completion_tokens', '?')} completion tokens"
                )

            return content_text

        except httpx.ConnectError as e:
            raise RuntimeError(
                f"Cannot connect to LLM provider at {self.base_url}: {e}"
            ) from e
        except httpx.TimeoutException as e:
            raise RuntimeError(f"Request timed out after {self.timeout}s: {e}") from e
        except httpx.HTTPStatusError as e:
            raise RuntimeError(f"HTTP error from LLM provider: {e}") from e

    async def generate_embedding(self, model: str, prompt: str) -> list[float]:
        """Generate embedding via /embeddings endpoint.

        Falls back to empty list if provider doesn't support embeddings.
        """
        payload = {
            "model": model,
            "input": prompt,
        }
        try:
            client = await self._get_client()
            url = f"{self.base_url}/embeddings"
            response = await client.post(url, json=payload)

            if response.status_code in (404, 400):
                logger.debug("Embeddings not supported by this provider/model")
                return []

            response.raise_for_status()
            data = response.json()

            # OpenAI format: {"data": [{"embedding": [...]}]}
            emb_data = data.get("data", [])
            if emb_data:
                return emb_data[0].get("embedding", [])
            return []

        except Exception as e:
            logger.debug(f"Embedding generation failed (non-fatal): {e}")
            return []

    async def list_models(self) -> list[dict]:
        """List available models via /models endpoint."""
        try:
            client = await self._get_client()
            url = f"{self.base_url}/models"
            response = await client.get(url)

            if response.status_code in (404, 403):
                return [{"name": "unknown", "note": "models endpoint not available"}]

            response.raise_for_status()
            data = response.json()

            # OpenAI format: {"data": [{"id": "gpt-4o", ...}]}
            models = data.get("data", [])
            return [{"name": m.get("id", "unknown"), **m} for m in models]

        except Exception as e:
            logger.warning(f"Failed to list models: {e}")
            return []

    async def health_check(self) -> bool:
        """Check if provider is reachable."""
        try:
            client = await self._get_client()
            url = f"{self.base_url}/models"
            response = await client.get(url, timeout=5.0)
            return response.status_code in (200, 401)  # 401 = reachable but bad key
        except Exception:
            return False

    async def close(self) -> None:
        """Close HTTP client connection."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
