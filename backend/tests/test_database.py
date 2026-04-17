"""Tests for app.database — async SQLite with job tracking."""

import pytest

from app.database import (
    init_db,
    create_job,
    get_job,
    update_job_status,
    add_job_attempt,
    get_job_attempts,
    get_table_names,
)


@pytest.fixture
async def db_session(tmp_path):
    """Create fresh async SQLite for each test."""
    db_url = f"sqlite+aiosqlite:///{tmp_path}/test.db"
    engine, session_factory = await init_db(db_url)
    async with session_factory() as session:
        yield session
    await engine.dispose()


@pytest.mark.asyncio
class TestDatabase:
    """Feature: Async SQLite with job tracking."""

    async def test_create_tables(self, db_session):
        """Scenario: Tables created on init."""
        tables = await get_table_names(db_session)
        assert "jobs" in tables
        assert "job_attempts" in tables
        assert "glossary" in tables

    async def test_create_job(self, db_session):
        """Scenario: Create a translation job."""
        job = await create_job(
            db_session,
            filename="test.docx",
            file_type="docx",
            file_path="/data/uploads/test.docx",
        )
        assert job.id is not None
        assert len(job.id) == 32  # UUID hex
        assert job.status == "pending"
        assert job.filename == "test.docx"
        assert job.file_type == "docx"

    async def test_get_job(self, db_session):
        """Scenario: Retrieve job by ID."""
        job = await create_job(db_session, "t.docx", "docx", "/f")
        found = await get_job(db_session, job.id)
        assert found is not None
        assert found.id == job.id

    async def test_get_job_not_found(self, db_session):
        """Scenario: Non-existent ID → None."""
        assert await get_job(db_session, "nonexistent") is None

    async def test_update_job_status(self, db_session):
        """Scenario: Update job from pending → planning."""
        job = await create_job(db_session, "t.docx", "docx", "/f")
        await update_job_status(db_session, job.id, "planning")
        updated = await get_job(db_session, job.id)
        assert updated.status == "planning"

    async def test_update_job_extra_fields(self, db_session):
        """Scenario: Update status + extra fields."""
        job = await create_job(db_session, "t.docx", "docx", "/f")
        await update_job_status(
            db_session, job.id, "completed",
            output_path="/data/output/t_vi.docx",
            segments_count=12,
            duration_seconds=134.5,
        )
        updated = await get_job(db_session, job.id)
        assert updated.status == "completed"
        assert updated.output_path == "/data/output/t_vi.docx"
        assert updated.segments_count == 12
        assert updated.duration_seconds == 134.5

    async def test_add_job_attempt(self, db_session):
        """Scenario: Log a failed extraction attempt."""
        job = await create_job(db_session, "t.docx", "docx", "/f")
        await add_job_attempt(
            db_session, job.id,
            attempt=1, phase="extracting",
            code="import docx",
            stderr="ImportError: No module named 'docx'",
            success=False,
            duration=1.2,
        )
        attempts = await get_job_attempts(db_session, job.id)
        assert len(attempts) == 1
        assert attempts[0].success is False
        assert attempts[0].phase == "extracting"
        assert "ImportError" in attempts[0].stderr

    async def test_multiple_attempts(self, db_session):
        """Scenario: Multiple attempts tracked in order."""
        job = await create_job(db_session, "t.docx", "docx", "/f")
        await add_job_attempt(db_session, job.id, 1, "extracting", "code1", "err1", False)
        await add_job_attempt(db_session, job.id, 2, "extracting", "code2", None, True)
        attempts = await get_job_attempts(db_session, job.id)
        assert len(attempts) == 2
        assert attempts[0].attempt_number == 1
        assert attempts[1].attempt_number == 2
        assert attempts[1].success is True
