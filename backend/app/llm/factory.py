"""Factory for creating LLM client instances based on backend configuration.

Supports 6 backends:
    ollama         → Local Ollama (default, air-gapped)
    ollama-cloud   → Ollama Cloud API
    openrouter     → OpenRouter gateway (100+ models)
    openai         → OpenAI direct
    google         → Google Gemini
    anthropic      → Anthropic Claude

Usage:
    from app.llm.factory import create_llm_client
    client = create_llm_client()
"""

from __future__ import annotations

import logging

from app.config import settings
from app.llm.base import LLMClient

logger = logging.getLogger(__name__)

# Provider base URLs
_PROVIDER_URLS = {
    "ollama-cloud": "https://api.ollama.com/v1",
    "openrouter": "https://openrouter.ai/api/v1",
    "openai": "https://api.openai.com/v1",
    "google": "https://generativelanguage.googleapis.com/v1beta/openai",
    "anthropic": "https://api.anthropic.com/v1",
}


def create_llm_client(
    url: str | None = None,
    timeout: float | None = None,
) -> LLMClient:
    """Create an LLM client based on LLM_BACKEND setting.

    Args:
        url: Override base URL (used for Ollama local).
        timeout: HTTP request timeout in seconds.

    Returns:
        LLMClient instance for the configured backend.
    """
    backend = settings.LLM_BACKEND
    _timeout = timeout or settings.OLLAMA_TIMEOUT

    # ── Ollama Local (default) ──
    if backend == "ollama":
        from app.ollama.client import OllamaClient

        _url = url or settings.OLLAMA_URL
        logger.info(f"LLM backend: Ollama (local) at {_url}")
        return OllamaClient(base_url=_url, timeout=_timeout)

    # ── Cloud Providers (OpenAI-compatible API) ──
    from app.llm.openai_compat import OpenAICompatClient

    # Resolve provider config
    provider_config = {
        "ollama-cloud": {
            "base_url": _PROVIDER_URLS["ollama-cloud"],
            "api_key": settings.OLLAMA_API_KEY,
        },
        "openrouter": {
            "base_url": _PROVIDER_URLS["openrouter"],
            "api_key": settings.OPENROUTER_API_KEY,
            "extra_headers": {
                "HTTP-Referer": "https://infitrans.app",
                "X-Title": "InfiTrans",
            },
        },
        "openai": {
            "base_url": _PROVIDER_URLS["openai"],
            "api_key": settings.OPENAI_API_KEY,
        },
        "google": {
            "base_url": _PROVIDER_URLS["google"],
            "api_key": settings.GOOGLE_API_KEY,
        },
        "anthropic": {
            "base_url": _PROVIDER_URLS["anthropic"],
            "api_key": settings.ANTHROPIC_API_KEY,
            "auth_header": "x-api-key",
            "extra_headers": {"anthropic-version": "2023-06-01"},
        },
    }

    if backend not in provider_config:
        raise ValueError(
            f"Unknown LLM_BACKEND: '{backend}'. "
            f"Valid options: ollama, {', '.join(provider_config.keys())}"
        )

    config = provider_config[backend]
    if not config.get("api_key"):
        raise ValueError(
            f"LLM_BACKEND='{backend}' requires an API key. "
            f"Set the corresponding env var (e.g., OPENROUTER_API_KEY)."
        )

    logger.info(f"LLM backend: {backend} at {config['base_url']}")
    return OpenAICompatClient(
        base_url=config["base_url"],
        api_key=config["api_key"],
        timeout=_timeout,
        auth_header=config.get("auth_header", "Authorization"),
        extra_headers=config.get("extra_headers"),
    )
