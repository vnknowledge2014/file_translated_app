"""Shared utilities for deterministic document reconstruction.

Pure functions with no file I/O or XML dependencies.
Used by all format-specific reconstructor modules.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def build_translation_map(segments: list[dict]) -> dict[str, str]:
    """Build a lookup from original text → translated text.

    Args:
        segments: List of segment dicts with 'text' and 'translated_text'.

    Returns:
        Dict mapping original JP text to translated VI text.
    """
    tmap: dict[str, str] = {}
    for seg in segments:
        original = seg.get("text", "").strip()
        translated = seg.get("translated_text", "").strip()
        if original and translated and original != translated:
            tmap[original] = translated
    return tmap


def replace_in_text(text: str, tmap: dict[str, str]) -> str | None:
    """Check if text matches any key in tmap, return replacement or None.

    Tries exact match first, then partial match for longer texts.

    Args:
        text: Original text to check.
        tmap: Translation lookup map.

    Returns:
        Translated text if found, None otherwise.
    """
    if not text or not text.strip():
        return None

    stripped = text.strip()

    # Exact match
    if stripped in tmap:
        return tmap[stripped]

    # Try partial match for longer texts (paragraph-level)
    # Sort by key length descending so longer strings are replaced first,
    # preventing short substrings from corrupting longer matches
    # (e.g., '管理' must not replace inside 'イベント管理')
    for jp, vi in sorted(tmap.items(), key=lambda x: len(x[0]), reverse=True):
        if jp in stripped:
            stripped = stripped.replace(jp, vi)
    if stripped != text.strip():
        return stripped

    return None
