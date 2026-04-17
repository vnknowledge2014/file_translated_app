"""Orchestrator — fully deterministic Extract → Translate → Reconstruct pipeline.

No LLM involvement in extraction or reconstruction.
LLM is used ONLY for the translation step.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Callable

from app.agent.extractor import extract_document
from app.agent.reconstructor import reconstruct_document, reconstruct_plaintext
from app.agent.translator import Translator, chunk_segments
from app.ollama.model_manager import ModelManager

logger = logging.getLogger(__name__)


class Orchestrator:
    """End-to-end translation pipeline.

    Steps:
    1. EXTRACTING: Deterministic extraction (python-docx/openpyxl/python-pptx)
    2. TRANSLATING: LLM batch translates JP → VI (parallel batches)
    3. RECONSTRUCTING: Clone original → replace text deterministically
    4. VERIFYING: Check output file integrity
    """

    def __init__(
        self,
        model_manager: ModelManager,
        translator: Translator,
        model: str,
        on_progress: Callable | None = None,
    ):
        """Initialize with pipeline dependencies.

        Args:
            model_manager: Model loading manager.
            translator: Batch translator.
            model: LLM model name (e.g., gemma4:e4b).
            on_progress: Optional progress callback.
        """
        self.model_manager = model_manager
        self.translator = translator
        self.model = model
        self.on_progress = on_progress

    def _emit(self, phase: str, progress: float, message: str):
        """Emit progress update."""
        if self.on_progress:
            self.on_progress(phase, progress, message)

    async def translate_file(
        self,
        file_path: str,
        file_type: str,
        job_id: str,
        output_path: str,
        glossary: list[dict] | None = None,
    ) -> dict:
        """Run complete translation pipeline.

        Args:
            file_path: Path to input file.
            file_type: Detected file type.
            job_id: Job UUID for tracking.
            output_path: Target output file path.
            glossary: Optional glossary terms.

        Returns:
            {
                "status": "completed" | "failed",
                "output_path": str | None,
                "segments_count": int,
                "duration_seconds": float,
                "error": str | None,
            }
        """
        start_time = time.time()
        segments_count = 0

        try:
            # ── PHASE 1: EXTRACTING (deterministic) ──
            self._emit("extracting", 0.1, "Extracting text from document...")

            segments = extract_document(file_type, file_path)
            segments_count = len(segments)

            logger.info(f"[{job_id}] Extracted {segments_count} segments")
            self._emit("extracting", 0.3, f"Extracted {segments_count} segments")

            if segments_count == 0:
                raise ValueError("No translatable text found in document")

            # ── PHASE 2: TRANSLATING (LLM — parallel batches) ──
            self._emit("translating", 0.3, f"Translating {segments_count} segments...")
            await self.model_manager.ensure_model(self.model)

            batches = chunk_segments(segments)

            def _on_translate_progress(completed: int, total: int):
                progress = 0.3 + (0.5 * completed / max(total, 1))
                self._emit(
                    "translating",
                    progress,
                    f"{completed}/{total} segments translated",
                )

            translated_count = await self.translator.translate_all(
                batches, file_type, glossary, on_progress=_on_translate_progress
            )

            logger.info(f"[{job_id}] Translated {translated_count} segments")

            # ── PHASE 3: RECONSTRUCTING (deterministic) ──
            self._emit("reconstructing", 0.8, "Rebuilding file...")

            if file_type in ("txt", "md", "csv"):
                result_path = reconstruct_plaintext(file_path, segments, output_path)
            else:
                result_path = reconstruct_document(
                    file_type=file_type,
                    file_path=file_path,
                    segments=segments,
                    output_path=output_path,
                )

            # ── PHASE 4: VERIFYING ──
            self._emit("verifying", 0.95, "Checking output...")

            if not os.path.exists(result_path):
                raise FileNotFoundError(f"Output file not found: {result_path}")

            duration = time.time() - start_time
            self._emit("completed", 1.0, f"Done in {duration:.1f}s!")

            logger.info(f"[{job_id}] Completed in {duration:.1f}s")

            return {
                "status": "completed",
                "output_path": result_path,
                "segments_count": segments_count,
                "duration_seconds": duration,
                "error": None,
            }

        except Exception as e:
            duration = time.time() - start_time
            error_msg = str(e)
            logger.error(f"[{job_id}] Failed: {error_msg}")
            self._emit("failed", 0.0, f"Error: {error_msg[:200]}")

            return {
                "status": "failed",
                "output_path": None,
                "segments_count": segments_count,
                "duration_seconds": duration,
                "error": error_msg,
            }
