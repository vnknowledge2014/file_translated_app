"""Upload route — POST /api/upload → save file + create job + start pipeline."""

import asyncio
import logging
import os
import shutil
import time

from fastapi import APIRouter, File, Request, UploadFile

from app.config import settings
from app.database import create_job, update_job_status
from app.ollama.client import OllamaClient
from app.utils.file_detect import detect_file_type

router = APIRouter()
logger = logging.getLogger(__name__)

# Track active pipeline tasks to prevent GC and enable monitoring
_active_tasks: set[asyncio.Task] = set()


def _on_pipeline_done(task: asyncio.Task) -> None:
    """Callback when pipeline task completes — log unhandled exceptions."""
    _active_tasks.discard(task)
    if task.cancelled():
        logger.warning(f"Pipeline task was cancelled: {task.get_name()}")
    elif exc := task.exception():
        logger.error(f"Pipeline task crashed with unhandled exception: {exc}", exc_info=exc)


async def _run_pipeline(app, job_id: str, file_path: str, file_type: str, filename: str):
    """Background task — runs the Orchestrator pipeline for a job.

    Uses a fresh OllamaClient per pipeline run to avoid shared state
    corruption after timeouts. Wraps all operations in bulletproof
    error handling so DB status is always updated.
    """
    from app.agent.orchestrator import Orchestrator
    from app.agent.translator import Translator
    from app.ollama.model_manager import ModelManager

    # Create fresh client for this pipeline run (not shared singleton)
    # This prevents timeout-corrupted state from affecting other requests
    client = OllamaClient(settings.OLLAMA_URL, timeout=settings.OLLAMA_TIMEOUT)

    try:
        model_manager = ModelManager(client)
        translator = Translator(
            client, settings.MODEL,
            max_concurrent=settings.MAX_CONCURRENT_BATCHES,
        )

        # Build output path
        base, ext = os.path.splitext(filename)
        output_filename = f"{base}_vi{ext}"
        output_path = os.path.join(settings.OUTPUT_DIR, output_filename)

        # Progress callback — updates DB status per pipeline phase
        # Skip 'completed'/'failed' — those are handled by the final explicit
        # update after translate_file returns (avoids race with ensure_future)
        _pending_progress: list[asyncio.Task] = []

        async def _on_progress(phase: str, progress: float, message: str):
            """Update job status and real progress in DB."""
            if phase in ("completed", "failed"):
                return  # Final state handled by explicit await below
            try:
                async with app.state.db_session_factory() as session:
                    await update_job_status(
                        session, job_id, phase,
                        progress=progress,
                        progress_message=message,
                    )
            except Exception:
                pass  # Non-critical — don't crash pipeline for status updates

        def _fire_progress(phase: str, progress: float, msg: str):
            """Fire progress update and track the future."""
            fut = asyncio.ensure_future(_on_progress(phase, progress, msg))
            _pending_progress.append(fut)

        orchestrator = Orchestrator(
            model_manager=model_manager,
            translator=translator,
            model=settings.MODEL,
            on_progress=_fire_progress,
        )

        # Initial status is set by the progress callback from Orchestrator
        result = await orchestrator.translate_file(
            file_path=file_path,
            file_type=file_type,
            job_id=job_id,
            output_path=output_path,
        )

        # CRITICAL: Await ALL pending progress callbacks before final write
        # This prevents lagging 'verifying' callbacks from overwriting 'completed'
        if _pending_progress:
            await asyncio.gather(*_pending_progress, return_exceptions=True)
            _pending_progress.clear()

        # Update DB with final result (authoritative — overrides any lagging callbacks)
        final_progress = 1.0 if result["status"] == "completed" else 0.0
        final_msg = (
            f"Hoàn thành! {result.get('segments_count', 0)} đoạn, "
            f"{(result.get('duration_seconds') or 0):.1f}s"
            if result["status"] == "completed"
            else result.get("error", "Lỗi")
        )
        async with app.state.db_session_factory() as session:
            await update_job_status(
                session, job_id,
                status=result["status"],
                progress=final_progress,
                progress_message=final_msg,
                output_path=result.get("output_path"),
                segments_count=result.get("segments_count"),
                duration_seconds=result.get("duration_seconds"),
                error_message=result.get("error"),
            )

        logger.info(f"[{job_id}] Pipeline finished: {result['status']}")

    except Exception as e:
        error_msg = f"{type(e).__name__}: {e}"
        logger.error(f"[{job_id}] Pipeline crashed: {error_msg}", exc_info=True)
        # Bulletproof DB update — this MUST succeed
        try:
            async with app.state.db_session_factory() as session:
                await update_job_status(
                    session, job_id, "failed", error_message=error_msg[:500]
                )
        except Exception as db_err:
            logger.critical(
                f"[{job_id}] CRITICAL: Failed to update DB after pipeline crash: {db_err}"
            )
    finally:
        # Always close the per-pipeline client
        await client.close()


@router.post("/upload")
async def upload_file(request: Request, file: UploadFile = File(...)):
    """Upload a document for translation.

    Validates file type, saves to upload dir, creates job record,
    and kicks off async translation pipeline.

    Returns:
        {"job_id": str, "filename": str, "file_type": str, "status": "pending"}
    """
    # Validate file type
    file_type = detect_file_type(file.filename or "")
    if not file_type:
        return {"error": f"Unsupported file type: {file.filename}"}

    # Save to upload directory
    upload_path = os.path.join(settings.UPLOAD_DIR, file.filename or "unknown")
    os.makedirs(os.path.dirname(upload_path), exist_ok=True)

    with open(upload_path, "wb") as f:
        content = await file.read()
        f.write(content)

    # Create job record
    async with request.app.state.db_session_factory() as session:
        job = await create_job(
            session,
            filename=file.filename or "unknown",
            file_type=file_type,
            file_path=upload_path,
        )
        job_id = job.id

    # Kick off pipeline in background with proper task tracking
    task = asyncio.create_task(
        _run_pipeline(request.app, job_id, upload_path, file_type, file.filename or "unknown"),
        name=f"pipeline-{job_id}",
    )
    _active_tasks.add(task)
    task.add_done_callback(_on_pipeline_done)

    return {
        "job_id": job_id,
        "filename": file.filename,
        "file_type": file_type,
        "status": "pending",
    }
