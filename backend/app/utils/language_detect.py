"""Universal language detection and text utilities.

Provides:
- has_source_language(): Check if text contains a specific language's characters
- detect_language(): Auto-detect the dominant language of text
- analyze_segment(): Deep analysis of mixed-language segments (composition, English terms)
- chunk_text(): Language-aware sentence-boundary text splitting

Usage:
    from app.utils.language_detect import has_source_language, detect_language, analyze_segment

    has_source_language("これはテスト", "ja")  # True
    detect_language("これはテスト")             # "ja"
    analyze_segment("APIキーを設定する")        # {"dominant": "ja", "has_english": True, ...}
"""

from __future__ import annotations

import re
from functools import lru_cache

from app.languages import LanguageProfile, get_language, SUPPORTED_LANGUAGES
from app.domains import get_domain


# Symbols that are commonly retained as visual markers and should NOT
# trigger source-language detection when they appear alone.
_SHARED_SYMBOLS = set("・ー〇△×◯●■□▲▼★☆◆※　")

# ── English technical term detection ──
# Matches sequences of ASCII letters (2+ chars) that look like English words/terms.
# Includes camelCase, PascalCase, UPPERCASE, and dotted terms (e.g. "api.v2").
_ENGLISH_TOKEN_RE = re.compile(
    r"""
    (?<![A-Za-z])          # Not preceded by ASCII letter
    (
        [A-Z]{2,}          # ACRONYMS: API, HTTP, SQL, AWS
        | [A-Z][a-z]+      # PascalCase words: Docker, Python, Kubernetes
          (?:[A-Z][a-z]+)* # ...continued: JavaScript, TypeScript
        | [a-z]{2,}        # lowercase words: docker, api, config (2+ chars)
    )
    (?:\.[A-Za-z]+)*       # Optional dotted suffix: api.v2, node.js
    (?![A-Za-z])           # Not followed by ASCII letter
    """,
    re.VERBOSE,
)

# Common English stop-words that should NOT be treated as "technical terms to preserve".
# These are functional words that are normally translated.
_ENGLISH_STOP_WORDS = frozenset({
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "shall",
    "should", "may", "might", "must", "can", "could",
    "and", "or", "but", "if", "then", "else", "when", "where", "how",
    "what", "which", "who", "whom", "this", "that", "these", "those",
    "it", "its", "he", "she", "we", "they", "you", "me", "him", "her",
    "us", "them", "my", "your", "his", "our", "their",
    "in", "on", "at", "to", "for", "of", "with", "by", "from", "as",
    "into", "about", "between", "through", "after", "before",
    "not", "no", "yes", "so", "than", "too", "very", "just", "also",
    "up", "out", "off", "over", "under",
})



@lru_cache(maxsize=32)
def _build_char_regex(lang_code: str) -> re.Pattern:
    """Build a compiled regex for detecting characters of a specific language.

    Args:
        lang_code: ISO 639-1 language code.

    Returns:
        Compiled regex pattern matching any character in the language's ranges.
    """
    profile = get_language(lang_code)
    if not profile.char_ranges:
        return re.compile(r"(?!)")  # Never matches

    parts = []
    for start, end in profile.char_ranges:
        if end <= 0xFFFF:
            parts.append(f"\\u{start:04X}-\\u{end:04X}")
        else:
            # Supplementary Unicode plane — use surrogate-safe pattern
            parts.append(f"\\U{start:08X}-\\U{end:08X}")
    pattern = f"[{''.join(parts)}]"
    return re.compile(pattern)


def _strip_shared_symbols(text: str) -> str:
    """Remove shared visual symbols from text for detection purposes."""
    return "".join(c for c in text if c not in _SHARED_SYMBOLS)


def has_source_language(text: str | None, lang_code: str) -> bool:
    """Return True if text contains characters from the specified source language.

    Args:
        text: Input string, may be None.
        lang_code: ISO 639-1 code of the source language to detect.

    Returns:
        True if any character from the source language is found.
    """
    if not text:
        return False

    stripped = _strip_shared_symbols(text.strip())
    if not stripped:
        return False

    regex = _build_char_regex(lang_code)
    return bool(regex.search(stripped))


def detect_language(text: str | None) -> str | None:
    """Auto-detect the dominant language of a text segment.

    Uses Unicode block analysis to identify the most likely language.
    For Latin-script languages, detection is less reliable and may
    return None (use an external library like `langdetect` for those).

    Args:
        text: Input text to analyze.

    Returns:
        ISO 639-1 code of detected language, or None if ambiguous.
    """
    if not text or not text.strip():
        return None

    stripped = _strip_shared_symbols(text.strip())
    if not stripped:
        return None

    # Score each language by character hit count
    scores: dict[str, int] = {}
    for lang_code, profile in SUPPORTED_LANGUAGES.items():
        if not profile.char_ranges:
            continue
        regex = _build_char_regex(lang_code)
        hits = len(regex.findall(stripped))
        if hits > 0:
            scores[lang_code] = hits

    if not scores:
        return None

    # For CJK disambiguation (JA vs ZH share many codepoints):
    # If both JA and ZH score, check for Hiragana/Katakana (unique to JA)
    if "ja" in scores and "zh" in scores:
        hiragana_katakana = re.compile(r"[\u3040-\u309F\u30A0-\u30FF]")
        if hiragana_katakana.search(stripped):
            # Has kana → definitely Japanese
            return "ja"
        else:
            # Pure kanji → could be either, prefer ZH if no kana
            return "zh"

    # Return highest scoring language
    return max(scores, key=scores.get)


def extract_english_terms(text: str) -> list[str]:
    """Extract English technical terms from a mixed-language text segment.

    Identifies English words/terms embedded in non-English text (e.g., "API"
    in "APIキーを設定する"). Filters out common stop-words that should be
    translated normally.

    Args:
        text: Input text, possibly mixed-language.

    Returns:
        List of unique English terms found, ordered by position.
    """
    if not text:
        return []

    matches = _ENGLISH_TOKEN_RE.findall(text)
    seen: set[str] = set()
    result: list[str] = []
    for m in matches:
        # Skip stop words (case-insensitive)
        if m.lower() in _ENGLISH_STOP_WORDS:
            continue
        # Skip single-char matches (usually not meaningful terms)
        if len(m) < 2:
            continue
        if m not in seen:
            seen.add(m)
            result.append(m)
    return result


def is_technical_term(term: str, domain_code: str | None = None) -> bool:
    """Check if an English term is a known technical term that should be preserved.

    Checks against the built-in dictionary for the specified Domain.
    The Glossary feature extends this dynamically at runtime.

    Args:
        term: English term to check.
        domain_code: The active Domain code (e.g., 'it', 'medical').

    Returns:
        True if the term should be preserved as-is in translation.
    """
    domain = get_domain(domain_code)
    
    # If the domain doesn't preserve English terms generally, ONLY check explicit dictionary
    if not domain.preserve_english_terms:
        if term in domain.built_in_terms:
            return True
        term_lower = term.lower()
        if any(t.lower() == term_lower for t in domain.built_in_terms):
            return True
        return False

    # Domain aggressively preserves English terms (like IT)
    # Exact match (case-sensitive for acronyms)
    if term in domain.built_in_terms:
        return True
    # Case-insensitive match for mixed-case terms
    term_lower = term.lower()
    if any(t.lower() == term_lower for t in domain.built_in_terms):
        return True
    # All-caps terms of 2-5 chars are likely acronyms → preserve
    if term.isupper() and 2 <= len(term) <= 5:
        return True
    return False


def analyze_segment(text: str | None, domain_code: str | None = None) -> dict:
    """Deep analysis of a text segment's language composition.

    This is the "smart mode" that understands mixed-language documents.
    It answers: What languages are in this segment? What English terms
    should be preserved? How much of the text is source language vs English?

    Args:
        text: Input text segment.
        domain_code: Active domain code for contextual term preservation.

    Returns:
        Dict with:
            - dominant: ISO 639-1 code of the dominant language, or None
            - languages: dict of {lang_code: char_count} for all detected languages
            - has_english: True if English text is present
            - english_terms: List of English terms found
            - english_ratio: Fraction of text that is English (0.0–1.0)
            - preserve_terms: English terms that should NOT be translated
            - translatable_ratio: Fraction of text that needs translation
    """
    if not text or not text.strip():
        return {
            "dominant": None,
            "languages": {},
            "has_english": False,
            "english_terms": [],
            "english_ratio": 0.0,
            "preserve_terms": [],
            "translatable_ratio": 0.0,
        }

    stripped = text.strip()
    total_chars = len(stripped)

    # Count characters per language
    lang_counts: dict[str, int] = {}
    for lang_code, profile in SUPPORTED_LANGUAGES.items():
        if not profile.char_ranges:
            continue
        regex = _build_char_regex(lang_code)
        hits = len(regex.findall(stripped))
        if hits > 0:
            lang_counts[lang_code] = hits

    # Count English ASCII characters (A-Z, a-z)
    en_chars = len(re.findall(r"[A-Za-z]", stripped))
    has_english = en_chars > 0

    # Extract English terms
    english_terms = extract_english_terms(stripped)
    preserve_terms = [t for t in english_terms if is_technical_term(t, domain_code)]

    # Calculate ratios
    english_ratio = en_chars / total_chars if total_chars > 0 else 0.0

    # Dominant language detection (excluding English from non-Latin source languages)
    dominant = detect_language(stripped)

    # Translatable ratio: characters belonging to the source language
    source_chars = sum(lang_counts.get(lc, 0) for lc in lang_counts if lc != "en")
    translatable_ratio = source_chars / total_chars if total_chars > 0 else 0.0

    return {
        "dominant": dominant,
        "languages": lang_counts,
        "has_english": has_english,
        "english_terms": english_terms,
        "english_ratio": round(english_ratio, 3),
        "preserve_terms": preserve_terms,
        "translatable_ratio": round(translatable_ratio, 3),
    }


@lru_cache(maxsize=32)
def _build_sentence_end_regex(lang_code: str) -> re.Pattern:
    """Build sentence-ending regex for a language."""
    profile = get_language(lang_code)
    enders = re.escape(profile.sentence_enders)
    return re.compile(f"([{enders}\\n\\n])")


def chunk_text(text: str, lang_code: str = "ja", max_chars: int = 3000) -> list[str]:
    """Split text into chunks at language-appropriate sentence boundaries.

    Args:
        text: Input text to chunk.
        lang_code: Source language code for sentence boundary detection.
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

    sentence_re = _build_sentence_end_regex(lang_code)
    chunks: list[str] = []
    remaining = text

    while remaining:
        if len(remaining) <= max_chars:
            chunks.append(remaining)
            break

        window = remaining[:max_chars]
        best_break = -1

        for match in sentence_re.finditer(window):
            best_break = match.end()

        if best_break > 0:
            chunks.append(remaining[:best_break])
            remaining = remaining[best_break:]
        else:
            chunks.append(remaining[:max_chars])
            remaining = remaining[max_chars:]

    return chunks
