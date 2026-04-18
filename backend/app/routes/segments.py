"""Segments API — GET/PUT/POST for Review Editor."""

import logging
import os

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.config import settings
from app.database import (
    get_job,
    get_segments,
    update_segment,
    approve_high_segments,
    save_segments,
)

router = APIRouter()
logger = logging.getLogger(__name__)


class SegmentEdit(BaseModel):
    """Request body for editing a segment."""
    edited: str


@router.get("/jobs/{job_id}/segments")
async def list_segments(request: Request, job_id: str, filter: str | None = None):
    """Get segments for a job.

    Query params:
        filter: Optional comma-separated statuses (pending, approved, edited).

    Returns:
        List of segment dicts with source, target, edited, confidence, status.
    """
    async with request.app.state.db_session_factory() as session:
        job = await get_job(session, job_id)
        if not job:
            return {"error": "Job not found"}

        segments = await get_segments(session, job_id, filter_status=filter)
        return {
            "job_id": job_id,
            "filename": job.filename,
            "total": job.segments_count or len(segments),
            "segments": [
                {
                    "index": s.index,
                    "source": s.source,
                    "target": s.target,
                    "edited": s.edited,
                    "confidence": s.confidence,
                    "status": s.status,
                    "location": s.location,
                }
                for s in segments
            ],
        }


@router.put("/jobs/{job_id}/segments/{index}")
async def edit_segment(request: Request, job_id: str, index: int, body: SegmentEdit):
    """Update a single segment's translated text.

    Args:
        index: Segment index (0-based).
        body: {"edited": "new translated text"}

    Returns:
        Updated segment data.
    """
    async with request.app.state.db_session_factory() as session:
        seg = await update_segment(session, job_id, index, body.edited)
        if not seg:
            return {"error": "Segment not found"}
        return {
            "index": seg.index,
            "source": seg.source,
            "target": seg.target,
            "edited": seg.edited,
            "confidence": seg.confidence,
            "status": seg.status,
        }


@router.post("/jobs/{job_id}/segments/approve-all")
async def approve_all(request: Request, job_id: str):
    """Approve all HIGH-confidence segments in bulk.

    Returns:
        Count of approved segments.
    """
    async with request.app.state.db_session_factory() as session:
        count = await approve_high_segments(session, job_id)
        return {"approved": count}


@router.post("/jobs/{job_id}/segments/reconstruct")
async def reconstruct_from_editor(request: Request, job_id: str):
    """Reconstruct output file using reviewed segments.

    Uses edited text where available, falls back to LLM target.
    Returns the reconstructed file as download.
    """
    from app.agent.extractor import extract_document
    from app.agent.reconstructor import reconstruct_document, reconstruct_plaintext

    async with request.app.state.db_session_factory() as session:
        job = await get_job(session, job_id)
        if not job:
            return {"error": "Job not found"}

        segments = await get_segments(session, job_id)
        if not segments:
            return {"error": "No segments found for this job"}

    # Re-extract original segments to get full metadata (location, type, etc.)
    original_segments = extract_document(job.file_type, job.file_path)

    # Build lookup: index → best translation (edited > target)
    edit_map = {}
    for s in segments:
        best = s.edited if s.edited and s.edited.strip() else s.target
        if best:
            edit_map[s.index] = best

    # Merge into original segments
    for idx, seg in enumerate(original_segments):
        if idx in edit_map:
            seg["translated_text"] = edit_map[idx]

    # Reconstruct
    base, ext = os.path.splitext(job.filename)
    output_filename = f"{base}_reviewed{ext}"
    output_path = os.path.join(settings.OUTPUT_DIR, output_filename)
    os.makedirs(settings.OUTPUT_DIR, exist_ok=True)

    if job.file_type in ("txt", "md", "csv"):
        reconstruct_plaintext(job.file_path, original_segments, output_path)
    else:
        reconstruct_document(job.file_type, job.file_path, original_segments, output_path)

    logger.info(f"[{job_id}] Reconstructed from editor → {output_path}")

    return FileResponse(
        output_path,
        media_type="application/octet-stream",
        filename=output_filename,
    )
