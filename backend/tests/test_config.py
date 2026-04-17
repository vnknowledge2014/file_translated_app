"""Tests for app.config — Settings."""

from app.config import Settings


class TestSettings:
    """Feature: Load config from env vars with defaults."""

    def test_default_ollama_url(self):
        """Scenario: No env var → default URL"""
        settings = Settings()
        assert settings.OLLAMA_URL == "http://ollama:11434"

    def test_env_override_ollama_url(self, monkeypatch):
        """Scenario: Env var set → overrides default"""
        monkeypatch.setenv("OLLAMA_URL", "http://localhost:11434")
        settings = Settings()
        assert settings.OLLAMA_URL == "http://localhost:11434"



    def test_default_max_workers(self):
        settings = Settings()
        assert settings.MAX_WORKERS == 1

    def test_env_override_max_workers(self, monkeypatch):
        monkeypatch.setenv("MAX_WORKERS", "4")
        settings = Settings()
        assert settings.MAX_WORKERS == 4

    def test_supported_file_types(self):
        settings = Settings()
        assert "docx" in settings.SUPPORTED_TYPES
        assert "xlsx" in settings.SUPPORTED_TYPES
        assert "pptx" in settings.SUPPORTED_TYPES
        assert "pdf" in settings.SUPPORTED_TYPES
        assert len(settings.SUPPORTED_TYPES) == 7


