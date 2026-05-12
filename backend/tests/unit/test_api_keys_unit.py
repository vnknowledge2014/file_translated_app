"""Unit Tests — API Key Management Logic.

Tests key generation format, hashing, prefix extraction, and scope validation.
"""



class TestApiKeyFormat:
    """Unit: API key format validation."""

    def test_key_format_itk_prefix(self):
        from app.auth import generate_api_key

        raw, _, _ = generate_api_key("read")
        assert raw.startswith("itk_read_")

    def test_key_format_translate_scope(self):
        from app.auth import generate_api_key

        raw, _, _ = generate_api_key("translate")
        assert raw.startswith("itk_translate_")

    def test_key_format_admin_scope(self):
        from app.auth import generate_api_key

        raw, _, _ = generate_api_key("admin")
        assert raw.startswith("itk_admin_")

    def test_key_has_random_part(self):
        from app.auth import generate_api_key

        raw, _, _ = generate_api_key("read")
        # Format: itk_{scope}_{32_hex_chars}
        parts = raw.split("_", 2)
        assert len(parts) == 3
        random_part = parts[2]
        assert len(random_part) == 32  # 16 bytes = 32 hex chars

    def test_key_length(self):
        from app.auth import generate_api_key

        raw, _, _ = generate_api_key("translate")
        # itk_ + translate_ + 32 hex = 4 + 10 + 32 = 46
        assert len(raw) > 30


class TestApiKeyHashing:
    """Unit: API key hashing produces consistent SHA-256."""

    def test_hash_is_sha256_length(self):
        from app.auth import hash_api_key

        h = hash_api_key("itk_read_abcdef1234567890abcdef12")
        assert len(h) == 64

    def test_hash_is_hex(self):
        from app.auth import hash_api_key

        h = hash_api_key("itk_read_test")
        assert all(c in "0123456789abcdef" for c in h)

    def test_same_input_same_hash(self):
        from app.auth import hash_api_key

        h1 = hash_api_key("itk_translate_abc123")
        h2 = hash_api_key("itk_translate_abc123")
        assert h1 == h2

    def test_different_input_different_hash(self):
        from app.auth import hash_api_key

        h1 = hash_api_key("itk_read_key1")
        h2 = hash_api_key("itk_read_key2")
        assert h1 != h2


class TestApiKeyPrefix:
    """Unit: Key prefix extraction for display."""

    def test_prefix_is_first_20_chars(self):
        from app.auth import generate_api_key

        raw, _, prefix = generate_api_key("translate")
        assert prefix == raw[:20]

    def test_prefix_length(self):
        from app.auth import generate_api_key

        _, _, prefix = generate_api_key("read")
        assert len(prefix) == 20

    def test_prefix_does_not_reveal_full_key(self):
        from app.auth import generate_api_key

        raw, _, prefix = generate_api_key("translate")
        assert len(prefix) < len(raw)


class TestScopeValidation:
    """Unit: Valid scope values."""

    def test_valid_scopes(self):
        from app.auth import SCOPE_HIERARCHY

        valid = {"read", "translate", "admin"}
        assert set(SCOPE_HIERARCHY.keys()) == valid

    def test_scope_ordering(self):
        from app.auth import SCOPE_HIERARCHY

        assert SCOPE_HIERARCHY["read"] < SCOPE_HIERARCHY["translate"]
        assert SCOPE_HIERARCHY["translate"] < SCOPE_HIERARCHY["admin"]
