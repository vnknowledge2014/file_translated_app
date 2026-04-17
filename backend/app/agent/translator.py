"""Batch translation via LLM with ||| delimiter.

Prompts and translation context are self-contained in this module.
No external prompt files or skill loaders needed.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re

import aiosqlite

from app.ollama.client import OllamaClient
from app.ollama.exceptions import OllamaTimeoutError

logger = logging.getLogger(__name__)


def _load_prompt_file(filename: str) -> str:
    """Load a prompt file from the prompts directory."""
    path = os.path.join(os.path.dirname(__file__), "../prompts", filename)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f"\n\n{f.read()}"
    return ""


# ── Format-specific translation rules ──
# OOXML rules (tag preservation) for docx/pptx/xlsx
# Plaintext rules (markdown/csv structure) for txt/md/csv
_OOXML_RULES = _load_prompt_file("ooxml_tag_rules.md")
_PLAINTEXT_RULES = _load_prompt_file("plaintext_rules.md")

_FORMAT_RULES: dict[str, str] = {
    "docx": _OOXML_RULES,
    "pptx": _OOXML_RULES,
    "xlsx": _OOXML_RULES,
    "txt": _PLAINTEXT_RULES,
    "md": _PLAINTEXT_RULES,
    "csv": _PLAINTEXT_RULES,
}


# ── Translation System Prompt ──

TRANSLATION_SYSTEM_PROMPT = """You are a Japanese-to-Vietnamese translator.

## INPUT FORMAT
- Single segment: translate directly
- Multiple segments separated by ||| → translate each, keep delimiter

## OUTPUT FORMAT
- Single → translated text only
- Multiple → translated segments separated by |||
- MUST output SAME NUMBER of segments as input
- No explanations, no notes, ONLY the translation

## RULES
- Japanese (日本語) → Vietnamese (Tiếng Việt)
- Keep English text AS-IS (do not translate English)
- Keep special characters: ※, ●, ◆, →, etc.
- Keep numbers and units: 100%, 3.14, 5GB
- Keep proper nouns and brand names

## QUALITY
- Natural Vietnamese grammar (Subject-Verb-Object)
- Correct Vietnamese diacritics (ă, â, ê, ô, ơ, ư, đ)
- Meaningful translation (意訳), not word-by-word (直訳)
- Ensure proper spacing between Vietnamese words at tag boundaries
- If a <tagN>word</tagN> is followed by another word, ensure a space exists
"""

# Max inline tags per segment before stripping tags for plain-text translation.
# LLM reliably handles ≤8 tags but consistently fails tag validation at >8,
# causing entire paragraphs to remain untranslated (seen in DOCX P[2]=28 tags).
_MAX_INLINE_TAGS = 8

# ── Per file-type context hints ──

TRANSLATE_CONTEXTS: dict[str, str] = {
    "docx": """## CONTEXT: Word Document
- Heading text → translate concisely
- Body text → translate naturally
- Table cells → translate as labels, keep short""",
    "xlsx": """## CONTEXT: Excel Spreadsheet
- Header cells → translate as column labels (short)
- Data cells → translate descriptions
- 完了→Hoàn thành, 未着手→Chưa bắt đầu, 進行中→Đang tiến hành""",
    "pptx": """## CONTEXT: PowerPoint Presentation
- Slide titles → concise, impactful
- Bullet points → maintain list structure
- Mixed JP/EN → translate only JP portions""",
    "pdf": """## CONTEXT: PDF Document
- May be from tables, paragraphs, or diagram labels
- Translate what's available""",
    "md": """## CONTEXT: Markdown Document
- PRESERVE ALL markup: #, **, ```, |, >, -, []()
- ONLY translate text between markup elements""",
    "txt": "## CONTEXT: Plain text. Translate naturally.",
    "csv": "## CONTEXT: CSV data. Translate text values only, not numbers/dates.",
}


def build_glossary_prompt(terms: list[dict]) -> str:
    """Build glossary injection for translation prompt.

    Args:
        terms: List of glossary term dicts with 'jp', 'vi', and optional 'context'.

    Returns:
        Formatted glossary table or "" if empty.
    """
    if not terms:
        return ""

    lines = [
        "## GLOSSARY (MUST use these translations)",
        "| JP | VI | Context |",
        "|:---|:---|:---|",
    ]
    for t in terms:
        lines.append(f"| {t['jp']} | {t['vi']} | {t.get('context', '')} |")
    lines.append(
        "\nWhen you see any term above, you MUST use the specified translation."
    )
    return "\n".join(lines)


# ── Batch Chunking ──


def chunk_segments(
    segments: list[dict],
    max_chars: int = 3000,
    max_segs: int = 5,
) -> list[list[dict]]:
    """Split segments into batches that fit the model's context window.

    Args:
        segments: List of segment dicts with 'text' field.
        max_chars: Max character count per batch.
        max_segs: Max segment count per batch.

    Returns:
        List of segment batches.

    Invariant:
        sum(len(batch) for batch in batches) == len(segments)
    """
    if not segments:
        return []

    batches: list[list[dict]] = []
    current_batch: list[dict] = []
    current_chars = 0

    for seg in segments:
        text_len = len(seg.get("text", ""))
        if current_batch and (
            current_chars + text_len > max_chars or len(current_batch) >= max_segs
        ):
            batches.append(current_batch)
            current_batch = []
            current_chars = 0
        current_batch.append(seg)
        current_chars += text_len

    if current_batch:
        batches.append(current_batch)

    return batches


# ── Translator ──


class Translator:
    """High-performance batch translator via local LLM.

    Supports concurrent batch translation using asyncio.gather
    with semaphore-based concurrency control to maximize throughput
    on local hardware.
    """

    def __init__(
        self,
        client: OllamaClient,
        model: str,
        max_concurrent: int = 1,
    ):
        """Initialize with Ollama client and model name.

        Args:
            client: Async Ollama HTTP client.
            model: Translation model name (e.g., "gemma4:e4b").
            max_concurrent: Max parallel batch requests to Ollama.
        """
        self.client = client
        self.model = model
        self._semaphore = asyncio.Semaphore(max_concurrent)
        
        # Ensure db dir exists and use absolute path
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "data", "db")
        os.makedirs(db_path, exist_ok=True)
        self.cache_db = os.path.join(db_path, "translations.db")

    async def _init_cache(self):
        """Initialize sqlite cache table."""
        async with aiosqlite.connect(self.cache_db) as db:
            await db.execute(
                "CREATE TABLE IF NOT EXISTS translations (source TEXT PRIMARY KEY, target TEXT)"
            )
            await db.commit()

    async def _get_cached_translation(self, source: str) -> str | None:
        async with aiosqlite.connect(self.cache_db) as db:
            async with db.execute(
                "SELECT target FROM translations WHERE source = ?", (source,)
            ) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else None

    async def _set_cached_translation(self, source: str, target: str):
        async with aiosqlite.connect(self.cache_db) as db:
            await db.execute(
                "INSERT OR REPLACE INTO translations (source, target) VALUES (?, ?)",
                (source, target),
            )
            await db.commit()

    def _build_system_prompt(
        self, file_type: str, glossary: list[dict] | None = None
    ) -> str:
        """Build the full system prompt with context and glossary."""
        system = TRANSLATION_SYSTEM_PROMPT
        ctx = TRANSLATE_CONTEXTS.get(file_type, "")
        if ctx:
            system += "\n" + ctx
        # Load format-specific rules (OOXML tags vs plaintext/markdown)
        format_rules = _FORMAT_RULES.get(file_type, "")
        if format_rules:
            system += format_rules
        gloss_prompt = build_glossary_prompt(glossary or [])
        if gloss_prompt:
            system += "\n" + gloss_prompt
        return system

    def _validate_tags(self, original: str, translated: str) -> bool:
        """Validate that all <tagX> or </tagX> in original exist exactly in translated."""
        orig_tags = sorted(re.findall(r"</?tag\d+>", original))
        trans_tags = sorted(re.findall(r"</?tag\d+>", translated))
        return orig_tags == trans_tags

    def _has_jp_leak(self, translated: str) -> bool:
        """Detect untranslated Japanese characters left in the translated output.

        Returns True if Hiragana, Katakana, or CJK ideographs are found in the
        translated text — indicating the LLM failed to translate some portion.

        Note: fullwidth digits/latin (\uff10-\uff5a) and halfwidth katakana
        (\uff65-\uff9f) are intentionally excluded because they can legitimately
        appear in Vietnamese technical contexts (e.g. product codes).

        Args:
            translated: The translated text returned by the LLM.

        Returns:
            True if Japanese characters are detected (leak found).
        """
        _LEAK_RE = re.compile(
            r"[\u3040-\u309F"  # Hiragana
            r"\u30A0-\u30FA\u30FC-\u30FF"  # Katakana EXCLUDING ・(U+30FB)
            r"\u4E00-\u9FFF"  # CJK Unified Ideographs (Kanji)
            r"\u3400-\u4DBF]"  # CJK Extension A
        )
        return bool(_LEAK_RE.search(translated))

    async def translate_batch(
        self,
        segments: list[dict],
        file_type: str,
        glossary: list[dict] | None = None,
    ) -> list[dict]:
        """Translate a batch of segments.

        Strategy:
        1. Join segment texts with |||
        2. Send to LLM
        3. Split response by |||
        4. If count mismatch → fall back to 1-by-1 translation

        Uses semaphore for concurrency control when called in parallel.

        Args:
            segments: List of segment dicts with 'text' field.
            file_type: Document type for context.
            glossary: Optional glossary terms.

        Returns:
            Same segments list with added "translated_text" field.
        """
        if not segments:
            return segments

        system = self._build_system_prompt(file_type, glossary)

        # Determine segments that actually need translation (checking cache)
        # We pre-fill cached translated texts and gather uncached texts
        to_translate = []
        for seg in segments:
            cache_hit = await self._get_cached_translation(seg["text"])
            if cache_hit:
                seg["translated_text"] = cache_hit
            else:
                to_translate.append(seg)

        if not to_translate:
            return segments

        # Strip tags from segments with too many inline tags.
        # These always fail tag validation and waste RALPH retries,
        # leaving the paragraph completely untranslated.
        for seg in to_translate:
            tag_count = len(re.findall(r'</?tag\d+>', seg["text"]))
            if tag_count > _MAX_INLINE_TAGS:
                seg["_original_tagged_text"] = seg["text"]
                seg["text"] = re.sub(r'</?tag\d+>', '', seg["text"])
                seg["_no_tags"] = True
                logger.info(
                    f"Stripped {tag_count} tags from segment "
                    f"({len(seg['text'])} chars) for plain-text translation."
                )

        texts = [s["text"] for s in to_translate]
        user_prompt = "|||".join(texts)

        try:
            async with self._semaphore:
                response = await self.client.generate(
                    model=self.model,
                    prompt=user_prompt,
                    system=system,
                    temperature=0.3,
                    num_ctx=4096,  # Reduced for safety
                )
        except OllamaTimeoutError:
            logger.error(
                "LLM Timeout explicitly caught for batch. Skipping to original texts."
            )
            for seg in to_translate:
                seg["translated_text"] = seg["text"]  # Graceful skip
            return segments

        # Parse response
        translated = response.strip().split("|||")

        # We will track which segments need a strict 1-by-1 retry
        needs_retry = []

        if len(translated) == len(to_translate):
            for seg, trans in zip(to_translate, translated):
                trans_clean = trans.strip()
                if self._has_jp_leak(trans_clean):
                    logger.warning(
                        f"JP leak detected in batch output for: {seg['text'][:60]!r}. "
                        f"Queueing for 1-by-1 retry."
                    )
                    needs_retry.append(seg)
                elif seg.get("_no_tags") or self._validate_tags(seg["text"], trans_clean):
                    # For tag-stripped segments, restore original tagged text as
                    # tmap key so reconstructor can match during run replacement.
                    if seg.get("_no_tags"):
                        cache_key = seg["text"]  # plain text (for cache)
                        seg["text"] = seg["_original_tagged_text"]
                    else:
                        cache_key = seg["text"]
                    seg["translated_text"] = trans_clean
                    await self._set_cached_translation(cache_key, trans_clean)
                else:
                    logger.warning(
                        f"Tag validation failed for segment. Queueing for RALPH retry."
                    )
                    needs_retry.append(seg)
        else:
            # Count mismatch — all need retry
            logger.warning(
                f"Batch count mismatch: expected {len(to_translate)}, "
                f"got {len(translated)}. Falling back to 1-by-1."
            )
            needs_retry = list(to_translate)

        # RALPH Loop: 1-by-1 retry with strict tag + JP-leak checking (max 3 attempts)
        for seg in needs_retry:
            max_attempts = (
                3  # 3 attempts max — at 90s timeout = 4.5min worst-case per segment
            )
            success = False
            single_clean = seg["text"]  # safe fallback default
            for attempt in range(1, max_attempts + 1):
                retry_system = system
                # Build cumulative warning based on what failed previously
                warnings: list[str] = []
                if attempt > 1 and re.findall(r"</?tag\d+>", seg["text"]):
                    warnings.append(
                        f"[WARNING] Your previous translation lost XML tags. "
                        f"You MUST preserve exactly these tags: "
                        f"{re.findall(r'</?tag\d+>', seg['text'])}"
                    )
                if attempt > 1:
                    warnings.append(
                        "[WARNING] You MUST translate ALL Japanese text to Vietnamese. "
                        "Do NOT leave any Kanji (漢字), Hiragana (ひらがな), or Katakana (カタカナ) "
                        "in the output. Every Japanese word must become a Vietnamese word."
                    )
                if warnings:
                    retry_system += "\n\n" + "\n".join(warnings)

                try:
                    async with self._semaphore:
                        single_response = await self.client.generate(
                            model=self.model,
                            prompt=seg["text"],
                            system=retry_system,
                            temperature=0.2,
                            num_ctx=4096,
                        )
                except OllamaTimeoutError:
                    logger.error(
                        f"Failed via Timeout during 1-by-1 attempt {attempt}. Graceful Skip."
                    )
                    single_response = seg["text"]

                single_clean = single_response.strip()

                jp_leak = self._has_jp_leak(single_clean)
                # Skip tag validation for segments that had tags stripped
                tags_ok = seg.get("_no_tags") or self._validate_tags(
                    seg["text"], single_clean
                )

                if jp_leak:
                    logger.warning(
                        f"Attempt {attempt}: JP leak still present in: {single_clean[:60]!r}"
                    )
                elif not tags_ok:
                    logger.warning(
                        f"Attempt {attempt}: Tag validation failed for {seg['text'][:60]!r}"
                    )
                else:
                    # Both checks pass — accept and cache
                    seg["translated_text"] = single_clean
                    await self._set_cached_translation(seg["text"], single_clean)
                    success = True
                    break

            if not success:
                logger.error(
                    f"Failed to fully translate after {max_attempts} attempts for: "
                    f"{seg['text'][:80]!r}. Using best-effort output."
                )
                # Do NOT cache a leaky/broken translation
                seg["translated_text"] = single_clean

        return segments

    async def translate_all(
        self,
        batches: list[list[dict]],
        file_type: str,
        glossary: list[dict] | None = None,
        on_progress: callable | None = None,
    ) -> int:
        """Translate all batches concurrently using asyncio.gather.

        Args:
            batches: Pre-chunked segment batches.
            file_type: Document type for context.
            glossary: Optional glossary terms.
            on_progress: Callback(translated_count, total_count) for progress.

        Returns:
            Total number of translated segments.
        """
        if not batches:
            return 0

        total = sum(len(b) for b in batches)
        completed = 0

        async def _translate_with_progress(batch: list[dict]) -> list[dict]:
            nonlocal completed
            result = await self.translate_batch(batch, file_type, glossary)
            completed += len(result)
            if on_progress:
                on_progress(completed, total)
            return result

        # Ensure cache DB exists before processing
        await self._init_cache()

        # Fire all batches concurrently — semaphore controls parallelism
        await asyncio.gather(*[_translate_with_progress(b) for b in batches])

        return total
