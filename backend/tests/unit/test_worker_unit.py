"""Unit Tests — Worker Pool.

Tests WorkerPool queue management, lifecycle, and webhook HMAC.
"""

import hashlib
import hmac
import json
import pytest
from unittest.mock import MagicMock


class TestWorkerPoolInit:
    """Unit: WorkerPool initialization."""

    def test_pool_creates_with_max_workers(self):
        from app.worker import WorkerPool

        pool = WorkerPool(max_workers=3)
        assert pool.max_workers == 3

    def test_pool_defaults_from_settings(self):
        from app.worker import WorkerPool
        from app.config import settings

        pool = WorkerPool()
        assert pool.max_workers == settings.MAX_WORKERS

    def test_pool_starts_not_started(self):
        from app.worker import WorkerPool

        pool = WorkerPool(max_workers=1)
        assert not pool._started
        assert pool.active_count == 0
        assert pool.queue_size == 0


class TestWorkerPoolLifecycle:
    """Unit: WorkerPool start/shutdown lifecycle."""

    @pytest.mark.asyncio
    async def test_pool_starts(self):
        from app.worker import WorkerPool

        pool = WorkerPool(max_workers=2)
        await pool.start()
        assert pool._started
        assert len(pool._workers) == 2
        await pool.shutdown()

    @pytest.mark.asyncio
    async def test_pool_shutdown(self):
        from app.worker import WorkerPool

        pool = WorkerPool(max_workers=1)
        await pool.start()
        await pool.shutdown()
        assert not pool._started
        assert len(pool._workers) == 0

    @pytest.mark.asyncio
    async def test_double_start_idempotent(self):
        from app.worker import WorkerPool

        pool = WorkerPool(max_workers=1)
        await pool.start()
        await pool.start()  # Should not create extra workers
        assert len(pool._workers) == 1
        await pool.shutdown()


class TestWorkerPoolQueue:
    """Unit: WorkerPool queue management."""

    @pytest.mark.asyncio
    async def test_submit_increments_queue(self):
        from app.worker import WorkerPool, JobItem

        pool = WorkerPool(max_workers=1)
        # Don't start workers — just test queue
        job = JobItem(
            app=MagicMock(),
            job_id="test-1",
            file_path="/tmp/test.docx",
            file_type="docx",
            filename="test.docx",
            export_xliff=False,
            xliff_version="2.1",
        )
        await pool._queue.put(job)
        assert pool.queue_size == 1

    def test_active_count_empty(self):
        from app.worker import WorkerPool

        pool = WorkerPool(max_workers=1)
        assert pool.active_count == 0


class TestJobItem:
    """Unit: JobItem dataclass."""

    def test_job_item_fields(self):
        from app.worker import JobItem

        job = JobItem(
            app=MagicMock(),
            job_id="abc-123",
            file_path="/data/test.docx",
            file_type="docx",
            filename="test.docx",
            export_xliff=True,
            xliff_version="2.1",
            domain="legal",
            source_lang="ja",
            target_lang="vi",
        )
        assert job.job_id == "abc-123"
        assert job.domain == "legal"
        assert job.source_lang == "ja"
        assert job.target_lang == "vi"

    def test_job_item_defaults(self):
        from app.worker import JobItem

        job = JobItem(
            app=MagicMock(),
            job_id="test",
            file_path="/tmp/x",
            file_type="docx",
            filename="x.docx",
            export_xliff=False,
            xliff_version="2.1",
        )
        assert job.domain == "general"
        assert job.source_lang == "ja"
        assert job.target_lang == "vi"
        assert job.no_translate is False
        assert job.webhook_url is None


class TestWebhookHMAC:
    """Unit: Webhook HMAC signature generation."""

    def test_webhook_hmac_valid(self):
        """Verify HMAC-SHA256 signature matches expected format."""
        from app.config import settings

        payload = {
            "event": "job.completed",
            "job_id": "test-123",
            "status": "completed",
        }
        payload_bytes = json.dumps(payload, sort_keys=True).encode()
        signature = hmac.new(
            settings.SECRET_KEY.encode(), payload_bytes, hashlib.sha256
        ).hexdigest()

        # Verify format
        assert len(signature) == 64  # SHA-256 hex
        assert isinstance(signature, str)

    def test_webhook_hmac_consistency(self):
        """Same payload produces same signature."""
        from app.config import settings

        payload = {"event": "job.failed", "job_id": "abc"}
        payload_bytes = json.dumps(payload, sort_keys=True).encode()
        sig1 = hmac.new(
            settings.SECRET_KEY.encode(), payload_bytes, hashlib.sha256
        ).hexdigest()
        sig2 = hmac.new(
            settings.SECRET_KEY.encode(), payload_bytes, hashlib.sha256
        ).hexdigest()
        assert sig1 == sig2

    def test_different_payloads_different_signatures(self):
        from app.config import settings

        payload1 = json.dumps({"a": 1}, sort_keys=True).encode()
        payload2 = json.dumps({"b": 2}, sort_keys=True).encode()
        sig1 = hmac.new(
            settings.SECRET_KEY.encode(), payload1, hashlib.sha256
        ).hexdigest()
        sig2 = hmac.new(
            settings.SECRET_KEY.encode(), payload2, hashlib.sha256
        ).hexdigest()
        assert sig1 != sig2
