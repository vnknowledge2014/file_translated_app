"""LLM client abstraction layer.

Provides a unified interface for multiple LLM backends:
- Ollama (cloud/remote)
- llama.cpp (local optimized)
"""

from app.llm.base import LLMClient
from app.llm.factory import create_llm_client

__all__ = [
    "LLMClient",
    "create_llm_client",
]
