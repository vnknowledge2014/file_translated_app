"""Application configuration loaded from environment variables."""

import os


class Settings:
    """Application settings from environment variables with defaults.

    All settings have sensible defaults for Docker deployment.
    Override via environment variables.
    """

    def __init__(self):
        self.OLLAMA_URL: str = os.environ.get("OLLAMA_URL", "http://ollama:11434")
        self.MODEL: str = os.environ.get("MODEL", "gemma4:e4b")
        self.DATABASE_URL: str = os.environ.get(
            "DATABASE_URL", "sqlite:///data/db/translations.db"
        )
        self.UPLOAD_DIR: str = os.environ.get("UPLOAD_DIR", "/data/uploads")
        self.OUTPUT_DIR: str = os.environ.get("OUTPUT_DIR", "/data/output")
        self.TEMP_DIR: str = os.environ.get("TEMP_DIR", "/data/temp")
        self.MAX_WORKERS: int = int(os.environ.get("MAX_WORKERS", "1"))
        self.MAX_CONCURRENT_BATCHES: int = int(
            os.environ.get("MAX_CONCURRENT_BATCHES", "2")
        )
        self.OLLAMA_TIMEOUT: float = float(
            os.environ.get("OLLAMA_TIMEOUT", "1800")
        )

        self.SUPPORTED_TYPES: set[str] = {
            "docx", "xlsx", "pptx", "pdf", "md", "txt", "csv"
        }


# Singleton instance
settings = Settings()
