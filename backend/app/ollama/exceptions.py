"""Custom exceptions for Ollama client."""


class OllamaError(Exception):
    """Base Ollama error."""
    pass


class OllamaConnectionError(OllamaError):
    """Cannot reach Ollama server."""
    pass


class OllamaTimeoutError(OllamaError):
    """Request timed out."""
    pass


class OllamaModelError(OllamaError):
    """Model not found or failed to load."""
    pass
