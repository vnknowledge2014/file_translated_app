"""File type detection for supported document formats."""

from __future__ import annotations

import os

SUPPORTED_TYPES: set[str] = {"docx", "xlsx", "pptx", "pdf", "md", "txt", "csv"}

_EXTENSION_MAP: dict[str, str] = {
    ".docx": "docx",
    ".xlsx": "xlsx",
    ".pptx": "pptx",
    ".pdf": "pdf",
    ".md": "md",
    ".txt": "txt",
    ".csv": "csv",
}


def detect_file_type(filename: str) -> str | None:
    """Detect file type from filename extension.

    Case-insensitive. Returns lowercase type string.
    Returns None for unsupported types.

    Args:
        filename: File name or path with extension.

    Returns:
        Lowercase file type string ("docx", "xlsx", etc.) or None.
    """
    if not filename:
        return None
    _, ext = os.path.splitext(filename)
    return _EXTENSION_MAP.get(ext.lower())


def get_supported_types() -> set[str]:
    """Return set of all supported file type strings."""
    return SUPPORTED_TYPES.copy()
