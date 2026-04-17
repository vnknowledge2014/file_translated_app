"""Job listing and detail routes."""

from fastapi import APIRouter, Request

from app.database import get_job, get_job_attempts, list_jobs

router = APIRouter()


@router.get("/jobs")
async def list_all_jobs(request: Request):
    """List recent translation jobs.

    Returns:
        List of recent jobs with status, filename, etc.
    """
    async with request.app.state.db_session_factory() as session:
        jobs = await list_jobs(session)
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
                "duration_seconds": j.duration_seconds,
                "created_at": str(j.created_at) if j.created_at else None,
            }
            for j in jobs
        ]


@router.get("/jobs/{job_id}")
async def get_job_detail(request: Request, job_id: str):
    """Get job status and details.

    Returns:
        Job details with status, filename, output_path, etc.
    """
    async with request.app.state.db_session_factory() as session:
        job = await get_job(session, job_id)
        if not job:
            return {"error": "Job not found"}

        attempts = await get_job_attempts(session, job_id)

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
            "duration_seconds": job.duration_seconds,
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
