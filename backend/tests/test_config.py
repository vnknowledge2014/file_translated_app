"""Tests for app.config — Settings."""

import os
from app.config import Settings


class TestSettings:
    """Feature: Load config from .env file and env vars with defaults."""

    def test_default_ollama_url(self, monkeypatch):
        """Scenario: No env var → default URL (unset any .env value first)"""
        monkeypatch.delenv("OLLAMA_URL", raising=False)
        settings = Settings()
        assert settings.OLLAMA_URL == "http://ollama:11434"

    def test_env_override_ollama_url(self, monkeypatch):
        """Scenario: Env var set → overrides default"""
        monkeypatch.setenv("OLLAMA_URL", "http://localhost:11434")
        settings = Settings()
        assert settings.OLLAMA_URL == "http://localhost:11434"

    def test_default_max_workers(self, monkeypatch):
        monkeypatch.delenv("MAX_WORKERS", raising=False)
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

    # ── New settings from .env externalization ──

    def test_translation_temperature_default(self, monkeypatch):
        monkeypatch.delenv("TRANSLATION_TEMPERATURE", raising=False)
        settings = Settings()
        assert settings.TRANSLATION_TEMPERATURE == 0.3

    def test_translation_temperature_override(self, monkeypatch):
        monkeypatch.setenv("TRANSLATION_TEMPERATURE", "0.5")
        settings = Settings()
        assert settings.TRANSLATION_TEMPERATURE == 0.5

    def test_translation_num_ctx_default(self, monkeypatch):
        monkeypatch.delenv("TRANSLATION_NUM_CTX", raising=False)
        settings = Settings()
        assert settings.TRANSLATION_NUM_CTX == 4096

    def test_max_inline_tags_default(self, monkeypatch):
        monkeypatch.delenv("MAX_INLINE_TAGS", raising=False)
        settings = Settings()
        assert settings.MAX_INLINE_TAGS == 8

    def test_max_segment_chars_default(self, monkeypatch):
        monkeypatch.delenv("MAX_SEGMENT_CHARS", raising=False)
        settings = Settings()
        assert settings.MAX_SEGMENT_CHARS == 400

    def test_batch_max_chars_default(self, monkeypatch):
        monkeypatch.delenv("BATCH_MAX_CHARS", raising=False)
        settings = Settings()
        assert settings.BATCH_MAX_CHARS == 3000

    def test_batch_max_segments_default(self, monkeypatch):
        monkeypatch.delenv("BATCH_MAX_SEGMENTS", raising=False)
        settings = Settings()
        assert settings.BATCH_MAX_SEGMENTS == 5
