"""Job listing, detail, retry, and delete routes."""

from fastapi import APIRouter, Request, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.auth import get_current_user, authenticate_token
from app.database import get_job, get_job_attempts, list_jobs, update_job_status, db
from app.storage import storage

router = APIRouter()


@router.get("/jobs")
async def list_all_jobs(
    request: Request,
    status: str = Query(None),
    current_user: dict = Depends(get_current_user),
):
    """List recent translation jobs.

    Returns:
        List of recent jobs with status, filename, etc.
    """
    jobs = await list_jobs(owner_id=current_user.get("id"), status=status)
    return [
        {
            "id": j.id,
            "filename": j.filename,
            "file_type": j.file_type,
            "status": j.status,
            "progress": j.progress,
            "progress_message": j.progress_message,
            "error_message": j.error_message,
            "segments_count": j.segments_count,
            "xliff_path": getattr(j, "xliff_path", None),
            "duration_seconds": j.duration_seconds,
            "source_lang": getattr(j, "source_lang", None),
            "target_lang": getattr(j, "target_lang", None),
            "created_at": str(j.created_at) if j.created_at else None,
        }
        for j in jobs
    ]


@router.get("/jobs/stream")
async def stream_job_events(request: Request, token: str = Query(...)):
    """SSE endpoint — streams job status updates to the browser.

    Uses `token` query parameter because EventSource API doesn't
    support setting custom Authorization headers.
    """
    import asyncio
    import json
    from app.event_bus import event_bus

    # Authenticate manually via query token
    user = await authenticate_token(token)
    user_id = user.get("id")

    queue = event_bus.subscribe(user_id)

    async def event_generator():
        try:
            # 1. Send initial job list as the first event (with timeout)
            jobs = await asyncio.wait_for(list_jobs(owner_id=user_id), timeout=10.0)
            initial_data = [
                {
                    "id": j.id,
                    "filename": j.filename,
                    "file_type": j.file_type,
                    "status": j.status,
                    "progress": j.progress,
                    "progress_message": j.progress_message,
                    "error_message": j.error_message,
                    "segments_count": j.segments_count,
                    "xliff_path": getattr(j, "xliff_path", None),
                    "duration_seconds": j.duration_seconds,
                    "source_lang": getattr(j, "source_lang", None),
                    "target_lang": getattr(j, "target_lang", None),
                    "created_at": str(j.created_at) if j.created_at else None,
                }
                for j in jobs
            ]
            yield f"event: init\ndata: {json.dumps(initial_data)}\n\n"

            # 2. Stream subsequent updates
            while True:
                if await request.is_disconnected():
                    break

                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield event.to_sse()
                except asyncio.TimeoutError:
                    # Send keepalive comment to prevent connection drop
                    yield ": keepalive\n\n"
        finally:
            event_bus.unsubscribe(user_id, queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Required for Nginx reverse proxy
        },
    )


@router.get("/jobs/{job_id}")
async def get_job_detail(
    request: Request, job_id: str, current_user: dict = Depends(get_current_user)
):
    """Get job status and details.

    Returns:
        Job details with status, filename, output_path, etc.
    """
    job = await get_job(job_id)
    if not job:
        return {"error": "Job not found"}

    if job.owner_id != current_user.get("id"):
        raise HTTPException(status_code=403, detail="Not authorized to view this job")

    attempts = await get_job_attempts(job_id)

    return {
        "id": job.id,
        "filename": job.filename,
        "file_type": job.file_type,
        "status": job.status,
        "progress": job.progress,
        "progress_message": job.progress_message,
        "error_message": job.error_message,
        "segments_count": job.segments_count,
        "output_path": job.output_path,
        "xliff_path": getattr(job, "xliff_path", None),
        "duration_seconds": job.duration_seconds,
        "source_lang": getattr(job, "source_lang", None),
        "target_lang": getattr(job, "target_lang", None),
        "created_at": str(job.created_at) if job.created_at else None,
        "updated_at": str(job.updated_at) if job.updated_at else None,
        "attempts": [
            {
                "attempt": a.attempt_number,
                "phase": a.phase,
                "success": a.success,
                "error_message": a.error_message,
                "duration_seconds": a.duration_seconds,
            }
            for a in attempts
        ],
    }


@router.post("/jobs/{job_id}/retry")
async def retry_job(
    request: Request,
    job_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Retry a failed or stuck translation job.

    Re-queues the job using the original uploaded file (still on MinIO).
    Clears old output, segments, and attempts before re-processing.

    Returns:
        {job_id, status, queue_depth, active_jobs}
    """
    import logging

    logger = logging.getLogger(__name__)

    job = await get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Ownership check
    if job.owner_id != current_user.get("id"):
        raise HTTPException(status_code=403, detail="Not authorized")

    pool = request.app.state.worker_pool

    # Prevent concurrent processing:
    # Block if it's newly queued, or if it's actively running in the worker pool
    if job.status == "queued" or job_id in pool._active_jobs:
        raise HTTPException(
            status_code=400,
            detail="Job is already queued or actively processing. Cannot retry.",
        )

    # Verify original file still exists in MinIO
    try:
        bucket, object_name = storage.parse_s3_uri(job.file_path)
        if not storage.object_exists(bucket, object_name):
            raise HTTPException(
                status_code=410,
                detail="Original file no longer exists on storage. Please re-upload.",
            )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid file path in job record")

    # Clean up old outputs from MinIO
    clean_id = job_id.split(":")[-1]
    storage.delete_job_outputs(clean_id)

    # Clean up old DB records (segments + attempts)
    await db.query(
        "DELETE segment_reviews WHERE job_id = $jid",
        {"jid": job_id},
    )
    await db.query(
        "DELETE job_attempts WHERE job_id = $jid",
        {"jid": job_id},
    )

    # Reset job status
    await update_job_status(
        job_id,
        status="queued",
        progress=0.0,
        progress_message=None,
        error_message=None,
        output_path=None,
        xliff_path=None,
        segments_count=None,
        duration_seconds=None,
    )

    # Re-submit to worker pool
    from app.worker import JobItem
    from app.config import settings

    await pool.submit(
        JobItem(
            app=request.app,
            job_id=job_id,
            file_path=job.file_path,
            file_type=job.file_type,
            filename=job.filename,
            export_xliff=bool(getattr(job, "xliff_path", None)),
            xliff_version="2.1",
            domain=getattr(job, "domain", settings.DEFAULT_DOMAIN),
            source_lang=getattr(job, "source_lang", settings.SOURCE_LANG),
            target_lang=getattr(job, "target_lang", settings.TARGET_LANG),
            owner_id=job.owner_id,
        )
    )

    logger.info(f"[{job_id}] Job retried by user {current_user.get('id')}")

    # Emit event so UI updates instantly
    from app.event_bus import event_bus, JobEvent

    await event_bus.publish(
        JobEvent(
            job_id=job_id,
            owner_id=job.owner_id or "",
            event_type="queued",
            data={"status": "queued", "progress": 0.0, "message": "Job retried..."},
        )
    )

    return {
        "job_id": job_id,
        "status": "queued",
        "queue_depth": pool.queue_size,
        "active_jobs": pool.active_count,
    }


@router.delete("/jobs/{job_id}")
async def delete_job(
    request: Request,
    job_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Permanently delete a job and ALL associated files.

    Removes:
    - Original uploaded file from MinIO (uploads bucket)
    - Output files from MinIO (outputs bucket)
    - Segment reviews from SurrealDB
    - Job attempts from SurrealDB
    - The job record itself

    Returns:
        {message: "Job deleted"}
    """
    import logging

    logger = logging.getLogger(__name__)

    job = await get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Ownership check
    if job.owner_id != current_user.get("id"):
        raise HTTPException(status_code=403, detail="Not authorized")

    clean_id = job_id.split(":")[-1]

    # 1. Delete original upload from MinIO
    try:
        bucket, object_name = storage.parse_s3_uri(job.file_path)
        storage.delete_object(bucket, object_name)
    except Exception as e:
        logger.warning(f"[{job_id}] Could not delete upload file: {e}")

    # 2. Delete all output files from MinIO
    storage.delete_job_outputs(clean_id)

    # 3. Delete DB records
    await db.query(
        "DELETE segment_reviews WHERE job_id = $jid",
        {"jid": job_id},
    )
    await db.query(
        "DELETE job_attempts WHERE job_id = $jid",
        {"jid": job_id},
    )
    await db.delete(f"jobs:{clean_id}")

    logger.info(f"[{job_id}] Job permanently deleted by user {current_user.get('id')}")

    return {"message": f"Job {job_id} deleted"}
