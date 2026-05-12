"""Unit Tests — Auth Module.

Tests JWT lifecycle and get_current_user logic.
All tests run WITHOUT SurrealDB (mocked via conftest.py).
"""

import pytest
from datetime import timedelta, timezone, datetime
from unittest.mock import AsyncMock, patch

from app.auth import (
    create_access_token,
    get_current_user,
    SECRET_KEY,
    ALGORITHM,
)
import jwt


class TestJWTLifecycle:
    """Unit: JWT token creation, decode, expiry."""

    def test_token_contains_subject(self):
        token = create_access_token(data={"sub": "alice"})
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["sub"] == "alice"

    def test_token_has_expiry(self):
        token = create_access_token(data={"sub": "alice"})
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert "exp" in payload

    def test_custom_expiry(self):
        token = create_access_token(
            data={"sub": "alice"}, expires_delta=timedelta(minutes=5)
        )
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert "exp" in payload

    def test_expired_token_rejected(self):
        token = create_access_token(
            data={"sub": "alice"}, expires_delta=timedelta(seconds=-10)
        )
        with pytest.raises(jwt.ExpiredSignatureError):
            jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

    def test_garbage_token_rejected(self):
        with pytest.raises(jwt.DecodeError):
            jwt.decode("not.valid.token", SECRET_KEY, algorithms=[ALGORITHM])

    def test_wrong_key_rejected(self):
        other_key = "another-secret-key-1234567890abcdef"
        token = jwt.encode(
            {"sub": "alice", "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
            other_key,
            algorithm=ALGORITHM,
        )
        with pytest.raises(jwt.InvalidSignatureError):
            jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

    def test_token_without_sub(self):
        token = create_access_token(data={"role": "admin"})
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert payload.get("sub") is None


class TestGetCurrentUser:
    """Unit: FastAPI dependency get_current_user()."""

    @pytest.mark.asyncio
    async def test_valid_token_returns_user(self, user_a, token_a):
        import app.database as db_mod

        with patch.object(db_mod, "db") as mock_db:
            mock_db.query = AsyncMock(return_value=[{"result": [user_a]}])
            result = await get_current_user(token=token_a)
            assert result["username"] == "alice"
            assert result["id"] == "user:userA_001"

    @pytest.mark.asyncio
    async def test_missing_sub_raises_401(self):
        token = create_access_token(data={"role": "admin"})
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc:
            await get_current_user(token=token)
        assert exc.value.status_code == 401

    @pytest.mark.asyncio
    async def test_user_not_in_db_raises_401(self, token_a):
        import app.database as db_mod

        with patch.object(db_mod, "db") as mock_db:
            mock_db.query = AsyncMock(return_value=[{"result": []}])
            from fastapi import HTTPException

            with pytest.raises(HTTPException) as exc:
                await get_current_user(token=token_a)
            assert exc.value.status_code == 401

    @pytest.mark.asyncio
    async def test_expired_token_raises_401(self, expired_token):
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc:
            await get_current_user(token=expired_token)
        assert exc.value.status_code == 401

    @pytest.mark.asyncio
    async def test_garbage_token_raises_401(self):
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc:
            await get_current_user(token="garbage.token.here")
        assert exc.value.status_code == 401
