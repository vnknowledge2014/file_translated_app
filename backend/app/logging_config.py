"""Structured JSON logging configuration.

Provides a JSON formatter for production use and a human-readable
colored formatter for development.

Usage in main.py:
    from app.logging_config import setup_logging
    setup_logging(json_mode=True)  # Production: JSON to stdout
    setup_logging(json_mode=False) # Dev: colored human-readable
"""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timezone


class JSONFormatter(logging.Formatter):
    """Emit log records as single-line JSON objects.

    Output format:
        {"ts": "...", "level": "INFO", "logger": "app.worker", "msg": "...", "extra": {...}}
    """

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }

        # Include exception info if present
        if record.exc_info and record.exc_info[0]:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Include extra fields (e.g. job_id, phase, duration)
        skip = {
            "name",
            "msg",
            "args",
            "created",
            "relativeCreated",
            "thread",
            "threadName",
            "msecs",
            "pathname",
            "filename",
            "module",
            "exc_info",
            "exc_text",
            "stack_info",
            "lineno",
            "funcName",
            "processName",
            "process",
            "message",
            "levelname",
            "levelno",
            "taskName",
        }
        extras = {
            k: v
            for k, v in record.__dict__.items()
            if k not in skip and not k.startswith("_")
        }
        if extras:
            log_entry["extra"] = extras

        return json.dumps(log_entry, ensure_ascii=False, default=str)


class DevFormatter(logging.Formatter):
    """Human-readable colored formatter for development."""

    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, "")
        ts = datetime.now().strftime("%H:%M:%S")
        prefix = f"{color}{ts} [{record.levelname:>7}]{self.RESET}"
        return f"{prefix} {record.name}: {record.getMessage()}"


def setup_logging(json_mode: bool | None = None) -> None:
    """Configure root logger with appropriate formatter.

    Args:
        json_mode: Force JSON (True) or dev (False) mode.
                   If None, auto-detect from LOG_FORMAT env var.
    """
    if json_mode is None:
        json_mode = os.environ.get("LOG_FORMAT", "dev").lower() == "json"

    level_str = os.environ.get("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_str, logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter() if json_mode else DevFormatter())

    # Configure root logger
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)

    # Reduce noise from third-party libs
    for noisy in ("httpx", "httpcore", "uvicorn.access", "surrealdb"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    logging.getLogger(__name__).info(
        f"Logging configured: mode={'json' if json_mode else 'dev'}, level={level_str}"
    )
