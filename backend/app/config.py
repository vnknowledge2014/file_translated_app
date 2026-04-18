"""Application configuration loaded from .env file and environment variables.

Priority: environment variables > .env file > defaults.
No external dependencies (no python-dotenv needed).
"""

import os


def _load_dotenv() -> None:
    """Load .env file into os.environ if it exists.

    Walks up from this file's directory to find .env at the project root.
    Only sets variables that are NOT already in os.environ
    (real env vars take priority over .env values).

    Supported syntax:
        KEY=value
        KEY="value with spaces"
        KEY='value with spaces'
        # comments and blank lines are ignored
    """
    # Walk up to find .env (max 5 levels: config.py → app → backend → project)
    search = os.path.dirname(os.path.abspath(__file__))
    for _ in range(5):
        env_path = os.path.join(search, ".env")
        if os.path.isfile(env_path):
            break
        search = os.path.dirname(search)
    else:
        return  # No .env found

    if not os.path.isfile(env_path):
        return

    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip()
            # Strip surrounding quotes
            if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
                value = value[1:-1]
            # Don't override existing env vars
            if key not in os.environ:
                os.environ[key] = value


# Load .env BEFORE creating Settings
_load_dotenv()


def _env(key: str, default: str) -> str:
    """Get env var with default."""
    return os.environ.get(key, default)


def _env_int(key: str, default: int) -> int:
    """Get env var as int with default."""
    return int(os.environ.get(key, str(default)))


def _env_float(key: str, default: float) -> float:
    """Get env var as float with default."""
    return float(os.environ.get(key, str(default)))


class Settings:
    """Application settings from .env file and environment variables.

    All settings have sensible defaults for Docker deployment.
    Override via .env file or environment variables.
    """

    def __init__(self):
        # ── Ollama Connection ──
        self.OLLAMA_URL: str = _env("OLLAMA_URL", "http://ollama:11434")
        self.OLLAMA_TIMEOUT: float = _env_float("OLLAMA_TIMEOUT", 1800)

        # ── Model ──
        self.MODEL: str = _env("MODEL", "gemma4:e4b")

        # ── Translation Parameters ──
        self.TRANSLATION_TEMPERATURE: float = _env_float(
            "TRANSLATION_TEMPERATURE", 0.3
        )
        self.TRANSLATION_NUM_CTX: int = _env_int("TRANSLATION_NUM_CTX", 4096)
        self.TRANSLATION_MAX_RETRIES: int = _env_int(
            "TRANSLATION_MAX_RETRIES", 3
        )
        self.MAX_CONCURRENT_BATCHES: int = _env_int(
            "MAX_CONCURRENT_BATCHES", 2
        )

        # ── Extraction Parameters ──
        self.MAX_INLINE_TAGS: int = _env_int("MAX_INLINE_TAGS", 8)
        self.MAX_SEGMENT_CHARS: int = _env_int("MAX_SEGMENT_CHARS", 400)
        self.BATCH_MAX_CHARS: int = _env_int("BATCH_MAX_CHARS", 3000)
        self.BATCH_MAX_SEGMENTS: int = _env_int("BATCH_MAX_SEGMENTS", 5)

        # ── Paths ──
        self.DATABASE_URL: str = _env(
            "DATABASE_URL", "sqlite:///data/db/translations.db"
        )
        self.UPLOAD_DIR: str = _env("UPLOAD_DIR", "/data/uploads")
        self.OUTPUT_DIR: str = _env("OUTPUT_DIR", "/data/output")
        self.TEMP_DIR: str = _env("TEMP_DIR", "/data/temp")

        # ── Workers ──
        self.MAX_WORKERS: int = _env_int("MAX_WORKERS", 1)

        # ── Supported File Types ──
        self.SUPPORTED_TYPES: set[str] = {
            "docx", "xlsx", "pptx", "pdf", "md", "txt", "csv"
        }


# Singleton instance
settings = Settings()

