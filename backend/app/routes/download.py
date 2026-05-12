"""Download route — GET /api/download/{job_id} → serve output file."""

import os

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.auth import get_current_user
from app.storage import storage

from app.database import get_job

router = APIRouter()


@router.get("/download/{job_id}")
async def download_file(
    request: Request,
    job_id: str,
    xliff: bool = False,
    current_user: dict = Depends(get_current_user),
):
    """Download translated document or its XLIFF representation.

    Returns 404 if job not found or not completed.
    Returns the file as attachment.
    """
    job = await get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.owner_id != current_user.get("id"):
        raise HTTPException(
            status_code=403, detail="Not authorized to download this file"
        )

    if job.status != "completed":
        return {"error": f"Job is not completed (status: {job.status})"}

    # Handle XLIFF download
    if xliff:
        if not job.xliff_path:
            return {"error": "XLIFF file not found for this job"}
        base, _ = os.path.splitext(job.filename)
        tl = getattr(job, 'target_lang', 'vi') or 'vi'
        dl_filename = f"{base}_{tl}.xlf"
        s3_uri = job.xliff_path
    else:
        if not job.output_path:
            return {"error": "Output file not found"}
        base, ext = os.path.splitext(job.filename)
        tl = getattr(job, 'target_lang', 'vi') or 'vi'
        dl_filename = f"{base}_{tl}{ext}"
        s3_uri = job.output_path

    try:
        bucket, object_name = storage.parse_s3_uri(s3_uri)
    except ValueError:
        return {"error": "Invalid file path in database"}

    return StreamingResponse(
        storage.get_object_stream(bucket, object_name),
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{dl_filename}"'},
    )
