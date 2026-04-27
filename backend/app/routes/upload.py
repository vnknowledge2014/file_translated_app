"""Upload route — POST /api/upload → save file + create job + queue to worker pool."""

import logging
import os
import uuid

from fastapi import APIRouter, File, Request, UploadFile, Form, Depends
from app.auth import get_current_user
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
    current_user: dict = Depends(get_current_user),
):
    """Upload a document for translation.

    Validates file type, saves to upload dir, creates job record,
    and submits to the worker pool queue.

    Returns:
        {"job_id": str, "filename": str, "file_type": str, "status": "queued",
         "queue_position": int}
    """
    # Validate file type
    safe_filename = (file.filename or "unknown").replace("/", "").replace("\\", "")
    file_type = detect_file_type(safe_filename)
    if not file_type:
        return {"error": f"Unsupported file type: {safe_filename}"}

    # Save to upload directory with unique prefix to prevent overwrite
    unique_prefix = uuid.uuid4().hex[:8]
    upload_filename = f"{unique_prefix}_{safe_filename}"
    upload_path = os.path.join(settings.UPLOAD_DIR, upload_filename)
    os.makedirs(os.path.dirname(upload_path), exist_ok=True)

    with open(upload_path, "wb") as f:
        content = await file.read()
        f.write(content)

    # Create job record
    job = await create_job(
        filename=safe_filename,
        file_type=file_type,
        file_path=upload_path,
        domain=domain or settings.DEFAULT_DOMAIN,
        source_lang=source_lang or settings.SOURCE_LANG,
        target_lang=target_lang or settings.TARGET_LANG,
        owner_id=current_user.get("id"),
    )
    job_id = job.id

    # Submit to worker pool (bounded by MAX_WORKERS)
    pool = request.app.state.worker_pool
    await pool.submit(JobItem(
        app=request.app,
        job_id=job_id,
        file_path=upload_path,
        file_type=file_type,
        filename=safe_filename,
        export_xliff=export_xliff,
        xliff_version=xliff_version,
        domain=domain or settings.DEFAULT_DOMAIN,
        source_lang=source_lang or settings.SOURCE_LANG,
        target_lang=target_lang or settings.TARGET_LANG,
    ))

    return {
        "job_id": job_id,
        "filename": safe_filename,
        "file_type": file_type,
        "status": "queued",
        "queue_depth": pool.queue_size,
        "active_jobs": pool.active_count,
    }
