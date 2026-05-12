"""Wallet Authentication — Phantom/Solana wallet login.

Flow:
    1. POST /api/auth/wallet/challenge   → Get nonce to sign
    2. POST /api/auth/wallet/verify      → Verify signature → JWT
    3. POST /api/auth/wallet/link        → Link wallet to existing account (requires JWT)
"""

import os
import time
from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.auth import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    create_access_token,
    get_current_user,
)
from app.database import db

router = APIRouter(prefix="/api/auth/wallet", tags=["wallet-auth"])

# In-memory nonce store (short-lived)
_nonces: dict[str, dict] = {}


def _cleanup_nonces():
    """Remove expired nonces (older than 5 min)."""
    now = time.time()
    expired = [k for k, v in _nonces.items() if now - v.get("created", 0) > 300]
    for k in expired:
        del _nonces[k]


def _verify_solana_signature(message: str, signature_hex: str, pubkey: str) -> bool:
    """Verify an Ed25519 signature from Phantom wallet.

    Uses nacl (PyNaCl) for Ed25519 verification.
    """
    try:
        import base58
        import nacl.signing

        # Decode public key from base58
        pubkey_bytes = base58.b58decode(pubkey)
        verify_key = nacl.signing.VerifyKey(pubkey_bytes)

        # Decode signature from hex
        sig_bytes = bytes.fromhex(signature_hex)

        # Verify
        message_bytes = message.encode("utf-8")
        verify_key.verify(message_bytes, sig_bytes)
        return True
    except Exception:
        return False


# ── Request/Response Models ──


class ChallengeRequest(BaseModel):
    wallet_address: str


class ChallengeResponse(BaseModel):
    nonce: str
    message: str


class VerifyRequest(BaseModel):
    wallet_address: str
    signature: str  # Hex-encoded Ed25519 signature
    nonce: str


class LinkWalletRequest(BaseModel):
    wallet_address: str
    signature: str
    nonce: str


class WalletUserResponse(BaseModel):
    id: str
    username: str
    wallet_address: str
    role: str
    plan: str


# ══════════════════════════════════════════════════════
#  Challenge (Step 1)
# ══════════════════════════════════════════════════════


@router.post("/challenge", response_model=ChallengeResponse)
async def wallet_challenge(data: ChallengeRequest) -> Any:
    """Generate a nonce for the wallet to sign."""
    _cleanup_nonces()

    nonce = os.urandom(16).hex()
    message = f"Sign this message to login to InfiTrans.\n\nNonce: {nonce}\nWallet: {data.wallet_address}"

    _nonces[nonce] = {
        "wallet_address": data.wallet_address,
        "message": message,
        "created": time.time(),
    }

    return ChallengeResponse(nonce=nonce, message=message)


# ══════════════════════════════════════════════════════
#  Verify Signature (Step 2) → JWT
# ══════════════════════════════════════════════════════


@router.post("/verify")
async def wallet_verify(data: VerifyRequest) -> Any:
    """Verify wallet signature and issue JWT.

    If wallet is not registered, auto-creates a new user.
    """
    _cleanup_nonces()

    # Validate nonce
    pending = _nonces.pop(data.nonce, None)
    if not pending:
        raise HTTPException(status_code=400, detail="Invalid or expired nonce")

    if pending["wallet_address"] != data.wallet_address:
        raise HTTPException(status_code=400, detail="Wallet address mismatch")

    # Verify signature
    if not _verify_solana_signature(
        pending["message"], data.signature, data.wallet_address
    ):
        raise HTTPException(status_code=400, detail="Invalid signature")

    # Find or create user
    result = await db.query(
        "SELECT * FROM user WHERE wallet_address = $addr LIMIT 1",
        {"addr": data.wallet_address},
    )
    records = result
    if not isinstance(records, list):
        records = [records] if records else []

    if records:
        user = records[0]
    else:
        # Auto-create user with wallet
        short_addr = data.wallet_address[:8]
        username = f"wallet_{short_addr}"

        # Ensure unique username
        check = await db.query(
            "SELECT * FROM user WHERE username = $u LIMIT 1", {"u": username}
        )
        existing = check
        if not isinstance(existing, list):
            existing = [existing] if existing else []
        if existing:
            username = f"wallet_{short_addr}_{os.urandom(2).hex()}"

        # Create user (wallet-only, no password needed)
        user_data = {
            "username": username,
            "role": "user",
            "wallet_address": data.wallet_address,
            "plan": "free",
            "pages_used_month": 0,
            "pages_limit": 100,
            "is_active": True,
        }
        created = await db.create("user", user_data)
        user = created[0] if isinstance(created, list) else created

    if not user.get("is_active", True):
        raise HTTPException(status_code=400, detail="Account is disabled")

    # Issue JWT
    access_token = create_access_token(
        data={"sub": user.get("username")},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.get("id"),
            "username": user.get("username"),
            "wallet_address": data.wallet_address,
            "role": user.get("role", "user"),
            "plan": user.get("plan", "free"),
        },
    }


# ══════════════════════════════════════════════════════
#  Link Wallet to Existing Account
# ══════════════════════════════════════════════════════


@router.post("/link")
async def link_wallet(
    data: LinkWalletRequest,
    current_user: dict = Depends(get_current_user),
) -> Any:
    """Link a Solana wallet to an existing account."""
    _cleanup_nonces()

    pending = _nonces.pop(data.nonce, None)
    if not pending:
        raise HTTPException(status_code=400, detail="Invalid or expired nonce")

    if pending["wallet_address"] != data.wallet_address:
        raise HTTPException(status_code=400, detail="Wallet address mismatch")

    if not _verify_solana_signature(
        pending["message"], data.signature, data.wallet_address
    ):
        raise HTTPException(status_code=400, detail="Invalid signature")

    # Check if wallet is already linked to another account
    result = await db.query(
        "SELECT * FROM user WHERE wallet_address = $addr LIMIT 1",
        {"addr": data.wallet_address},
    )
    records = result
    if not isinstance(records, list):
        records = [records] if records else []

    if records and records[0].get("id") != current_user.get("id"):
        raise HTTPException(
            status_code=400, detail="Wallet is already linked to another account"
        )

    # Link wallet
    user_id = current_user.get("id")
    await db.query(
        "UPDATE type::record($uid) SET wallet_address = $addr",
        {"uid": user_id, "addr": data.wallet_address},
    )

    return {"message": f"Wallet {data.wallet_address[:8]}... linked successfully"}
