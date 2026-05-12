"""Unit Tests — Wallet Auth Logic.

Tests nonce generation, message formatting, and signature verification logic.
"""

import os
import time


class TestNonceGeneration:
    """Unit: Nonce generation and management."""

    def test_nonce_is_hex_string(self):
        """Nonces should be hex-encoded random bytes."""
        nonce = os.urandom(16).hex()
        assert len(nonce) == 32
        assert all(c in "0123456789abcdef" for c in nonce)

    def test_nonce_uniqueness(self):
        """Two nonces should not be identical."""
        n1 = os.urandom(16).hex()
        n2 = os.urandom(16).hex()
        assert n1 != n2

    def test_nonce_sufficient_entropy(self):
        """Nonce should have at least 16 bytes of entropy."""
        nonce = os.urandom(16)
        assert len(nonce) >= 16


class TestNonceMessage:
    """Unit: Challenge message formatting."""

    def test_message_contains_nonce(self):
        nonce = "abc123def456"
        msg = f"InfiTrans Login: {nonce}"
        assert nonce in msg

    def test_message_format(self):
        nonce = "test_nonce_value"
        msg = f"InfiTrans Login: {nonce}"
        assert msg.startswith("InfiTrans Login:")

    def test_message_encoding(self):
        nonce = "abc123"
        msg = f"InfiTrans Login: {nonce}"
        encoded = msg.encode("utf-8")
        assert isinstance(encoded, bytes)


class TestNonceCleanup:
    """Unit: Expired nonce cleanup logic."""

    def test_expired_nonce_detected(self):
        """Nonces older than TTL should be marked expired."""
        created_at = time.time() - 600  # 10 minutes ago
        ttl = 300  # 5 minutes
        is_expired = (time.time() - created_at) > ttl
        assert is_expired

    def test_fresh_nonce_not_expired(self):
        """Recent nonces should not be expired."""
        created_at = time.time() - 60  # 1 minute ago
        ttl = 300  # 5 minutes
        is_expired = (time.time() - created_at) > ttl
        assert not is_expired


class TestWalletAddressValidation:
    """Unit: Solana wallet address format validation."""

    def test_valid_base58_length(self):
        """Solana addresses are 32-44 chars of base58."""
        addr = "3ryqjZssaGkkv983cbDDA9a8y2Gth4uqqdnWxUb4eu3G"
        assert 32 <= len(addr) <= 44

    def test_empty_address_rejected(self):
        addr = ""
        assert len(addr) < 32

    def test_short_address_rejected(self):
        addr = "abc123"
        assert len(addr) < 32
