"""Job Worker Pool — bounded concurrency for translation pipelines.

Uses asyncio.Queue + consumer tasks to enforce MAX_WORKERS limit.
Prevents OOM on 16GB RAM when multiple files are uploaded simultaneously.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class JobItem:
    """A queued translation job."""
    app: Any
    job_id: str
    file_path: str
    file_type: str
    filename: str
    export_xliff: bool
    xliff_version: str
    domain: str = "general"
    source_lang: str = "ja"
    target_lang: str = "vi"


class WorkerPool:
    """Bounded worker pool for translation pipelines.

    Enforces MAX_WORKERS concurrency limit so that only N jobs
    run simultaneously. Additional uploads are queued and processed
    in FIFO order.

    Usage:
        pool = WorkerPool(max_workers=1)
        await pool.start()        # Start consumer tasks
        await pool.submit(job)    # Queue a job (non-blocking)
        await pool.shutdown()     # Graceful shutdown
    """

    def __init__(self, max_workers: int | None = None):
        self.max_workers = max_workers or settings.MAX_WORKERS
        self._queue: asyncio.Queue[JobItem | None] = asyncio.Queue()
        self._workers: list[asyncio.Task] = []
        self._active_jobs: set[str] = set()
        self._started = False

    @property
    def queue_size(self) -> int:
        """Number of jobs waiting in queue."""
        return self._queue.qsize()

    @property
    def active_count(self) -> int:
        """Number of jobs currently being processed."""
        return len(self._active_jobs)

    async def start(self) -> None:
        """Start worker consumer tasks."""
        if self._started:
            return
        self._started = True
        for i in range(self.max_workers):
            task = asyncio.create_task(
                self._worker_loop(i), name=f"worker-{i}"
            )
            self._workers.append(task)
        logger.info(
            f"WorkerPool started with {self.max_workers} worker(s)"
        )

    async def submit(self, job: JobItem) -> None:
        """Submit a job to the queue (non-blocking).

        Args:
            job: JobItem to process.
        """
        await self._queue.put(job)
        logger.info(
            f"[{job.job_id}] Job queued. "
            f"Queue depth: {self._queue.qsize()}, "
            f"Active: {len(self._active_jobs)}"
        )

    async def shutdown(self) -> None:
        """Gracefully shutdown all workers.

        Sends poison pills and waits for workers to finish
        their current jobs.
        """
        logger.info("WorkerPool shutting down...")
        # Send poison pill (None) for each worker
        for _ in self._workers:
            await self._queue.put(None)
        # Wait for all workers to finish
        if self._workers:
            await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers.clear()
        self._started = False
        logger.info("WorkerPool shutdown complete")

    async def _worker_loop(self, worker_id: int) -> None:
        """Consumer loop — pull jobs from queue and run pipeline."""
        logger.debug(f"Worker-{worker_id} started")
        while True:
            job = await self._queue.get()
            if job is None:
                # Poison pill — exit
                self._queue.task_done()
                logger.debug(f"Worker-{worker_id} received shutdown signal")
                break

            self._active_jobs.add(job.job_id)
            try:
                logger.info(
                    f"Worker-{worker_id} processing [{job.job_id}] "
                    f"{job.filename}"
                )
                await self._run_pipeline(job)
            except Exception as e:
                logger.error(
                    f"Worker-{worker_id} [{job.job_id}] unhandled error: {e}",
                    exc_info=True,
                )
            finally:
                self._active_jobs.discard(job.job_id)
                self._queue.task_done()

    async def _run_pipeline(self, job: JobItem) -> None:
        """Run the translation pipeline for a single job.

        This is the same logic as the old _run_pipeline in upload.py,
        extracted here for worker pool management.
        """
        import os
        from app.agent.orchestrator import Orchestrator
        from app.agent.translator import Translator
        from app.ollama.model_manager import ModelManager
        from app.llm.factory import create_llm_client
        from app.database import update_job_status, save_segments, get_all_glossary_terms

        app = job.app

        # Create fresh client per job (avoids shared state corruption)
        client = create_llm_client(
            url=settings.OLLAMA_URL,
            timeout=settings.OLLAMA_TIMEOUT,
        )

        try:
            model_manager = ModelManager(client)
            translator = Translator(
                client, settings.MODEL,
                max_concurrent=settings.MAX_CONCURRENT_BATCHES,
            )

            # Build output path
            base, ext = os.path.splitext(job.filename)
            output_filename = f"{base}_{settings.TARGET_LANG}{ext}"
            output_path = os.path.join(settings.OUTPUT_DIR, output_filename)

            # Progress callback
            _pending_progress: list[asyncio.Task] = []

            async def _on_progress(phase: str, progress: float, message: str):
                if phase in ("completed", "failed"):
                    return
                try:
                    await update_job_status(
                        job.job_id, phase,
                        progress=progress,
                        progress_message=message,
                    )
                except Exception:
                    pass

            def _fire_progress(phase: str, progress: float, msg: str):
                fut = asyncio.ensure_future(_on_progress(phase, progress, msg))
                _pending_progress.append(fut)

            orchestrator = Orchestrator(
                model_manager=model_manager,
                translator=translator,
                model=settings.MODEL,
                on_progress=_fire_progress,
            )

            # Fetch glossary terms for the active language pair and domain
            glossary_models = await get_all_glossary_terms(
                source_lang=settings.SOURCE_LANG,
                target_lang=settings.TARGET_LANG,
                domain=job.domain,
            )
            glossary_dicts = [
                {
                    "source_text": g.source_text,
                    "target_text": g.target_text,
                    "context": g.context,
                }
                for g in glossary_models
            ]

            result = await orchestrator.translate_file(
                file_path=job.file_path,
                file_type=job.file_type,
                job_id=job.job_id,
                output_path=output_path,
                export_xliff_flag=job.export_xliff,
                xliff_version=job.xliff_version,
                glossary=glossary_dicts,
                domain_code=job.domain,
                source_lang=job.source_lang,
                target_lang=job.target_lang,
            )

            # Await all pending progress callbacks
            if _pending_progress:
                await asyncio.gather(*_pending_progress, return_exceptions=True)
                _pending_progress.clear()

            # Final DB update
            final_progress = 1.0 if result["status"] == "completed" else 0.0
            final_msg = (
                f"Hoàn thành! {result.get('segments_count', 0)} đoạn, "
                f"{(result.get('duration_seconds') or 0):.1f}s"
                if result["status"] == "completed"
                else result.get("error", "Lỗi")
            )
            await update_job_status(
                job.job_id,
                status=result["status"],
                progress=final_progress,
                progress_message=final_msg,
                output_path=result.get("output_path"),
                xliff_path=result.get("xliff_path"),
                segments_count=result.get("segments_count"),
                duration_seconds=result.get("duration_seconds"),
                error_message=result.get("error"),
            )

            logger.info(f"[{job.job_id}] Pipeline finished: {result['status']}")

            # Save segments for Review Editor
            if result["status"] == "completed" and result.get("_segments"):
                try:
                    await save_segments(
                        job.job_id, result["_segments"]
                    )
                    logger.info(
                        f"[{job.job_id}] Saved {len(result['_segments'])} "
                        f"segments for review"
                    )
                except Exception as seg_err:
                    logger.warning(
                        f"[{job.job_id}] Failed to save segments: {seg_err}"
                    )

        except Exception as e:
            error_msg = f"{type(e).__name__}: {e}"
            logger.error(
                f"[{job.job_id}] Pipeline crashed: {error_msg}", exc_info=True
            )
            try:
                await update_job_status(
                    job.job_id, "failed",
                    error_message=error_msg[:500],
                )
            except Exception as db_err:
                logger.critical(
                    f"[{job.job_id}] CRITICAL: DB update failed: {db_err}"
                )
        finally:
            await client.close()
