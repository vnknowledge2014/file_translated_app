"""Async SQLite database with CRUD operations for job tracking."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models import Base, GlossaryTerm, Job, JobAttempt, SegmentReview


async def init_db(database_url: str) -> tuple:
    """Initialize database, create all tables.

    Also runs lightweight schema migrations for existing databases
    (e.g., glossary table column rename from jp/vi to source_text/target_text).

    Args:
        database_url: SQLAlchemy async database URL.

    Returns:
        Tuple of (engine, session_factory).
    """
    engine = create_async_engine(database_url, echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        # Lightweight migration: add new columns to existing tables if missing
        # This handles the transition from the old JP/VI-only schema
        try:
            # Check if glossary table has the old schema
            result = await conn.execute(text("PRAGMA table_info(glossary)"))
            columns = {row[1] for row in result.fetchall()}

            if "jp" in columns and "source_text" not in columns:
                # Migrate old schema: rename jp→source_text, vi→target_text
                await conn.execute(text("ALTER TABLE glossary RENAME TO glossary_old"))
                await conn.run_sync(Base.metadata.create_all)
                await conn.execute(text(
                    "INSERT INTO glossary (source_lang, target_lang, source_text, target_text, context, created_at) "
                    "SELECT 'ja', 'vi', jp, vi, context, created_at FROM glossary_old"
                ))
                await conn.execute(text("DROP TABLE glossary_old"))

            # Add source_lang/target_lang/domain to jobs if missing
            result = await conn.execute(text("PRAGMA table_info(jobs)"))
            job_columns = {row[1] for row in result.fetchall()}
            if "source_lang" not in job_columns:
                await conn.execute(text("ALTER TABLE jobs ADD COLUMN source_lang TEXT NOT NULL DEFAULT 'ja'"))
                await conn.execute(text("ALTER TABLE jobs ADD COLUMN target_lang TEXT NOT NULL DEFAULT 'vi'"))
            if "domain" not in job_columns:
                await conn.execute(text("ALTER TABLE jobs ADD COLUMN domain TEXT NOT NULL DEFAULT 'general'"))

            # Add domain to glossary if missing
            if "domain" not in columns:  # columns is table_info(glossary) from earlier
                await conn.execute(text("ALTER TABLE glossary ADD COLUMN domain TEXT NOT NULL DEFAULT 'general'"))
        except Exception:
            pass  # Migration already done or fresh DB

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    return engine, session_factory


async def create_job(
    session: AsyncSession,
    filename: str,
    file_type: str,
    file_path: str,
    domain: str = "general",
    source_lang: str = "ja",
    target_lang: str = "vi",
) -> Job:
    """Create new job with status='pending'.

    Args:
        session: Async database session.
        filename: Original filename.
        file_type: Detected file type (docx, xlsx, etc.).
        file_path: Path to uploaded file.
        domain: Domain context for translation.

    Returns:
        Created Job instance.
    """
    from app.config import settings
    job = Job(
        id=uuid.uuid4().hex,
        filename=filename,
        file_type=file_type,
        file_path=file_path,
        domain=domain,
        source_lang=source_lang,
        target_lang=target_lang,
        status="pending",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    session.add(job)
    await session.commit()
    await session.refresh(job)
    return job


async def get_job(session: AsyncSession, job_id: str) -> Job | None:
    """Get job by ID.

    Args:
        session: Async database session.
        job_id: Job UUID.

    Returns:
        Job instance or None.
    """
    result = await session.execute(select(Job).where(Job.id == job_id))
    return result.scalar_one_or_none()


async def update_job_status(
    session: AsyncSession,
    job_id: str,
    status: str,
    **kwargs,
) -> None:
    """Update job status and optional fields.

    Args:
        session: Async database session.
        job_id: Job UUID.
        status: New status value.
        **kwargs: Additional fields to update (error_message, output_path, etc.).
    """
    job = await get_job(session, job_id)
    if job:
        job.status = status
        job.updated_at = datetime.now(UTC)
        for key, value in kwargs.items():
            if hasattr(job, key):
                setattr(job, key, value)
        await session.commit()


async def add_job_attempt(
    session: AsyncSession,
    job_id: str,
    attempt: int,
    phase: str,
    code: str | None,
    stderr: str | None,
    success: bool,
    duration: float | None = None,
    error_message: str | None = None,
) -> JobAttempt:
    """Log a job attempt for debugging.

    Args:
        session: Async database session.
        job_id: Parent job UUID.
        attempt: Attempt number (1, 2, 3...).
        phase: Pipeline phase (planning, extracting, etc.).
        code: Generated code that was tried.
        stderr: Execution stderr output.
        success: Whether the attempt succeeded.
        duration: Execution duration in seconds.
        error_message: Error message if failed.

    Returns:
        Created JobAttempt instance.
    """
    job_attempt = JobAttempt(
        job_id=job_id,
        attempt_number=attempt,
        phase=phase,
        code_generated=code,
        stderr=stderr,
        success=success,
        duration_seconds=duration,
        error_message=error_message,
    )
    session.add(job_attempt)
    await session.commit()
    return job_attempt


async def get_job_attempts(session: AsyncSession, job_id: str) -> list[JobAttempt]:
    """Get all attempts for a job.

    Args:
        session: Async database session.
        job_id: Parent job UUID.

    Returns:
        List of JobAttempt instances ordered by attempt number.
    """
    result = await session.execute(
        select(JobAttempt)
        .where(JobAttempt.job_id == job_id)
        .order_by(JobAttempt.attempt_number)
    )
    return list(result.scalars().all())


async def get_table_names(session: AsyncSession) -> list[str]:
    """Return all table names in the database.

    Args:
        session: Active async session.

    Returns:
        List of table name strings.
    """
    result = await session.execute(
        text("SELECT name FROM sqlite_master WHERE type='table'")
    )
    return [row[0] for row in result.fetchall()]


async def list_jobs(session: AsyncSession, limit: int = 20) -> list[Job]:
    """List recent translation jobs, newest first.

    Args:
        session: Active async session.
        limit: Maximum number of jobs to return.

    Returns:
        List of Job objects ordered by created_at descending.
    """
    result = await session.execute(
        select(Job).order_by(Job.created_at.desc()).limit(limit)
    )
    return list(result.scalars().all())


async def save_segments(
    session: AsyncSession,
    job_id: str,
    segments: list[dict],
    high_threshold: float = 0.85,
) -> None:
    """Bulk-save translated segments for Review Editor.

    Args:
        session: Async database session.
        job_id: Parent job UUID.
        segments: List of segment dicts from the pipeline.
        high_threshold: Confidence above this is auto-approved.
    """
    for idx, seg in enumerate(segments):
        source = seg.get("text", "").strip()
        if not source:
            continue
        target = seg.get("translated_text", "")
        confidence = seg.get("confidence", 0.0)
        status = "approved" if confidence >= high_threshold else "pending"
        review = SegmentReview(
            job_id=job_id,
            index=idx,
            source=source,
            target=target,
            confidence=confidence,
            status=status,
            location=seg.get("location", ""),
        )
        session.add(review)
    await session.commit()


async def get_segments(
    session: AsyncSession,
    job_id: str,
    filter_status: str | None = None,
) -> list[SegmentReview]:
    """Get segments for a job, optionally filtered by status.

    Args:
        session: Async database session.
        job_id: Parent job UUID.
        filter_status: Optional comma-separated statuses (e.g. "pending,edited").

    Returns:
        List of SegmentReview instances ordered by index.
    """
    query = select(SegmentReview).where(SegmentReview.job_id == job_id)
    if filter_status:
        statuses = [s.strip() for s in filter_status.split(",")]
        query = query.where(SegmentReview.status.in_(statuses))
    query = query.order_by(SegmentReview.index)
    result = await session.execute(query)
    return list(result.scalars().all())


async def update_segment(
    session: AsyncSession,
    job_id: str,
    index: int,
    edited_text: str,
) -> SegmentReview | None:
    """Update a single segment's edited text.

    Args:
        session: Async database session.
        job_id: Parent job UUID.
        index: Segment index.
        edited_text: New translated text from the reviewer.

    Returns:
        Updated SegmentReview or None if not found.
    """
    result = await session.execute(
        select(SegmentReview).where(
            SegmentReview.job_id == job_id,
            SegmentReview.index == index,
        )
    )
    seg = result.scalar_one_or_none()
    if seg:
        seg.edited = edited_text
        seg.status = "edited"
        await session.commit()
        await session.refresh(seg)
    return seg


async def approve_high_segments(
    session: AsyncSession,
    job_id: str,
    threshold: float = 0.85,
) -> int:
    """Approve all HIGH-confidence segments in bulk.

    Returns:
        Number of segments approved.
    """
    result = await session.execute(
        select(SegmentReview).where(
            SegmentReview.job_id == job_id,
            SegmentReview.confidence >= threshold,
            SegmentReview.status == "pending",
        )
    )
    segments = list(result.scalars().all())
    for seg in segments:
        seg.status = "approved"
    await session.commit()
    return len(segments)


async def get_all_glossary_terms(
    session: AsyncSession,
    source_lang: str | None = None,
    target_lang: str | None = None,
    domain: str | None = None,
) -> list[GlossaryTerm]:
    """Get all glossary terms, optionally filtered by language pair and domain.

    Args:
        session: Async database session.
        source_lang: Optional source language filter (ISO 639-1).
        target_lang: Optional target language filter (ISO 639-1).
        domain: Optional domain filter.

    Returns:
        List of GlossaryTerm instances ordered by created_at.
    """
    query = select(GlossaryTerm)
    if source_lang:
        query = query.where(GlossaryTerm.source_lang == source_lang)
    if target_lang:
        query = query.where(GlossaryTerm.target_lang == target_lang)
    if domain:
        query = query.where(GlossaryTerm.domain == domain)
    query = query.order_by(GlossaryTerm.created_at)
    result = await session.execute(query)
    return list(result.scalars().all())


async def add_glossary_terms(
    session: AsyncSession,
    terms: list[dict],
    replace: bool = True,
    source_lang: str = "ja",
    target_lang: str = "vi",
    domain: str = "general",
) -> int:
    """Add new glossary terms from a list of dicts.

    Args:
        session: Async database session.
        terms: List of dicts with 'source_text'/'jp', 'target_text'/'vi',
               and optional 'context'.
        replace: If True, deletes all existing terms for this domain/language pair.
        source_lang: Source language code.
        target_lang: Target language code.
        domain: Domain code.

    Returns:
        Number of terms added.
    """
    if replace:
        await session.execute(
            text("DELETE FROM glossary WHERE source_lang = :sl AND target_lang = :tl AND domain = :dom"),
            {"sl": source_lang, "tl": target_lang, "dom": domain},
        )

    added = 0
    for t in terms:
        source_text = str(t.get("source_text") or t.get("jp", "")).strip()
        target_text = str(t.get("target_text") or t.get("vi", "")).strip()
        context = str(t.get("context", "")).strip()

        if not source_text or not target_text:
            continue
        
        # Check if exists if not replacing
        if not replace:
            existing = await session.execute(
                select(GlossaryTerm).where(
                    GlossaryTerm.source_text == source_text,
                    GlossaryTerm.source_lang == source_lang,
                    GlossaryTerm.target_lang == target_lang,
                    GlossaryTerm.domain == domain,
                )
            )
            if existing.scalar_one_or_none():
                continue

        term = GlossaryTerm(
            source_lang=source_lang,
            target_lang=target_lang,
            domain=domain,
            source_text=source_text,
            target_text=target_text,
            context=context if context else None,
        )
        session.add(term)
        added += 1

    await session.commit()
    return added


async def delete_glossary_term(session: AsyncSession, term_id: int) -> bool:
    """Delete a glossary term by ID.

    Args:
        session: Async database session.
        term_id: ID of the term to delete.

    Returns:
        True if deleted, False if not found.
    """
    result = await session.execute(
        select(GlossaryTerm).where(GlossaryTerm.id == term_id)
    )
    term = result.scalar_one_or_none()
    if term:
        await session.delete(term)
        await session.commit()
        return True
    return False

