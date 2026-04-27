"""Tests for authentication flow: register, login, token validation.

These tests are designed to run WITHOUT SurrealDB or Ollama — they mock all
external I/O and focus on the auth module's own logic.
"""

import sys
from unittest.mock import MagicMock

# ── Pre-import mocking ──
# The `surrealdb` package may not be installed locally. We mock it
# before any app module tries to import it.
sys.modules.setdefault("surrealdb", MagicMock())

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

from app.auth import (
    create_access_token,
    get_password_hash,
    verify_password,
    get_current_user,
    SECRET_KEY,
    ALGORITHM,
)
import jwt


# ── Password Hashing Tests ──

class TestPasswordHashing:
    def test_hash_and_verify_correct(self):
        password = "test_pass_123"
        hashed = get_password_hash(password)
        assert hashed != password
        assert verify_password(password, hashed) is True

    def test_verify_wrong_password(self):
        hashed = get_password_hash("correct")
        assert verify_password("wrong", hashed) is False

    def test_hash_is_unique_per_salt(self):
        """Each hash should be unique due to bcrypt salt."""
        h1 = get_password_hash("same")
        h2 = get_password_hash("same")
        assert h1 != h2
        assert verify_password("same", h1) is True
        assert verify_password("same", h2) is True


# ── JWT Token Tests ──

class TestJWTTokens:
    def test_create_token_contains_subject(self):
        token = create_access_token(data={"sub": "testuser"})
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["sub"] == "testuser"

    def test_create_token_with_custom_expiry(self):
        expires = timedelta(minutes=30)
        token = create_access_token(data={"sub": "testuser"}, expires_delta=expires)
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert "exp" in payload

    def test_create_token_default_expiry(self):
        token = create_access_token(data={"sub": "testuser"})
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert "exp" in payload

    def test_expired_token_raises(self):
        """An expired token should be rejected by jwt.decode."""
        expires = timedelta(seconds=-10)
        token = create_access_token(data={"sub": "testuser"}, expires_delta=expires)
        with pytest.raises(jwt.ExpiredSignatureError):
            jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

    def test_invalid_token_string(self):
        with pytest.raises(jwt.DecodeError):
            jwt.decode("not.a.real.token", SECRET_KEY, algorithms=[ALGORITHM])

    def test_wrong_secret_key(self):
        """Token signed with different key should be rejected."""
        other_key = "a-totally-different-secret-key-1234567890"
        token = jwt.encode(
            {"sub": "testuser", "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
            other_key,
            algorithm=ALGORITHM,
        )
        with pytest.raises(jwt.InvalidSignatureError):
            jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])


# ── get_current_user Tests ──
# The `db` object is lazy-imported inside `get_current_user`, so we need
# to mock it at the database module level.

class TestGetCurrentUser:
    @pytest.mark.asyncio
    async def test_valid_token_returns_user(self):
        token = create_access_token(data={"sub": "admin"})
        mock_user = {"id": "user:abc123", "username": "admin", "role": "user"}

        import app.database as db_module
        with patch.object(db_module, "db") as mock_db:
            mock_db.query = AsyncMock(return_value=[{"result": [mock_user]}])
            user = await get_current_user(token=token)
            assert user["username"] == "admin"
            assert user["id"] == "user:abc123"

    @pytest.mark.asyncio
    async def test_missing_sub_claim_raises_401(self):
        """Token without 'sub' claim → 401."""
        token = create_access_token(data={"role": "admin"})  # No 'sub'

        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(token=token)
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_user_not_found_raises_401(self):
        """Valid token for a user that doesn't exist in DB → 401."""
        token = create_access_token(data={"sub": "ghost_user"})

        import app.database as db_module
        with patch.object(db_module, "db") as mock_db:
            mock_db.query = AsyncMock(return_value=[{"result": []}])

            from fastapi import HTTPException
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(token=token)
            assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_expired_token_raises_401(self):
        """Expired token → 401."""
        token = create_access_token(
            data={"sub": "testuser"},
            expires_delta=timedelta(seconds=-10),
        )

        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(token=token)
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_garbage_token_raises_401(self):
        """Random garbage string as token → 401."""
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(token="this.is.garbage.token")
        assert exc_info.value.status_code == 401
