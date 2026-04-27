"""Upload route — POST /api/upload → save file + create job + queue to worker pool."""

import logging
import os

from fastapi import APIRouter, File, Request, UploadFile, Form

from app.config import settings
from app.database import create_job
from app.utils.file_detect import detect_file_type
from app.worker import JobItem

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/upload")
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    export_xliff: bool = Form(False),
    xliff_version: str = Form("2.1"),
    domain: str = Form(None),
    source_lang: str = Form(None),
    target_lang: str = Form(None),
):
    """Upload a document for translation.

    Validates file type, saves to upload dir, creates job record,
    and submits to the worker pool queue.

    Returns:
        {"job_id": str, "filename": str, "file_type": str, "status": "queued",
         "queue_position": int}
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
            domain=domain or settings.DEFAULT_DOMAIN,
            source_lang=source_lang or settings.SOURCE_LANG,
            target_lang=target_lang or settings.TARGET_LANG,
        )
        job_id = job.id

    # Submit to worker pool (bounded by MAX_WORKERS)
    pool = request.app.state.worker_pool
    await pool.submit(JobItem(
        app=request.app,
        job_id=job_id,
        file_path=upload_path,
        file_type=file_type,
        filename=file.filename or "unknown",
        export_xliff=export_xliff,
        xliff_version=xliff_version,
        domain=domain or settings.DEFAULT_DOMAIN,
        source_lang=source_lang or settings.SOURCE_LANG,
        target_lang=target_lang or settings.TARGET_LANG,
    ))

    return {
        "job_id": job_id,
        "filename": file.filename,
        "file_type": file_type,
        "status": "queued",
        "queue_depth": pool.queue_size,
        "active_jobs": pool.active_count,
    }
