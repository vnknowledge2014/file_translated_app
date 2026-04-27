"""Factory for creating LLM client instances based on backend configuration.

Usage:
    from app.llm.factory import create_llm_client
    client = create_llm_client("llamacpp", "http://localhost:8080", timeout=600)
"""

from __future__ import annotations

import logging

from app.llm.base import LLMClient

logger = logging.getLogger(__name__)


def create_llm_client(
    url: str = "http://localhost:11434",
    timeout: float = 600.0,
) -> LLMClient:
    """Create an LLM client for Ollama.

    Args:
        url: Base URL for the backend server.
        timeout: HTTP request timeout in seconds.

    Returns:
        An OllamaClient instance.
    """
    from app.ollama.client import OllamaClient

    logger.info(f"Using Ollama backend at {url}")
    return OllamaClient(base_url=url, timeout=timeout)
