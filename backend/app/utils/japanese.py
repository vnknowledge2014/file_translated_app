"""Japanese text detection and chunking utilities."""

from __future__ import annotations

import re

# Pre-compiled regex for performance — covers all Japanese character ranges
_JP_PATTERN = re.compile(
    r"[\u3040-\u309F"  # Hiragana: ぁ-ん
    r"\u30A0-\u30FF"  # Katakana: ァ-ヶ
    r"\u4E00-\u9FFF"  # CJK Unified Ideographs: 漢字
    r"\uFF10-\uFF19"  # Fullwidth digits: ０-９
    r"\uFF21-\uFF5A"  # Fullwidth latin: Ａ-ｚ
    r"\uFF65-\uFF9F]"  # Halfwidth katakana: ｦ-ﾟ
)

# Japanese sentence-ending markers
_JP_SENTENCE_ENDS = re.compile(r"([。！？\n\n])")


# Japanese symbols that are commonly retained in translated text as visual markers
# (middle dot, long vowel, circle, triangle, cross, fullwidth space, etc.)
# These should NOT trigger has_japanese() when they appear alone or mixed with non-JP text
_JP_SYMBOL_CHARS = set("・ー〇△×◯●■□▲▼★☆◆※　")  # U+30FB U+30FC U+3007 etc.


def _strip_jp_symbols(text: str) -> str:
    """Remove known JP visual symbols from text for detection purposes."""
    return "".join(c for c in text if c not in _JP_SYMBOL_CHARS)


def has_japanese(text: str | None) -> bool:
    """Return True if text contains any Japanese characters.

    Detects Hiragana, Katakana, CJK Ideographs, fullwidth digits/latin,
    and halfwidth katakana. Excludes strings that are purely punctuation.

    Args:
        text: Input string, may be None.

    Returns:
        True if any translatable Japanese character found, False otherwise.
    """
    if not text:
        return False

    # Strip visual JP symbols (・〇△ー etc.) before checking —
    # these are commonly retained as bullet markers in translated text
    stripped = _strip_jp_symbols(text.strip())
    if not stripped:
        return False  # text was purely JP symbols

    return bool(_JP_PATTERN.search(stripped))


def chunk_text(text: str, max_chars: int = 3000) -> list[str]:
    """Split text into chunks that fit within max_chars.

    Breaks at Japanese sentence boundaries (。！？) or double newlines.
    If no boundary found within max_chars, hard-breaks at max_chars.

    Args:
        text: Input text to chunk.
        max_chars: Maximum characters per chunk.

    Returns:
        List of text chunks. Empty list if text is empty/None.

    Invariant:
        "".join(chunks) == text  (no text lost)
    """
    if not text:
        return []

    if len(text) <= max_chars:
        return [text]

    chunks: list[str] = []
    remaining = text

    while remaining:
        if len(remaining) <= max_chars:
            chunks.append(remaining)
            break

        # Look for the last sentence boundary within max_chars
        window = remaining[:max_chars]
        best_break = -1

        # Search for sentence-ending markers
        for match in _JP_SENTENCE_ENDS.finditer(window):
            best_break = match.end()

        if best_break > 0:
            chunks.append(remaining[:best_break])
            remaining = remaining[best_break:]
        else:
            # No sentence boundary found — hard break
            chunks.append(remaining[:max_chars])
            remaining = remaining[max_chars:]

    return chunks
