"""Tests for FastAPI routes — upload, jobs, download, health."""

import os
import pytest
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from app.main import app
from app.database import init_db


@pytest.fixture
async def test_app(tmp_path):
    """Create test FastAPI app with temp DB."""
    db_path = tmp_path / "test.db"
    db_url = f"sqlite+aiosqlite:///{db_path}"
    engine, session_factory = await init_db(db_url)
    app.state.db_engine = engine
    app.state.db_session_factory = session_factory
    app.state.ollama_client = AsyncMock()
    app.state.ollama_client.health_check = AsyncMock(return_value=True)

    # Override upload/output dirs
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    os.environ["UPLOAD_DIR"] = str(upload_dir)
    os.environ["OUTPUT_DIR"] = str(output_dir)

    # Patch settings
    from app.config import settings
    settings.UPLOAD_DIR = str(upload_dir)
    settings.OUTPUT_DIR = str(output_dir)

    yield app

    await engine.dispose()


@pytest.fixture
def client(test_app):
    """Sync TestClient for FastAPI app."""
    # Using TestClient in sync mode since it handles the async loop
    return TestClient(app, raise_server_exceptions=True)


class TestHealthEndpoint:
    """Feature: Health check."""

    @pytest.mark.asyncio
    async def test_health(self, test_app, client):
        """Scenario: Health endpoint → returns status."""
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"


class TestUploadEndpoint:
    """Feature: Upload file for translation."""

    @pytest.mark.asyncio
    async def test_upload_docx(self, test_app, client, tmp_path):
        """Scenario: Upload .docx → creates job."""
        response = client.post(
            "/api/upload",
            files={"file": ("test.docx", b"fake docx content", "application/octet-stream")},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["file_type"] == "docx"
        assert data["status"] == "pending"
        assert "job_id" in data

    @pytest.mark.asyncio
    async def test_upload_unsupported_type(self, test_app, client):
        """Scenario: Upload .exe → rejected."""
        response = client.post(
            "/api/upload",
            files={"file": ("virus.exe", b"bad content", "application/octet-stream")},
        )
        assert response.status_code == 200
        data = response.json()
        assert "error" in data

    @pytest.mark.asyncio
    async def test_upload_xlsx(self, test_app, client):
        """Scenario: Upload .xlsx → creates job."""
        response = client.post(
            "/api/upload",
            files={"file": ("data.xlsx", b"fake xlsx", "application/octet-stream")},
        )
        data = response.json()
        assert data["file_type"] == "xlsx"
        assert data["status"] == "pending"


class TestJobsEndpoint:
    """Feature: Job status tracking."""

    @pytest.mark.asyncio
    async def test_get_job_detail(self, test_app, client):
        """Scenario: Upload then fetch job → returns details."""
        # First upload
        upload_resp = client.post(
            "/api/upload",
            files={"file": ("test.docx", b"content", "application/octet-stream")},
        )
        job_id = upload_resp.json()["job_id"]

        # Then fetch
        response = client.get(f"/api/jobs/{job_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == job_id
        assert data["filename"] == "test.docx"
        assert data["status"] == "pending"

    @pytest.mark.asyncio
    async def test_get_nonexistent_job(self, test_app, client):
        """Scenario: Nonexistent job → error."""
        response = client.get("/api/jobs/nonexistent")
        data = response.json()
        assert "error" in data


class TestDownloadEndpoint:
    """Feature: Download translated file."""

    @pytest.mark.asyncio
    async def test_download_not_completed(self, test_app, client):
        """Scenario: Job not completed → error."""
        upload_resp = client.post(
            "/api/upload",
            files={"file": ("test.docx", b"content", "application/octet-stream")},
        )
        job_id = upload_resp.json()["job_id"]

        response = client.get(f"/api/download/{job_id}")
        data = response.json()
        assert "error" in data
        assert "not completed" in data["error"]

    @pytest.mark.asyncio
    async def test_download_nonexistent(self, test_app, client):
        """Scenario: Nonexistent job → error."""
        response = client.get("/api/download/nonexistent")
        data = response.json()
        assert "error" in data
