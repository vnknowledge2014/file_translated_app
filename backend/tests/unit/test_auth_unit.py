"""Unit Tests — Auth RBAC, Role Hierarchy, API Key Generation.

Tests:
- Role hierarchy logic
- Superadmin auto-promotion
- API key generation & hashing
- Token creation & validation
- require_role dependency
- require_scope dependency
"""

import pytest
from datetime import timedelta
from unittest.mock import patch


class TestRoleHierarchy:
    """Unit: ROLE_HIERARCHY values are correctly ordered."""

    def test_hierarchy_has_user(self):
        from app.auth import ROLE_HIERARCHY

        assert "user" in ROLE_HIERARCHY
        assert ROLE_HIERARCHY["user"] == 0

    def test_hierarchy_has_admin(self):
        from app.auth import ROLE_HIERARCHY

        assert "admin" in ROLE_HIERARCHY
        assert ROLE_HIERARCHY["admin"] == 1

    def test_hierarchy_has_superadmin(self):
        from app.auth import ROLE_HIERARCHY

        assert "superadmin" in ROLE_HIERARCHY
        assert ROLE_HIERARCHY["superadmin"] == 2

    def test_superadmin_higher_than_admin(self):
        from app.auth import ROLE_HIERARCHY

        assert ROLE_HIERARCHY["superadmin"] > ROLE_HIERARCHY["admin"]

    def test_admin_higher_than_user(self):
        from app.auth import ROLE_HIERARCHY

        assert ROLE_HIERARCHY["admin"] > ROLE_HIERARCHY["user"]


class TestScopeHierarchy:
    """Unit: SCOPE_HIERARCHY values are correctly ordered."""

    def test_scope_hierarchy_has_read(self):
        from app.auth import SCOPE_HIERARCHY

        assert "read" in SCOPE_HIERARCHY

    def test_scope_hierarchy_has_translate(self):
        from app.auth import SCOPE_HIERARCHY

        assert "translate" in SCOPE_HIERARCHY

    def test_scope_hierarchy_has_admin(self):
        from app.auth import SCOPE_HIERARCHY

        assert "admin" in SCOPE_HIERARCHY

    def test_translate_higher_than_read(self):
        from app.auth import SCOPE_HIERARCHY

        assert SCOPE_HIERARCHY["translate"] > SCOPE_HIERARCHY["read"]


class TestSuperadminPromotion:
    """Unit: _apply_role_promotion auto-promotes superadmin wallet."""

    def test_matching_wallet_promotes(self):
        from app.auth import _apply_role_promotion

        with patch("app.auth.SUPERADMIN_WALLET", "SUPER_WALLET_123"):
            user = {"role": "user", "wallet_address": "SUPER_WALLET_123"}
            result = _apply_role_promotion(user)
            assert result["role"] == "superadmin"

    def test_non_matching_wallet_stays_user(self):
        from app.auth import _apply_role_promotion

        with patch("app.auth.SUPERADMIN_WALLET", "SUPER_WALLET_123"):
            user = {"role": "user", "wallet_address": "SOME_OTHER_WALLET"}
            result = _apply_role_promotion(user)
            assert result["role"] == "user"

    def test_empty_superadmin_wallet_no_promotion(self):
        from app.auth import _apply_role_promotion

        with patch("app.auth.SUPERADMIN_WALLET", ""):
            user = {"role": "user", "wallet_address": "ANY_WALLET"}
            result = _apply_role_promotion(user)
            assert result["role"] == "user"

    def test_no_wallet_in_user_no_promotion(self):
        from app.auth import _apply_role_promotion

        with patch("app.auth.SUPERADMIN_WALLET", "SUPER_WALLET_123"):
            user = {"role": "user"}
            result = _apply_role_promotion(user)
            assert result["role"] == "user"


class TestApiKeyGeneration:
    """Unit: API key generation produces valid keys."""

    def test_key_starts_with_itk_prefix(self):
        from app.auth import generate_api_key

        raw_key, _, _ = generate_api_key("translate")
        assert raw_key.startswith("itk_translate_")

    def test_key_hash_is_sha256(self):
        from app.auth import generate_api_key

        _, key_hash, _ = generate_api_key("read")
        assert len(key_hash) == 64  # SHA-256 hex digest

    def test_key_prefix_length(self):
        from app.auth import generate_api_key

        _, _, key_prefix = generate_api_key("translate")
        assert len(key_prefix) == 20

    def test_different_keys_generate_different_hashes(self):
        from app.auth import generate_api_key

        _, hash1, _ = generate_api_key("read")
        _, hash2, _ = generate_api_key("read")
        assert hash1 != hash2

    def test_hash_api_key_consistency(self):
        from app.auth import hash_api_key

        raw = "itk_translate_abcdef1234567890"
        h1 = hash_api_key(raw)
        h2 = hash_api_key(raw)
        assert h1 == h2


class TestAccessToken:
    """Unit: JWT token creation and validation."""

    def test_create_token_returns_string(self):
        from app.auth import create_access_token

        token = create_access_token(data={"sub": "testuser"})
        assert isinstance(token, str)
        assert len(token) > 10

    def test_create_token_with_expiry(self):
        from app.auth import create_access_token

        token = create_access_token(
            data={"sub": "testuser"},
            expires_delta=timedelta(hours=1),
        )
        assert isinstance(token, str)

    def test_token_contains_subject(self):
        import jwt
        from app.auth import create_access_token, SECRET_KEY, ALGORITHM

        token = create_access_token(data={"sub": "mike"})
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["sub"] == "mike"

    def test_token_contains_expiry(self):
        import jwt
        from app.auth import create_access_token, SECRET_KEY, ALGORITHM

        token = create_access_token(
            data={"sub": "mike"}, expires_delta=timedelta(hours=2)
        )
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert "exp" in payload

    def test_expired_token_raises(self):
        import jwt
        from app.auth import create_access_token, SECRET_KEY, ALGORITHM

        token = create_access_token(
            data={"sub": "mike"}, expires_delta=timedelta(seconds=-10)
        )
        with pytest.raises(jwt.ExpiredSignatureError):
            jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
