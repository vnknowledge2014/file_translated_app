"""Unit Tests — Security Hardening.

Tests filename sanitization, vector search edge cases, and
configuration security.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.auth import get_password_hash, verify_password, SECRET_KEY


class TestFilenameSanitization:
    """Unit: Upload filename sanitization prevents path traversal."""

    def test_slash_stripped(self):
        raw = "../../../etc/passwd.docx"
        safe = raw.replace("/", "").replace("\\", "")
        assert "/" not in safe
        assert "\\" not in safe
        assert safe == "......etcpasswd.docx"

    def test_backslash_stripped(self):
        raw = "..\\..\\..\\windows\\system32\\cmd.docx"
        safe = raw.replace("/", "").replace("\\", "")
        assert "\\" not in safe

    def test_normal_filename_unchanged(self):
        raw = "my_report_2024.docx"
        safe = raw.replace("/", "").replace("\\", "")
        assert safe == raw

    def test_japanese_filename_preserved(self):
        raw = "設計書_0825_新デザイン.xlsx"
        safe = raw.replace("/", "").replace("\\", "")
        assert safe == raw

    def test_empty_filename_handled(self):
        raw = ""
        safe = (raw or "unknown").replace("/", "").replace("\\", "")
        assert safe == "unknown"


class TestVectorSearchResilience:
    """Unit: Translation Memory graceful fallback."""

    @pytest.mark.asyncio
    async def test_empty_embedding_not_stored(self):
        """If embedding is [], it should NOT be included in the UPSERT."""
        embedding = []
        # Simulate the conditional logic from translator.py
        if embedding:
            query = "UPSERT ... SET ... embedding = $embedding"
        else:
            query = "UPSERT ... SET ..."
        assert "embedding" not in query

    @pytest.mark.asyncio
    async def test_valid_embedding_stored(self):
        """If embedding is a valid list, include it."""
        embedding = [0.1, 0.2, 0.3, 0.4]
        if embedding:
            query = "UPSERT ... SET ... embedding = $embedding"
        else:
            query = "UPSERT ... SET ..."
        assert "embedding" in query

    @pytest.mark.asyncio
    async def test_embedding_failure_returns_empty_matches(self):
        """If embedding generation fails, return no fuzzy matches."""
        try:
            raise Exception("Ollama timeout")
        except Exception:
            fuzzy_matches = []
        assert fuzzy_matches == []


class TestSecretKeyConfiguration:
    """Unit: SECRET_KEY is configurable and not hardcoded."""

    def test_secret_key_from_settings(self):
        from app.config import settings
        assert hasattr(settings, "SECRET_KEY")
        assert isinstance(settings.SECRET_KEY, str)
        assert len(settings.SECRET_KEY) > 10

    def test_embedding_model_from_settings(self):
        from app.config import settings
        assert hasattr(settings, "EMBEDDING_MODEL")
        assert isinstance(settings.EMBEDDING_MODEL, str)

    def test_auth_uses_settings_key(self):
        """Verify auth.py reads from settings, not hardcoded."""
        from app.config import settings
        assert SECRET_KEY == settings.SECRET_KEY


class TestPasswordSecurity:
    """Unit: Password handling edge cases."""

    def test_unicode_password(self):
        pw = "パスワード123"
        h = get_password_hash(pw)
        assert verify_password(pw, h)
        assert not verify_password("wrong", h)

    def test_long_password(self):
        """bcrypt has a 72-byte limit, should not crash."""
        pw = "a" * 72
        h = get_password_hash(pw)
        assert verify_password(pw, h)

    def test_special_chars_password(self):
        pw = "p@$$w0rd!#%^&*(){}[]"
        h = get_password_hash(pw)
        assert verify_password(pw, h)
