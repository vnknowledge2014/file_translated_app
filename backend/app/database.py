"""Async SQLite database with CRUD operations for job tracking."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models import Base, GlossaryTerm, Job, JobAttempt


async def init_db(database_url: str) -> tuple:
    """Initialize database, create all tables.

    Args:
        database_url: SQLAlchemy async database URL.

    Returns:
        Tuple of (engine, session_factory).
    """
    engine = create_async_engine(database_url, echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    return engine, session_factory


async def create_job(
    session: AsyncSession,
    filename: str,
    file_type: str,
    file_path: str,
) -> Job:
    """Create new job with status='pending'.

    Args:
        session: Async database session.
        filename: Original filename.
        file_type: Detected file type (docx, xlsx, etc.).
        file_path: Path to uploaded file.

    Returns:
        Created Job instance.
    """
    job = Job(
        id=uuid.uuid4().hex,
        filename=filename,
        file_type=file_type,
        file_path=file_path,
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
