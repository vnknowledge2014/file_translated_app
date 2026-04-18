"""Download route — GET /api/download/{job_id} → serve output file."""

import os

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse

from app.database import get_job

router = APIRouter()


@router.get("/download/{job_id}")
async def download_file(request: Request, job_id: str, xliff: bool = False):
    """Download translated document or its XLIFF representation.

    Returns 404 if job not found or not completed.
    Returns the file as attachment.
    """
    async with request.app.state.db_session_factory() as session:
        job = await get_job(session, job_id)
        if not job:
            return {"error": "Job not found"}

        if job.status != "completed":
            return {"error": f"Job is not completed (status: {job.status})"}

        # Handle XLIFF download
        if xliff:
            if not job.xliff_path or not os.path.exists(job.xliff_path):
                return {"error": "XLIFF file not found for this job"}
            base, _ = os.path.splitext(job.filename)
            dl_filename = f"{base}_vi.xlf"
            file_path = job.xliff_path
        else:
            if not job.output_path or not os.path.exists(job.output_path):
                return {"error": "Output file not found"}
            base, ext = os.path.splitext(job.filename)
            dl_filename = f"{base}_vi{ext}"
            file_path = job.output_path

        return FileResponse(
            path=file_path,
            filename=dl_filename,
            media_type="application/octet-stream",
        )
