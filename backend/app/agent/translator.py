"""Batch translation via LLM with ||| delimiter.

Prompts and translation context are self-contained in this module.
No external prompt files or skill loaders needed.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re

from app.database import db

from app.config import settings
from app.languages import get_language

from app.llm.base import LLMClient
from app.ollama.exceptions import OllamaTimeoutError
from app.agent.prompt_router import PromptRouter

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


# ── Batch Chunking ──


def chunk_segments(
    segments: list[dict],
    max_chars: int | None = None,
    max_segs: int | None = None,
) -> list[list[dict]]:
    if max_chars is None:
        max_chars = settings.BATCH_MAX_CHARS
    if max_segs is None:
        max_segs = settings.BATCH_MAX_SEGMENTS
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
        client: LLMClient,
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
        self.router = PromptRouter()
        # Concurrency limiter to prevent overloading Ollama
        self._semaphore = asyncio.Semaphore(max_concurrent)

    async def _init_cache(self):
        """No initialization needed for SurrealDB here."""
        pass

    async def _get_cached_translation(
        self, source: str, source_lang: str, target_lang: str, domain: str
    ) -> tuple[str | None, list[dict]]:
        try:
            # 1. Exact match check
            result = await db.query(
                "SELECT target FROM translation_cache WHERE source = $source AND source_lang = $source_lang AND target_lang = $target_lang AND model = $model AND domain = $domain LIMIT 1",
                {
                    "source": source,
                    "source_lang": source_lang,
                    "target_lang": target_lang,
                    "model": self.model,
                    "domain": domain,
                },
            )
            records = result if isinstance(result, list) else [result] if result else []
            if records:
                return records[0]["target"], []

            # 2. Fuzzy match (Vector Search)
            if not settings.ENABLE_FUZZY_CACHE:
                return None, []

            # Generate embedding for the source text
            try:
                query_embedding = await self.client.generate_embedding(
                    model=settings.EMBEDDING_MODEL, prompt=source
                )
            except Exception as e:
                logger.warning(f"Failed to generate embedding: {e}")
                return None, []

            fuzzy_result = await db.query(
                "SELECT source, target, vector::similarity::cosine(embedding, $query_embedding) AS sim FROM translation_cache WHERE source_lang = $source_lang AND target_lang = $target_lang AND domain = $domain AND sim > 0.8 ORDER BY sim DESC LIMIT 3",
                {
                    "query_embedding": query_embedding,
                    "source_lang": source_lang,
                    "target_lang": target_lang,
                    "domain": domain,
                },
            )
            fuzzy_matches = fuzzy_result if isinstance(fuzzy_result, list) else [fuzzy_result] if fuzzy_result else []
            return None, fuzzy_matches
        except Exception as e:
            logger.debug(f"Cache lookup failed (non-fatal): {e}")
            return None, []

    async def _set_cached_translation(
        self, source: str, target: str, source_lang: str, target_lang: str, domain: str
    ):
        try:
            embedding = []
            if settings.ENABLE_FUZZY_CACHE:
                try:
                    embedding = await self.client.generate_embedding(
                        model=settings.EMBEDDING_MODEL, prompt=source
                    )
                except Exception as e:
                    logger.warning(f"Failed to generate embedding for cache storage: {e}")

            import hashlib
            raw_key = f"{source}_{source_lang}_{target_lang}_{self.model}_{domain}"
            key_hash = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
            record_id = f"translation_cache:{key_hash}"
            
            data = {
                "source": source,
                "target": target,
                "source_lang": source_lang,
                "target_lang": target_lang,
                "model": self.model,
                "domain": domain,
            }

            if embedding:
                data["embedding"] = embedding

            await db.query(
                "UPSERT type::record($id) CONTENT $data",
                {"id": record_id, "data": data},
            )
        except Exception as e:
            logger.debug(f"Cache store failed (non-fatal): {e}")

    def _validate_tags(self, original: str, translated: str) -> bool:
        """Validate that all <tagX> or </tagX> in original exist exactly in translated."""
        orig_tags = sorted(re.findall(r"</?tag\d+>", original))
        trans_tags = sorted(re.findall(r"</?tag\d+>", translated))
        return orig_tags == trans_tags

    def _has_source_leak(
        self, translated: str, source_lang: str, target_lang: str
    ) -> bool:
        """Detect untranslated source language characters left in the output.

        Returns True if source language characters are found in the
        translated text — indicating the LLM failed to translate some portion.

        Args:
            translated: The translated text returned by the LLM.
            source_lang: The source language code to detect.
            target_lang: The target language code to prevent false positives.

        Returns:
            True if source language characters are detected (leak found).
        """
        from app.utils.language_detect import has_source_language

        return has_source_language(translated, source_lang, target_lang)

    async def translate_batch(
        self,
        segments: list[dict],
        file_type: str,
        glossary: list[dict] | None = None,
        domain_code: str = "general",
        source_lang: str = "ja",
        target_lang: str = "vi",
    ) -> list[dict]:
        """Translate a batch of segments using a single prompt with ||| delimiter."""
        if not segments:
            return segments

        # Extract english terms upfront to detect mixed languages if any
        # This acts as our "Language Composition" detection
        from app.utils.language_detect import extract_english_terms, is_technical_term

        all_terms: set[str] = set()
        for s in segments:
            for term in extract_english_terms(s["text"]):
                if is_technical_term(term, domain_code):
                    all_terms.add(term)

        mixed = []
        if all_terms:
            mixed = ["en"]  # For now, we flag English if there are English terms

        # 1) Build Super-Prompt using Context Matrix
        system = self.router.build_prompt(
            source_lang=source_lang,
            target_lang=target_lang,
            domain=domain_code,
            file_type=file_type,
            mixed_languages=mixed,
        )

        # 2) Optional glossary injection
        if glossary:
            terms = "\n".join([f"- {g['source']} -> {g['target']}" for g in glossary])
            system += f"\n\n## GLOSSARY\nUse these strict translations:\n{terms}"

        # Determine segments that actually need translation (checking cache)
        # We pre-fill cached translated texts and gather uncached texts
        to_translate = []
        all_fuzzy_matches = []
        for seg in segments:
            cache_hit, fuzzy_matches = await self._get_cached_translation(
                seg["text"], source_lang, target_lang, domain_code
            )
            if cache_hit:
                seg["translated_text"] = cache_hit
            else:
                to_translate.append(seg)
                all_fuzzy_matches.extend(fuzzy_matches)

        if not to_translate:
            return segments

        # Inject Fuzzy Matches into System Prompt
        if all_fuzzy_matches:
            # Deduplicate matches
            seen = set()
            unique_matches = []
            for m in all_fuzzy_matches:
                if m["source"] not in seen:
                    seen.add(m["source"])
                    unique_matches.append(m)

            tm_context = "\n".join(
                [
                    f"- Original: {m['source']}\n  Translation: {m['target']}"
                    for m in unique_matches[:5]
                ]
            )
            system += f"\n\n## TRANSLATION MEMORY (FUZZY MATCHES)\nThe following previous translations are similar to your current text. Use them as stylistic and terminological references:\n{tm_context}"

        texts = [s["text"] for s in to_translate]
        user_prompt = "|||".join(texts)

        try:
            async with self._semaphore:
                response = await self.client.generate(
                    model=self.model,
                    prompt=user_prompt,
                    system=system,
                    temperature=settings.TRANSLATION_TEMPERATURE,
                    num_ctx=settings.TRANSLATION_NUM_CTX,
                    think=settings.OLLAMA_THINK,
                    top_k=settings.TOP_K,
                    top_p=settings.TOP_P,
                    repeat_penalty=settings.REPETITION_PENALTY,
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
                if self._has_source_leak(trans_clean, source_lang, target_lang):
                    logger.warning(
                        f"Source language leak detected in batch output for: {seg['text'][:60]!r}. "
                        f"Queueing for 1-by-1 retry."
                    )
                    needs_retry.append(seg)
                elif self._validate_tags(seg["text"], trans_clean):
                    seg["translated_text"] = trans_clean
                    await self._set_cached_translation(
                        seg["text"], trans_clean, source_lang, target_lang, domain_code
                    )
                else:
                    logger.warning(
                        "Tag validation failed for segment. Queueing for RALPH retry."
                    )
                    needs_retry.append(seg)
        else:
            # Count mismatch — all need retry
            logger.warning(
                f"Batch count mismatch: expected {len(to_translate)}, "
                f"got {len(translated)}. Falling back to 1-by-1."
            )
            needs_retry = list(to_translate)

        # RALPH Loop: 1-by-1 retry with strict tag + source-leak checking (max 3 attempts)
        for seg in needs_retry:
            max_attempts = settings.TRANSLATION_MAX_RETRIES
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
                    src = get_language(source_lang)
                    tgt = get_language(target_lang)
                    warnings.append(
                        f"[WARNING] You MUST translate ALL {src.name} text to {tgt.name}. "
                        f"Do NOT leave any {src.name} characters "
                        f"in the output. Every {src.name} word must become a {tgt.name} word."
                    )
                if warnings:
                    retry_system += "\n\n" + "\n".join(warnings)

                try:
                    async with self._semaphore:
                        single_response = await self.client.generate(
                            model=self.model,
                            prompt=seg["text"],
                            system=retry_system,
                            temperature=max(
                                settings.TRANSLATION_TEMPERATURE - 0.1, 0.1
                            ),
                            num_ctx=settings.TRANSLATION_NUM_CTX,
                            think=settings.OLLAMA_THINK,
                            top_k=settings.TOP_K,
                            top_p=settings.TOP_P,
                            repeat_penalty=settings.REPETITION_PENALTY,
                        )
                except OllamaTimeoutError:
                    logger.error(
                        f"Failed via Timeout during 1-by-1 attempt {attempt}. Graceful Skip."
                    )
                    single_response = seg["text"]

                single_clean = single_response.strip()

                jp_leak = self._has_source_leak(single_clean, source_lang, target_lang)
                tags_ok = self._validate_tags(seg["text"], single_clean)

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
                    await self._set_cached_translation(
                        seg["text"], single_clean, source_lang, target_lang, domain_code
                    )
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
        domain_code: str = "general",
        source_lang: str = "ja",
        target_lang: str = "vi",
        on_progress: callable | None = None,
    ) -> int:
        """Translate all batches concurrently using asyncio.gather.

        Args:
            batches: Pre-chunked segment batches.
            file_type: Document type for context.
            glossary: Optional glossary terms.
            domain_code: Active domain code.
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
            result = await self.translate_batch(
                batch, file_type, glossary, domain_code, source_lang, target_lang
            )
            completed += len(result)
            if on_progress:
                on_progress(completed, total)
            return result

        # Ensure cache DB exists before processing
        await self._init_cache()

        # Fire all batches concurrently — semaphore controls parallelism
        await asyncio.gather(*[_translate_with_progress(b) for b in batches])

        return total
