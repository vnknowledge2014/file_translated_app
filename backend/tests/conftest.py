"""Shared test fixtures and conftest for the entire test suite.

Provides:
- Pre-import mocking of surrealdb to allow tests without the DB running
- Shared auth fixtures (tokens, users)
- Mock database fixtures
"""

import sys
from unittest.mock import MagicMock, AsyncMock

# ── Pre-import mock: prevent surrealdb ImportError ──
# This MUST happen before any app module is imported
_mock_surreal = MagicMock()
_mock_surreal_instance = MagicMock()
_mock_surreal_instance.connect = AsyncMock()
_mock_surreal_instance.signin = AsyncMock()
_mock_surreal_instance.use = AsyncMock()
_mock_surreal_instance.close = AsyncMock()
_mock_surreal_instance.create = AsyncMock(return_value=[{}])
_mock_surreal_instance.select = AsyncMock(return_value=None)
_mock_surreal_instance.merge = AsyncMock()
_mock_surreal_instance.query = AsyncMock(return_value=[])
_mock_surreal.Surreal = MagicMock(return_value=_mock_surreal_instance)
sys.modules.setdefault("surrealdb", _mock_surreal)

import pytest
from datetime import timedelta

from app.auth import create_access_token


# ── Test Users ──

TEST_USER_A = {
    "id": "user:userA_001",
    "username": "alice",
    "wallet_address": "ALicE111111111111111111111111111111111111111",
    "role": "user",
    "is_active": True,
}

TEST_USER_B = {
    "id": "user:userB_002",
    "username": "bob",
    "wallet_address": "B0Bxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    "role": "user",
    "is_active": True,
}


@pytest.fixture
def user_a():
    return TEST_USER_A.copy()


@pytest.fixture
def user_b():
    return TEST_USER_B.copy()


@pytest.fixture
def token_a():
    """Valid JWT token for user A."""
    return create_access_token(data={"sub": "alice"}, expires_delta=timedelta(hours=1))


@pytest.fixture
def token_b():
    """Valid JWT token for user B."""
    return create_access_token(data={"sub": "bob"}, expires_delta=timedelta(hours=1))


@pytest.fixture
def expired_token():
    """Expired JWT token."""
    return create_access_token(
        data={"sub": "alice"}, expires_delta=timedelta(seconds=-10)
    )


@pytest.fixture
def auth_headers_a(token_a):
    """HTTP headers with auth for user A."""
    return {"Authorization": f"Bearer {token_a}"}


@pytest.fixture
def auth_headers_b(token_b):
    """HTTP headers with auth for user B."""
    return {"Authorization": f"Bearer {token_b}"}


@pytest.fixture
def tmp_dirs(tmp_path):
    """Create temp directory and patch settings."""
    temp = tmp_path / "temp"
    temp.mkdir()

    from app.config import settings

    orig_temp = settings.TEMP_DIR

    settings.TEMP_DIR = str(temp)

    yield {"temp": str(temp)}

    settings.TEMP_DIR = orig_temp
