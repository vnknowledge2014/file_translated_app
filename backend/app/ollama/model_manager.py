"""Model loading/unloading manager for 16GB RAM constraint."""

from __future__ import annotations

import logging

from app.ollama.client import OllamaClient

logger = logging.getLogger(__name__)


class ModelManager:
    """Manage model loading on Ollama.

    Track currently loaded model. If same model requested → no-op.
    On first use, warm the model with a minimal generate request.
    """

    def __init__(self, client: OllamaClient):
        """Initialize with OllamaClient.

        Args:
            client: Async Ollama API client.
        """
        self.client = client
        self.current_model: str | None = None
        self._load_count: int = 0

    async def ensure_model(self, model_name: str) -> None:
        """Ensure model is loaded and ready.

        If model is already loaded, this is a no-op.
        If a different model is loaded, triggers a model swap
        (Ollama handles unloading automatically with MAX_LOADED_MODELS=1).

        Args:
            model_name: Model identifier (e.g., "gemma4:e4b").
        """
        if self.current_model == model_name:
            logger.debug(f"Model {model_name} already loaded, skipping")
            return

        logger.info(f"Loading model: {model_name} (was: {self.current_model})")

        # Warm the model by sending a minimal generate request
        # Ollama will auto-unload the previous model if MAX_LOADED_MODELS=1
        await self.client.generate(
            model=model_name,
            prompt="hi",
            num_ctx=128,
        )

        self.current_model = model_name
        self._load_count += 1
        logger.info(f"Model {model_name} loaded (total loads: {self._load_count})")

    async def get_current_model(self) -> str | None:
        """Return currently loaded model name."""
        return self.current_model
