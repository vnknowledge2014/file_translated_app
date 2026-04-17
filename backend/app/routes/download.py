"""Download route — GET /api/download/{job_id} → serve output file."""

import os

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse

from app.database import get_job

router = APIRouter()


@router.get("/download/{job_id}")
async def download_file(request: Request, job_id: str):
    """Download translated document.

    Returns 404 if job not found or not completed.
    Returns the translated file as attachment.
    """
    async with request.app.state.db_session_factory() as session:
        job = await get_job(session, job_id)
        if not job:
            return {"error": "Job not found"}

        if job.status != "completed":
            return {"error": f"Job is not completed (status: {job.status})"}

        if not job.output_path or not os.path.exists(job.output_path):
            return {"error": "Output file not found"}

        # Build Vietnamese filename: report.docx → report_vi.docx
        base, ext = os.path.splitext(job.filename)
        vi_filename = f"{base}_vi{ext}"

        return FileResponse(
            path=job.output_path,
            filename=vi_filename,
            media_type="application/octet-stream",
        )
