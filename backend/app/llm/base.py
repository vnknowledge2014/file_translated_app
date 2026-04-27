"""Abstract base class for LLM clients.

Defines the interface that all LLM backends (Ollama, llama.cpp, etc.) must implement.
Downstream code (Translator, ModelManager) depends ONLY on this interface.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class LLMClient(ABC):
    """Abstract LLM client interface.

    All LLM backends must implement generate(), list_models(),
    health_check(), and close().
    """

    @abstractmethod
    async def generate(
        self,
        model: str,
        prompt: str,
        system: str | None = None,
        images: list[str] | None = None,
        temperature: float = 0.3,
        num_ctx: int = 8192,
    ) -> str:
        """Generate text completion.

        Args:
            model: Model name/identifier.
            prompt: User prompt.
            system: Optional system prompt.
            images: Optional list of base64-encoded images.
            temperature: Sampling temperature.
            num_ctx: Context window size.

        """
        ...

    @abstractmethod
    async def generate_embedding(self, model: str, prompt: str) -> list[float]:
        """Generate vector embedding for text.
        
        Args:
            model: Embedding model name.
            prompt: Text to embed.
            
        Returns:
            List of floats.
        """
        ...

    @abstractmethod
    async def list_models(self) -> list[dict]:
        """List available models.

        Returns:
            List of model info dicts.
        """
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the backend is reachable.

        Returns:
            True if reachable, False otherwise.
        """
        ...

    @abstractmethod
    async def close(self) -> None:
        """Close HTTP client connection."""
        ...
