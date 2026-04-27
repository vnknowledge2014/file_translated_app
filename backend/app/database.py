"""Async SurrealDB database client with CRUD operations for job tracking."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from surrealdb import Surreal
from app.config import settings
from app.models import GlossaryTerm, Job, JobAttempt, SegmentReview

# Global SurrealDB client
db = Surreal(settings.SURREALDB_URL)


async def init_db() -> None:
    """Initialize database connection."""
    await db.connect()
    await db.signin({
        "user": settings.SURREALDB_USER,
        "pass": settings.SURREALDB_PASS
    })
    await db.use(settings.SURREALDB_NS, settings.SURREALDB_DB)


async def close_db() -> None:
    """Close database connection."""
    await db.close()


async def create_job(
    filename: str,
    file_type: str,
    file_path: str,
    domain: str = "general",
    source_lang: str = "ja",
    target_lang: str = "vi",
    owner_id: str | None = None,
) -> Job:
    """Create new job with status='pending'."""
    job_id = uuid.uuid4().hex
    record_id = f"jobs:{job_id}"
    
    now = datetime.now(timezone.utc)
    data = {
        "id": record_id,
        "filename": filename,
        "file_type": file_type,
        "file_path": file_path,
        "domain": domain,
        "source_lang": source_lang,
        "target_lang": target_lang,
        "owner_id": owner_id,
        "status": "pending",
        "progress": 0.0,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }
    
    result = await db.create(record_id, data)
    # create() returns a list of created records, or the record itself depending on version.
    res_data = result[0] if isinstance(result, list) and len(result) > 0 else result
    return Job(**res_data)


async def get_job(job_id: str) -> Job | None:
    """Get job by ID."""
    # Ensure job_id doesn't have the table prefix if passed with it
    clean_id = job_id.split(':')[-1]
    result = await db.select(f"jobs:{clean_id}")
    if not result:
        return None
    return Job(**result)


async def update_job_status(
    job_id: str,
    status: str,
    **kwargs: Any,
) -> None:
    """Update job status and optional fields."""
    clean_id = job_id.split(':')[-1]
    now = datetime.now(timezone.utc).isoformat()
    
    data = {
        "status": status,
        "updated_at": now,
        **kwargs
    }
    await db.merge(f"jobs:{clean_id}", data)


async def add_job_attempt(
    job_id: str,
    attempt: int,
    phase: str,
    code: str | None,
    stderr: str | None,
    success: bool,
    duration: float | None = None,
    error_message: str | None = None,
) -> JobAttempt:
    """Log a job attempt for debugging."""
    data = {
        "job_id": job_id,
        "attempt_number": attempt,
        "phase": phase,
        "code_generated": code,
        "stderr": stderr,
        "success": success,
        "duration_seconds": duration,
        "error_message": error_message,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    result = await db.create("job_attempts", data)
    res_data = result[0] if isinstance(result, list) and len(result) > 0 else result
    
    # Create graph edge relating job to attempt
    clean_id = job_id.split(':')[-1]
    await db.query(f"RELATE jobs:{clean_id}->has_attempt->{res_data['id']}")
    
    return JobAttempt(**res_data)


async def get_job_attempts(job_id: str) -> list[JobAttempt]:
    """Get all attempts for a job."""
    clean_id = job_id.split(':')[-1]
    result = await db.query(
        "SELECT * FROM job_attempts WHERE job_id = $job_id ORDER BY attempt_number ASC",
        {"job_id": job_id}
    )
    # query() returns a list of results per statement
    records = result[0].get("result", [])
    return [JobAttempt(**r) for r in records]


async def get_table_names() -> list[str]:
    """Return all table names in the database."""
    result = await db.query("INFO FOR DB;")
    tables = result[0].get("result", {}).get("tables", {})
    return list(tables.keys())


async def list_jobs(limit: int = 20, owner_id: str | None = None) -> list[Job]:
    """List recent translation jobs, newest first."""
    if owner_id:
        result = await db.query("SELECT * FROM jobs WHERE owner_id = $owner_id ORDER BY created_at DESC LIMIT $limit", {"limit": limit, "owner_id": owner_id})
    else:
        result = await db.query("SELECT * FROM jobs ORDER BY created_at DESC LIMIT $limit", {"limit": limit})
    records = result[0].get("result", [])
    return [Job(**r) for r in records]


async def save_segments(
    job_id: str,
    segments: list[dict],
    high_threshold: float = 0.85,
) -> None:
    """Bulk-save translated segments for Review Editor."""
    clean_id = job_id.split(':')[-1]
    
    # Prepare batch data
    now = datetime.now(timezone.utc).isoformat()
    to_insert = []
    
    for idx, seg in enumerate(segments):
        source = seg.get("text", "").strip()
        if not source:
            continue
        confidence = seg.get("confidence", 0.0)
        status = "approved" if confidence >= high_threshold else "pending"
        
        to_insert.append({
            "job_id": job_id,
            "index": idx,
            "source": source,
            "target": seg.get("translated_text", ""),
            "confidence": confidence,
            "status": status,
            "location": seg.get("location", ""),
            "created_at": now
        })
        
    if to_insert:
        # Create segments
        for seg_data in to_insert:
            res = await db.create("segment_reviews", seg_data)
            res_data = res[0] if isinstance(res, list) and len(res) > 0 else res
            # Relate to job
            await db.query(f"RELATE jobs:{clean_id}->has_segment->{res_data['id']}")


async def get_segments(
    job_id: str,
    filter_status: str | None = None,
) -> list[SegmentReview]:
    """Get segments for a job, optionally filtered by status."""
    if filter_status:
        statuses = [s.strip() for s in filter_status.split(",")]
        result = await db.query(
            "SELECT * FROM segment_reviews WHERE job_id = $job_id AND status IN $statuses ORDER BY index ASC",
            {"job_id": job_id, "statuses": statuses}
        )
    else:
        result = await db.query(
            "SELECT * FROM segment_reviews WHERE job_id = $job_id ORDER BY index ASC",
            {"job_id": job_id}
        )
        
    records = result[0].get("result", [])
    return [SegmentReview(**r) for r in records]


async def update_segment(
    job_id: str,
    index: int,
    edited_text: str,
) -> SegmentReview | None:
    """Update a single segment's edited text."""
    result = await db.query(
        "UPDATE segment_reviews SET edited = $edited, status = 'edited' WHERE job_id = $job_id AND index = $index RETURN AFTER",
        {"job_id": job_id, "index": index, "edited": edited_text}
    )
    records = result[0].get("result", [])
    if records:
        return SegmentReview(**records[0])
    return None


async def approve_high_segments(
    job_id: str,
    threshold: float = 0.85,
) -> int:
    """Approve all HIGH-confidence segments in bulk."""
    result = await db.query(
        "UPDATE segment_reviews SET status = 'approved' WHERE job_id = $job_id AND confidence >= $threshold AND status = 'pending'",
        {"job_id": job_id, "threshold": threshold}
    )
    records = result[0].get("result", [])
    return len(records)


async def get_all_glossary_terms(
    source_lang: str | None = None,
    target_lang: str | None = None,
    domain: str | None = None,
    owner_id: str | None = None,
) -> list[GlossaryTerm]:
    """Get all glossary terms, optionally filtered by language pair and domain."""
    query = "SELECT * FROM glossary"
    conds = []
    params = {}
    
    if owner_id:
        conds.append("owner_id = $owner_id")
        params["owner_id"] = owner_id
    
    if source_lang:
        conds.append("source_lang = $sl")
        params["sl"] = source_lang
    if target_lang:
        conds.append("target_lang = $tl")
        params["tl"] = target_lang
    if domain:
        conds.append("domain = $dom")
        params["dom"] = domain
        
    if conds:
        query += " WHERE " + " AND ".join(conds)
        
    query += " ORDER BY created_at ASC"
    
    result = await db.query(query, params)
    records = result[0].get("result", [])
    return [GlossaryTerm(**r) for r in records]


async def add_glossary_terms(
    terms: list[dict],
    replace: bool = True,
    source_lang: str = "ja",
    target_lang: str = "vi",
    domain: str = "general",
    owner_id: str | None = None,
) -> int:
    """Add new glossary terms from a list of dicts."""
    if replace:
        if owner_id:
            await db.query(
                "DELETE glossary WHERE source_lang = $sl AND target_lang = $tl AND domain = $dom AND owner_id = $owner_id",
                {"sl": source_lang, "tl": target_lang, "dom": domain, "owner_id": owner_id}
            )
        else:
            await db.query(
                "DELETE glossary WHERE source_lang = $sl AND target_lang = $tl AND domain = $dom",
                {"sl": source_lang, "tl": target_lang, "dom": domain}
            )

    added = 0
    now = datetime.now(timezone.utc).isoformat()
    
    for t in terms:
        source_text = str(t.get("source_text") or t.get("jp", "")).strip()
        target_text = str(t.get("target_text") or t.get("vi", "")).strip()
        context = str(t.get("context", "")).strip()

        if not source_text or not target_text:
            continue
        
        if not replace:
            # Check existence
            exists = await db.query(
                "SELECT * FROM glossary WHERE source_text = $st AND source_lang = $sl AND target_lang = $tl AND domain = $dom",
                {"st": source_text, "sl": source_lang, "tl": target_lang, "dom": domain}
            )
            if exists[0].get("result", []):
                continue
                
        term_data = {
            "source_lang": source_lang,
            "target_lang": target_lang,
            "domain": domain,
            "owner_id": owner_id,
            "source_text": source_text,
            "target_text": target_text,
            "context": context if context else None,
            "created_at": now
        }
        await db.create("glossary", term_data)
        added += 1

    return added


async def delete_glossary_term(term_id: str) -> bool:
    """Delete a glossary term by ID."""
    clean_id = term_id if term_id.startswith("glossary:") else f"glossary:{term_id}"
    result = await db.delete(clean_id)
    return bool(result)
