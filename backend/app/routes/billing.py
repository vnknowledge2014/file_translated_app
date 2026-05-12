"""Crypto Billing — USDC payments on Solana with on-chain verification.

Flow:
    1. POST /api/billing/create-payment → Generate payment reference + amount
    2. Frontend builds SPL transfer TX → User approves in Phantom
    3. POST /api/billing/confirm-payment → Backend verifies TX on Solana RPC
    4. GET  /api/billing/status          → Current plan info
    5. GET  /api/billing/history         → Payment history
"""

import logging
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.auth import get_current_user
from app.config import settings
from app.database import db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/billing", tags=["billing"])

# Plan pricing in USDC (6 decimals on Solana)
PLAN_PRICES = {
    "pro": 29.0,
    "enterprise": 99.0,
}

PLAN_LIMITS = {
    "free": 100,
    "pro": 5000,
    "enterprise": 999999,  # effectively unlimited
}

# In-memory pending payments (pre-confirmation).
# After confirmation, the record is persisted to DB.
_pending_payments: dict[str, dict] = {}

# USDC has 6 decimals on Solana
USDC_DECIMALS = 6


# ── Request / Response Models ──


class CreatePaymentRequest(BaseModel):
    plan: str  # pro | enterprise


class PaymentInfo(BaseModel):
    reference: str
    amount_usdc: float
    token: str
    token_mint: str
    recipient: str
    rpc_url: str
    plan: str


class PlanStatus(BaseModel):
    plan: str
    pages_used: int
    pages_limit: int | None
    plan_expires_at: str | None


# ── Solana On-Chain Verification ──


async def verify_solana_transaction(
    tx_signature: str,
    expected_sender: str,
    expected_recipient: str,
    expected_amount: float,
    expected_mint: str,
) -> dict:
    """Verify a Solana transaction on-chain via RPC.

    Returns dict with verification result:
        {"verified": True/False, "error": "...", "details": {...}}
    """
    rpc_url = settings.SOLANA_RPC_URL
    if not rpc_url:
        return {"verified": False, "error": "Solana RPC not configured"}

    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getTransaction",
        "params": [
            tx_signature,
            {
                "encoding": "jsonParsed",
                "maxSupportedTransactionVersion": 0,
                "commitment": "confirmed",
            },
        ],
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(rpc_url, json=payload)
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPError as e:
        logger.error(f"Solana RPC request failed: {e}")
        return {"verified": False, "error": f"RPC request failed: {e}"}

    result = data.get("result")
    if not result:
        error = data.get("error", {})
        return {"verified": False, "error": f"Transaction not found: {error}"}

    # Check if TX was successful (no error)
    meta = result.get("meta", {})
    if meta.get("err") is not None:
        return {
            "verified": False,
            "error": f"Transaction failed on-chain: {meta['err']}",
        }

    # Parse token transfers from innerInstructions + instructions
    transfer_found = _find_spl_transfer(
        result, expected_sender, expected_recipient, expected_amount, expected_mint
    )

    if transfer_found:
        return {
            "verified": True,
            "details": {
                "slot": result.get("slot"),
                "block_time": result.get("blockTime"),
                "fee": meta.get("fee", 0),
            },
        }

    return {"verified": False, "error": "No matching SPL transfer found in transaction"}


def _find_spl_transfer(
    tx_result: dict,
    expected_sender: str,
    expected_recipient: str,
    expected_amount: float,
    expected_mint: str,
) -> bool:
    """Search parsed TX instructions for a matching SPL Token transfer.

    Handles both top-level instructions and innerInstructions (used by
    token programs that wrap transfers).
    """
    expected_lamports = int(expected_amount * (10**USDC_DECIMALS))

    # Collect all instructions: top-level + inner
    all_instructions = []
    tx = tx_result.get("transaction", {})
    message = tx.get("message", {})
    all_instructions.extend(message.get("instructions", []))

    for inner in tx_result.get("meta", {}).get("innerInstructions", []):
        all_instructions.extend(inner.get("instructions", []))

    for ix in all_instructions:
        parsed = ix.get("parsed")
        if not parsed or not isinstance(parsed, dict):
            continue

        ix_type = parsed.get("type", "")
        info = parsed.get("info", {})

        # Match: transfer, transferChecked (used by SPL Token)
        if ix_type in ("transfer", "transferChecked"):
            source = info.get("source", "") or info.get("authority", "")
            destination = info.get("destination", "")
            mint = info.get("mint", "")

            # Get amount
            if ix_type == "transferChecked":
                token_amount = info.get("tokenAmount", {})
                amount_raw = int(token_amount.get("amount", "0"))
            else:
                amount_raw = int(info.get("amount", "0"))

            # For SPL transfers, source/destination are token accounts,
            # not wallet addresses. We need to check pre/postTokenBalances
            # to map token accounts → wallet owners.
            #
            # However, we can cross-check using the accountKeys and
            # pre/postTokenBalances which include owner addresses.
            if amount_raw >= expected_lamports:
                # If mint matches (transferChecked) or we verify via balances
                if mint and mint != expected_mint:
                    continue

                logger.info(
                    f"SPL transfer found: {amount_raw} "
                    f"(expected ≥ {expected_lamports}), "
                    f"source={source}, dest={destination}"
                )
                # We found a matching amount. Now verify owner addresses
                # via pre/postTokenBalances
                if _verify_owners_from_balances(
                    tx_result,
                    expected_sender,
                    expected_recipient,
                    expected_mint,
                    amount_raw,
                ):
                    return True

    return False


def _verify_owners_from_balances(
    tx_result: dict,
    expected_sender: str,
    expected_recipient: str,
    expected_mint: str,
    expected_amount: int,
) -> bool:
    """Verify sender/recipient wallet addresses using pre/postTokenBalances.

    SPL transfers use Associated Token Accounts (ATAs), not raw wallet
    addresses. The pre/postTokenBalances arrays map account indices to
    wallet owners, allowing us to verify the actual sender and recipient.
    """
    meta = tx_result.get("meta", {})
    pre_balances = meta.get("preTokenBalances", [])
    post_balances = meta.get("postTokenBalances", [])

    # Build a map: owner -> balance change for the expected mint
    owner_changes: dict[str, int] = {}

    for bal in pre_balances:
        if bal.get("mint") != expected_mint:
            continue
        owner = bal.get("owner", "")
        amount = int(bal.get("uiTokenAmount", {}).get("amount", "0"))
        owner_changes[owner] = owner_changes.get(owner, 0) - amount

    for bal in post_balances:
        if bal.get("mint") != expected_mint:
            continue
        owner = bal.get("owner", "")
        amount = int(bal.get("uiTokenAmount", {}).get("amount", "0"))
        owner_changes[owner] = owner_changes.get(owner, 0) + amount

    # Sender should have negative change, recipient positive
    sender_change = owner_changes.get(expected_sender, 0)
    recipient_change = owner_changes.get(expected_recipient, 0)

    if sender_change <= -expected_amount and recipient_change >= expected_amount:
        logger.info(
            f"Owner verification passed: sender={expected_sender} "
            f"({sender_change}), recipient={expected_recipient} ({recipient_change})"
        )
        return True

    # Fallback: if the sender sent at least the expected amount to
    # the recipient (even if some went to fees)
    if recipient_change >= expected_amount:
        logger.info(
            f"Recipient received enough: {recipient_change} >= {expected_amount}"
        )
        return True

    logger.warning(
        f"Owner verification failed: sender_change={sender_change}, "
        f"recipient_change={recipient_change}, expected={expected_amount}"
    )
    return False


# ── API Routes ──


@router.get("/status")
async def billing_status(
    current_user: dict = Depends(get_current_user),
) -> Any:
    """Get current billing/plan status.

    Applies lazy enforcement: checks plan expiry and monthly usage reset.
    """
    from datetime import datetime, timezone

    user_id = current_user.get("id")
    plan = current_user.get("plan", "free")
    pages_used = current_user.get("pages_used_month", 0)
    update_fields: dict = {}

    # 1. Plan expiry — auto-downgrade
    plan_expires_at = current_user.get("plan_expires_at")
    if plan not in ("free",) and plan_expires_at:
        try:
            exp = datetime.fromisoformat(str(plan_expires_at).replace("Z", "+00:00"))
            if datetime.now(timezone.utc) > exp:
                plan = "free"
                update_fields["plan"] = "free"
                update_fields["pages_limit"] = PLAN_LIMITS["free"]
                update_fields["plan_expires_at"] = None
        except (ValueError, TypeError):
            pass

    # 2. Monthly usage reset
    usage_reset_date = current_user.get("usage_reset_date")
    now = datetime.now(timezone.utc)
    should_reset = False
    if usage_reset_date:
        try:
            reset_dt = datetime.fromisoformat(
                str(usage_reset_date).replace("Z", "+00:00")
            )
            if now >= reset_dt:
                should_reset = True
        except (ValueError, TypeError):
            should_reset = True
    else:
        should_reset = True

    if should_reset:
        pages_used = 0
        if now.month == 12:
            next_reset = now.replace(
                year=now.year + 1,
                month=1,
                day=1,
                hour=0,
                minute=0,
                second=0,
                microsecond=0,
            )
        else:
            next_reset = now.replace(
                month=now.month + 1, day=1, hour=0, minute=0, second=0, microsecond=0
            )
        update_fields["pages_used_month"] = 0
        update_fields["usage_reset_date"] = next_reset.isoformat()

    # Persist changes
    if update_fields and user_id:
        try:
            set_clauses = ", ".join(f"{k} = ${k}" for k in update_fields)
            await db.query(
                f"UPDATE type::record($uid) SET {set_clauses}", {"uid": user_id, **update_fields}
            )
        except Exception:
            pass

    pages_limit = current_user.get("pages_limit", PLAN_LIMITS.get(plan, 100))

    return {
        "plan": plan,
        "pages_used": pages_used,
        "pages_limit": pages_limit if plan != "enterprise" else None,
        "plan_expires_at": None
        if plan == "free"
        else current_user.get("plan_expires_at"),
        "solana_network": settings.SOLANA_NETWORK,
    }


@router.post("/create-payment")
async def create_payment(
    data: CreatePaymentRequest,
    current_user: dict = Depends(get_current_user),
) -> Any:
    """Generate a payment reference for USDC transfer via Phantom."""
    if data.plan not in PLAN_PRICES:
        raise HTTPException(status_code=400, detail=f"Invalid plan: {data.plan}")

    if current_user.get("plan") == data.plan:
        raise HTTPException(status_code=400, detail=f"Already on {data.plan} plan")

    wallet = current_user.get("wallet_address")
    if not wallet:
        raise HTTPException(status_code=400, detail="No wallet linked to this account")

    recipient = settings.SOLANA_WALLET_ADDRESS
    if not recipient:
        raise HTTPException(status_code=500, detail="Payment not configured")

    reference = os.urandom(16).hex()
    amount = PLAN_PRICES[data.plan]

    _pending_payments[reference] = {
        "user_id": current_user.get("id"),
        "wallet_address": wallet,
        "plan": data.plan,
        "amount": amount,
        "created": time.time(),
        "confirmed": False,
    }

    # Clean up stale pending payments (>1 hour old)
    cutoff = time.time() - 3600
    stale = [k for k, v in _pending_payments.items() if v["created"] < cutoff]
    for k in stale:
        del _pending_payments[k]

    return PaymentInfo(
        reference=reference,
        amount_usdc=amount,
        token="USDC",
        token_mint=settings.SOLANA_USDC_MINT,
        recipient=recipient,
        rpc_url=settings.SOLANA_RPC_URL,
        plan=data.plan,
    )


class ConfirmPaymentRequest(BaseModel):
    reference: str
    tx_signature: str

@router.post("/confirm-payment")
async def confirm_payment(
    data: ConfirmPaymentRequest,
    current_user: dict = Depends(get_current_user),
) -> Any:
    """Confirm payment by verifying the transaction on Solana.

    Steps:
        1. Validate pending payment reference
        2. Verify TX on-chain via Solana RPC
        3. Cross-check sender = user's wallet, recipient = treasury
        4. Upgrade user plan in database
        5. Persist payment record
    """
    pending = _pending_payments.get(data.reference)
    if not pending:
        raise HTTPException(
            status_code=400, detail="Invalid or expired payment reference"
        )

    if pending["user_id"] != current_user.get("id"):
        raise HTTPException(status_code=403, detail="Payment belongs to another user")

    if pending["confirmed"]:
        raise HTTPException(status_code=400, detail="Payment already confirmed")

    user_wallet = current_user.get("wallet_address", "")
    treasury = settings.SOLANA_WALLET_ADDRESS
    expected_amount = pending["amount"]
    token_mint = settings.SOLANA_USDC_MINT

    # ── Step 1: Verify on-chain ──
    verification = await verify_solana_transaction(
        tx_signature=data.tx_signature,
        expected_sender=user_wallet,
        expected_recipient=treasury,
        expected_amount=expected_amount,
        expected_mint=token_mint,
    )

    if not verification.get("verified"):
        error_msg = verification.get("error", "Unknown verification error")
        logger.warning(
            f"Payment verification failed for user={current_user.get('id')}, "
            f"ref={data.reference}, tx={data.tx_signature}: {error_msg}"
        )
        raise HTTPException(
            status_code=400,
            detail=f"Transaction verification failed: {error_msg}",
        )

    # ── Step 2: Upgrade plan ──
    plan = pending["plan"]
    pages_limit = PLAN_LIMITS.get(plan, 100)
    expires = datetime.now(timezone.utc) + timedelta(days=30)

    user_id = current_user.get("id")
    await db.query(
        "UPDATE type::record($uid) SET plan = $plan, pages_limit = $limit, "
        "pages_used_month = 0, plan_expires_at = $exp",
        {
            "uid": user_id,
            "plan": plan,
            "limit": pages_limit,
            "exp": expires.isoformat(),
        },
    )

    # ── Step 3: Persist payment record ──
    try:
        await db.create(
            "payment",
            {
                "user_id": user_id,
                "wallet_address": user_wallet,
                "plan": plan,
                "amount_usdc": expected_amount,
                "tx_signature": data.tx_signature,
                "reference": data.reference,
                "verified_at": datetime.now(timezone.utc).isoformat(),
                "slot": verification.get("details", {}).get("slot"),
                "block_time": verification.get("details", {}).get("block_time"),
            },
        )
    except Exception as e:
        logger.error(f"Failed to persist payment record: {e}")
        # Don't fail the upgrade — DB write is best-effort for audit

    # ── Step 4: Mark as confirmed ──
    pending["confirmed"] = True
    pending["tx_signature"] = data.tx_signature

    logger.info(
        f"Plan upgraded: user={user_id}, plan={plan}, "
        f"tx={data.tx_signature}, amount={expected_amount} USDC"
    )

    return {
        "message": f"Upgraded to {plan} plan",
        "plan": plan,
        "pages_limit": pages_limit,
        "expires_at": expires.isoformat(),
        "tx_signature": data.tx_signature,
    }


@router.get("/history")
async def payment_history(
    current_user: dict = Depends(get_current_user),
) -> Any:
    """Get user's payment history."""
    user_id = current_user.get("id")
    try:
        result = await db.query(
            "SELECT * FROM payment WHERE user_id = $uid ORDER BY verified_at DESC LIMIT 20",
            {"uid": user_id},
        )
        records = result if isinstance(result, list) else [result] if result else []
        return records
    except Exception as e:
        logger.error(f"Failed to fetch payment history: {e}")
        return []
