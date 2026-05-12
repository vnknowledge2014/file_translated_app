"""Async HTTP client for Ollama REST API."""

from __future__ import annotations

import httpx

from app.ollama.exceptions import (
    OllamaConnectionError,
    OllamaError,
    OllamaModelError,
    OllamaTimeoutError,
)

from app.llm.base import LLMClient


class OllamaClient(LLMClient):
    """Async HTTP client for Ollama API.

    Supports text generation (including vision mode), model listing,
    and health checks.
    """

    def __init__(self, base_url: str, timeout: float = 600.0):
        """Initialize with Ollama base URL.

        Args:
            base_url: Ollama API base URL (e.g., "http://ollama:11434").
            timeout: HTTP request timeout in seconds.
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Lazy-init HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(self.timeout),
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
        """Generate text completion.

        Args:
            model: Model name (e.g., "gemma4:e4b").
            prompt: User prompt.
            system: Optional system prompt.
            images: Optional list of base64-encoded images (vision mode).
            temperature: Sampling temperature.
            num_ctx: Context window size.
            top_k: Top-K sampling parameter.
            top_p: Top-P (nucleus) sampling parameter.
            repeat_penalty: Repetition penalty factor.

        Returns:
            Generated text response.

        Raises:
            OllamaConnectionError: Cannot reach Ollama.
            OllamaTimeoutError: Request timed out.
            OllamaModelError: Model not found.
        """
        options: dict = {
            "temperature": temperature,
            "num_ctx": num_ctx,
        }
        if top_k is not None:
            options["top_k"] = top_k
        if top_p is not None:
            options["top_p"] = top_p
        if repeat_penalty is not None:
            options["repeat_penalty"] = repeat_penalty

        payload: dict = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": options,
        }
        if think is not None:
            payload["think"] = think
        if system:
            payload["system"] = system
        if images:
            payload["images"] = images

        try:
            client = await self._get_client()
            response = await client.post("/api/generate", json=payload)

            if response.status_code == 404:
                raise OllamaModelError(f"Model '{model}' not found")

            response.raise_for_status()
            data = response.json()
            return data.get("response", "")

        except httpx.ConnectError as e:
            raise OllamaConnectionError(
                f"Cannot connect to Ollama at {self.base_url}: {e}"
            ) from e
        except httpx.TimeoutException as e:
            raise OllamaTimeoutError(
                f"Request timed out after {self.timeout}s: {e}"
            ) from e
        except httpx.HTTPStatusError as e:
            raise OllamaError(f"HTTP error: {e}") from e

    async def generate_embedding(self, model: str, prompt: str) -> list[float]:
        """Generate vector embedding for text.

        Args:
            model: Embedding model name.
            prompt: Text to embed.

        Returns:
            List of floats.
        """
        payload = {
            "model": model,
            "prompt": prompt,
        }
        try:
            client = await self._get_client()
            response = await client.post("/api/embeddings", json=payload)
            if response.status_code == 404:
                raise OllamaModelError(f"Model '{model}' not found")
            response.raise_for_status()
            data = response.json()
            return data.get("embedding", [])
        except httpx.ConnectError as e:
            raise OllamaConnectionError(
                f"Cannot connect to Ollama at {self.base_url}: {e}"
            ) from e
        except httpx.TimeoutException as e:
            raise OllamaTimeoutError(
                f"Request timed out after {self.timeout}s: {e}"
            ) from e
        except httpx.HTTPStatusError as e:
            raise OllamaError(f"HTTP error: {e}") from e

    async def list_models(self) -> list[dict]:
        """List available models.

        Returns:
            List of model info dicts with 'name', 'size', etc.

        Raises:
            OllamaConnectionError: Cannot reach Ollama.
        """
        try:
            client = await self._get_client()
            response = await client.get("/api/tags")
            response.raise_for_status()
            data = response.json()
            return data.get("models", [])
        except httpx.ConnectError as e:
            raise OllamaConnectionError(
                f"Cannot connect to Ollama at {self.base_url}: {e}"
            ) from e

    async def health_check(self) -> bool:
        """Check if Ollama is reachable.

        Returns:
            True if reachable, False otherwise.
        """
        try:
            client = await self._get_client()
            response = await client.get("/api/tags")
            return response.status_code == 200
        except (httpx.ConnectError, httpx.TimeoutException):
            return False

    async def close(self):
        """Close HTTP client connection."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
