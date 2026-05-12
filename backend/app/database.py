"""Async SurrealDB database client with CRUD operations for job tracking."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from surrealdb import AsyncSurreal
from app.config import settings
from app.models import GlossaryTerm, Job, JobAttempt, SegmentReview

import logging
import asyncio

logger = logging.getLogger(__name__)


def _sanitize(data):
    """Recursively convert SurrealDB native types (like RecordID) to standard types."""
    if isinstance(data, list):
        return [_sanitize(x) for x in data]
    if isinstance(data, dict):
        return {k: _sanitize(v) for k, v in data.items()}
    if type(data).__name__ == "RecordID":
        return str(data)
    return data


class SafeSurrealDB:
    def __init__(self, url: str):
        self._url = url
        self._client = AsyncSurreal(url)
        self._lock = asyncio.Lock()
        self._credentials = None
        self._namespace = None
        self._database = None

    @property
    def client(self):
        return self._client

    async def connect(self):
        async with self._lock:
            return await self._client.connect()

    async def signin(self, credentials):
        self._credentials = credentials
        async with self._lock:
            return await self._client.signin(credentials)

    async def use(self, namespace, database):
        self._namespace = namespace
        self._database = database
        async with self._lock:
            return await self._client.use(namespace, database)

    async def close(self):
        async with self._lock:
            return await self._client.close()

    async def _reconnect(self):
        """Reconnect to SurrealDB after a dropped WebSocket."""
        logger.warning("SurrealDB WebSocket reconnecting...")
        try:
            await self._client.close()
        except Exception:
            pass
        self._client = AsyncSurreal(self._url)
        await self._client.connect()
        if self._credentials:
            await self._client.signin(self._credentials)
        if self._namespace and self._database:
            await self._client.use(self._namespace, self._database)
        logger.info("SurrealDB WebSocket reconnected successfully")

    async def _safe_call(self, method_name: str, *args, **kwargs):
        """Call a SurrealDB client method with auto-reconnect on failure."""
        async with self._lock:
            try:
                method = getattr(self._client, method_name)
                res = await method(*args, **kwargs)
                return _sanitize(res)
            except Exception as e:
                logger.warning(
                    f"SurrealDB {method_name} failed ({e}), attempting reconnect..."
                )
                try:
                    await self._reconnect()
                    method = getattr(self._client, method_name)
                    res = await method(*args, **kwargs)
                    return _sanitize(res)
                except Exception as e2:
                    logger.error(f"SurrealDB reconnect failed: {e2}")
                    raise

    async def query(self, *args, **kwargs):
        return await self._safe_call("query", *args, **kwargs)

    async def create(self, *args, **kwargs):
        return await self._safe_call("create", *args, **kwargs)

    async def select(self, *args, **kwargs):
        return await self._safe_call("select", *args, **kwargs)

    async def merge(self, *args, **kwargs):
        return await self._safe_call("merge", *args, **kwargs)

    async def delete(self, *args, **kwargs):
        return await self._safe_call("delete", *args, **kwargs)


# Global safe SurrealDB client
db = SafeSurrealDB(settings.SURREALDB_URL)

_initialized = False


async def _run_migrations() -> None:
    """Run database schema migrations (idempotent)."""
    migrations = [
        "DEFINE INDEX IF NOT EXISTS idx_jobs_owner ON jobs FIELDS owner_id",
        "DEFINE INDEX IF NOT EXISTS idx_jobs_status ON jobs FIELDS status",
        "DEFINE INDEX IF NOT EXISTS idx_jobs_created ON jobs FIELDS created_at",
        "DEFINE INDEX IF NOT EXISTS idx_glossary_pair ON glossary FIELDS source_lang, target_lang, domain",
        "DEFINE INDEX IF NOT EXISTS idx_glossary_owner ON glossary FIELDS owner_id",
        "DEFINE INDEX IF NOT EXISTS idx_cache_lookup ON translation_cache FIELDS source, source_lang, target_lang, model, domain",
        "DEFINE INDEX IF NOT EXISTS idx_cache_lang ON translation_cache FIELDS source_lang, target_lang, domain",
        "DEFINE INDEX IF NOT EXISTS idx_segments_job ON segment_reviews FIELDS job_id",
        "DEFINE INDEX IF NOT EXISTS idx_segments_status ON segment_reviews FIELDS job_id, status",
        "DEFINE INDEX IF NOT EXISTS idx_attempts_job ON job_attempts FIELDS job_id",
        "DEFINE INDEX IF NOT EXISTS idx_user_username ON user FIELDS username UNIQUE",
    ]

    success = 0
    for stmt in migrations:
        try:
            await db.query(stmt)
            success += 1
        except Exception as e:
            logger.warning(f"Migration skipped: {stmt[:60]}... — {e}")

    logger.info(f"Database migrations: {success}/{len(migrations)} applied")


async def init_db() -> None:
    """Initialize database connection and run migrations."""
    global _initialized
    if _initialized:
        return
    await db.connect()
    await db.signin(
        {"username": settings.SURREALDB_USER, "password": settings.SURREALDB_PASS}
    )
    await db.use(settings.SURREALDB_NS, settings.SURREALDB_DB)
    await _run_migrations()
    _initialized = True


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
    res_data = result[0] if isinstance(result, list) and len(result) > 0 else result
    return Job(**res_data)


async def get_job(job_id: str) -> Job | None:
    """Get job by ID."""
    clean_id = job_id.split(":")[-1]
    result = await db.select(f"jobs:{clean_id}")
    if not result:
        return None
    res_data = result[0] if isinstance(result, list) else result
    return Job(**res_data)


async def update_job_status(
    job_id: str,
    status: str,
    **kwargs: Any,
) -> None:
    """Update job status and optional fields."""
    clean_id = job_id.split(":")[-1]
    now = datetime.now(timezone.utc).isoformat()

    data = {"status": status, "updated_at": now, **kwargs}
    await db.query(
        "UPDATE type::record($job_id) MERGE $data", {"job_id": f"jobs:{clean_id}", "data": data}
    )


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
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    result = await db.create("job_attempts", data)
    res_data = result[0] if isinstance(result, list) and len(result) > 0 else result

    clean_id = job_id.split(":")[-1]
    await db.query(f"RELATE jobs:{clean_id}->has_attempt->{res_data['id']}")

    return JobAttempt(**res_data)


async def get_job_attempts(job_id: str) -> list[JobAttempt]:
    """Get all attempts for a job."""
    result = await db.query(
        "SELECT * FROM job_attempts WHERE job_id = $job_id ORDER BY attempt_number ASC",
        {"job_id": job_id},
    )
    # v2 returns results directly
    records = result if isinstance(result, list) else []
    return [JobAttempt(**r) for r in records]


async def get_table_names() -> list[str]:
    """Return all table names in the database."""
    result = await db.query("INFO FOR DB;")
    tables = result[0].get("tables", {}) if result else {}
    return list(tables.keys())


async def list_jobs(
    limit: int = 20, owner_id: str | None = None, status: str | None = None
) -> list[Job]:
    """List recent translation jobs, newest first."""
    query = "SELECT * FROM jobs"
    conditions = []
    params = {"limit": limit}

    if owner_id:
        conditions.append("owner_id = $owner_id")
        params["owner_id"] = owner_id
    if status:
        conditions.append("status = $status")
        params["status"] = status

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY created_at DESC LIMIT $limit"

    result = await db.query(query, params)

    records = result if isinstance(result, list) else []
    jobs = []
    for r in records:
        if not isinstance(r, dict) or "filename" not in r:
            logger.warning(f"Skipping invalid job record: {r}")
            continue
        try:
            jobs.append(Job(**r))
        except Exception as e:
            logger.warning(f"Skipping unparseable job record: {e}")
    return jobs


async def save_segments(
    job_id: str,
    segments: list[dict],
    high_threshold: float = 0.85,
) -> None:
    """Bulk-save translated segments for Review Editor."""
    clean_id = job_id.split(":")[-1]
    now = datetime.now(timezone.utc).isoformat()
    to_insert = []

    for idx, seg in enumerate(segments):
        source = seg.get("text", "").strip()
        if not source:
            continue
        confidence = seg.get("confidence", 0.0)
        status = "approved" if confidence >= high_threshold else "pending"

        to_insert.append(
            {
                "job_id": job_id,
                "index": idx,
                "source": source,
                "target": seg.get("translated_text", ""),
                "confidence": confidence,
                "status": status,
                "location": seg.get("location", ""),
                "created_at": now,
            }
        )

    if to_insert:
        for seg_data in to_insert:
            res = await db.create("segment_reviews", seg_data)
            res_data = res[0] if isinstance(res, list) and len(res) > 0 else res
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
            {"job_id": job_id, "statuses": statuses},
        )
    else:
        result = await db.query(
            "SELECT * FROM segment_reviews WHERE job_id = $job_id ORDER BY index ASC",
            {"job_id": job_id},
        )

    records = result if isinstance(result, list) else []
    return [SegmentReview(**r) for r in records]


async def update_segment(
    job_id: str,
    index: int,
    edited_text: str,
) -> SegmentReview | None:
    """Update a single segment's edited text."""
    result = await db.query(
        "UPDATE segment_reviews SET edited = $edited, status = 'edited' WHERE job_id = $job_id AND index = $index RETURN AFTER",
        {"job_id": job_id, "index": index, "edited": edited_text},
    )
    records = result if isinstance(result, list) else []
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
        {"job_id": job_id, "threshold": threshold},
    )
    records = result if isinstance(result, list) else []
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
    records = result if isinstance(result, list) else []
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
                {
                    "sl": source_lang,
                    "tl": target_lang,
                    "dom": domain,
                    "owner_id": owner_id,
                },
            )
        else:
            await db.query(
                "DELETE glossary WHERE source_lang = $sl AND target_lang = $tl AND domain = $dom",
                {"sl": source_lang, "tl": target_lang, "dom": domain},
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
            exists = await db.query(
                "SELECT * FROM glossary WHERE source_text = $st AND source_lang = $sl AND target_lang = $tl AND domain = $dom",
                {
                    "st": source_text,
                    "sl": source_lang,
                    "tl": target_lang,
                    "dom": domain,
                },
            )
            if exists:
                continue

        term_data = {
            "source_lang": source_lang,
            "target_lang": target_lang,
            "domain": domain,
            "owner_id": owner_id,
            "source_text": source_text,
            "target_text": target_text,
            "context": context if context else None,
            "created_at": now,
        }
        await db.create("glossary", term_data)
        added += 1

    return added


async def delete_glossary_term(term_id: str, owner_id: str | None = None) -> bool:
    """Delete a glossary term by ID, with optional owner verification."""
    clean_id = term_id if term_id.startswith("glossary:") else f"glossary:{term_id}"
    if owner_id:
        # Verify ownership before deleting
        result = await db.query(
            "SELECT id FROM type::record($tid) WHERE owner_id = $owner_id LIMIT 1",
            {"tid": clean_id, "owner_id": owner_id},
        )
        records = result if isinstance(result, list) else [result] if result else []
        if not records:
            return False
    result = await db.delete(clean_id)
    return bool(result)
