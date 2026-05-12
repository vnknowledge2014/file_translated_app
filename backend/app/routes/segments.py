"""Segments API — GET/PUT/POST for Review Editor."""

import logging
import os

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.auth import get_current_user

from app.config import settings
from app.database import (
    get_job,
    get_segments,
    update_segment,
    approve_high_segments,
)

router = APIRouter()
logger = logging.getLogger(__name__)


class SegmentEdit(BaseModel):
    """Request body for editing a segment."""

    edited: str


@router.get("/jobs/{job_id}/segments")
async def list_segments(
    request: Request,
    job_id: str,
    filter: str | None = None,
    current_user: dict = Depends(get_current_user),
):
    """Get segments for a job.

    Query params:
        filter: Optional comma-separated statuses (pending, approved, edited).

    Returns:
        List of segment dicts with source, target, edited, confidence, status.
    """
    job = await get_job(job_id)
    if not job:
        return {"error": "Job not found"}

    if job.owner_id != current_user.get("id"):
        raise HTTPException(status_code=403, detail="Not authorized to view this job")

    segments = await get_segments(job_id, filter_status=filter)
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
async def edit_segment(
    request: Request,
    job_id: str,
    index: int,
    body: SegmentEdit,
    current_user: dict = Depends(get_current_user),
):
    """Update a single segment's translated text.

    Args:
        index: Segment index (0-based).
        body: {"edited": "new translated text"}

    Returns:
        Updated segment data.
    """
    job = await get_job(job_id)
    if not job or (job.owner_id != current_user.get("id")):
        raise HTTPException(status_code=403, detail="Not authorized")

    seg = await update_segment(job_id, index, body.edited)
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
async def approve_all(
    request: Request, job_id: str, current_user: dict = Depends(get_current_user)
):
    """Approve all HIGH-confidence segments in bulk.

    Returns:
        Count of approved segments.
    """
    job = await get_job(job_id)
    if not job or (job.owner_id != current_user.get("id")):
        raise HTTPException(status_code=403, detail="Not authorized")

    count = await approve_high_segments(job_id)
    return {"approved": count}


@router.post("/jobs/{job_id}/segments/reconstruct")
async def reconstruct_from_editor(
    request: Request, job_id: str, current_user: dict = Depends(get_current_user)
):
    """Reconstruct output file using reviewed segments.

    Uses edited text where available, falls back to LLM target.
    Returns the reconstructed file as download.
    """
    from app.agent.extractor import extract_document
    from app.agent.reconstructor import reconstruct_document, reconstruct_plaintext

    job = await get_job(job_id)
    if not job:
        return {"error": "Job not found"}

    if job.owner_id != current_user.get("id"):
        raise HTTPException(
            status_code=403, detail="Not authorized to reconstruct this job"
        )

    segments = await get_segments(job_id)
    if not segments:
        return {"error": "No segments found for this job"}

    from app.storage import storage
    import uuid

    # 1. Download original file from MinIO to TEMP_DIR
    bucket, object_name = storage.parse_s3_uri(job.file_path)
    temp_input_path = os.path.join(
        settings.TEMP_DIR,
        f"recon_in_{uuid.uuid4().hex}_{os.path.basename(object_name)}",
    )
    storage.download_file(bucket, object_name, temp_input_path)

    try:
        # Re-extract original segments to get full metadata (location, type, etc.)
        original_segments = extract_document(job.file_type, temp_input_path)

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
        temp_output_path = os.path.join(
            settings.TEMP_DIR, f"recon_out_{uuid.uuid4().hex}_{output_filename}"
        )

        if job.file_type in ("txt", "md", "csv"):
            reconstruct_plaintext(temp_input_path, original_segments, temp_output_path)
        else:
            reconstruct_document(
                job.file_type, temp_input_path, original_segments, temp_output_path
            )

        # Upload reviewed file to MinIO
        final_s3_uri = storage.upload_file(
            storage.outputs_bucket, f"{job_id}/{output_filename}", temp_output_path
        )
        logger.info(f"[{job_id}] Reconstructed from editor → {final_s3_uri}")

        # Stream the result
        return StreamingResponse(
            storage.get_object_stream(
                storage.outputs_bucket, f"{job_id}/{output_filename}"
            ),
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": f'attachment; filename="{output_filename}"'
            },
        )
    finally:
        # Clean up
        if os.path.exists(temp_input_path):
            os.remove(temp_input_path)
        if "temp_output_path" in locals() and os.path.exists(temp_output_path):
            os.remove(temp_output_path)
