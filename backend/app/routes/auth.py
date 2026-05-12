"""Authentication routes — Wallet-only auth.

Auth flows:
    GET  /api/auth/me   → Current user info (requires JWT or API Key)
    PUT  /api/auth/me   → Update profile (username)

Wallet login is handled by routes/wallet_auth.py.
"""

import re
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.auth import get_current_user
from app.database import db

router = APIRouter(prefix="/api/auth", tags=["auth"])


class UserResponse(BaseModel):
    id: str
    username: str
    role: str
    wallet_address: str | None = None
    plan: str = "free"


class UpdateProfileRequest(BaseModel):
    username: str | None = None


@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: dict = Depends(get_current_user)):
    return UserResponse(
        id=current_user.get("id"),
        username=current_user.get("username"),
        role=current_user.get("role"),
        wallet_address=current_user.get("wallet_address"),
        plan=current_user.get("plan", "free"),
    )


@router.put("/me")
async def update_profile(
    data: UpdateProfileRequest,
    current_user: dict = Depends(get_current_user),
) -> Any:
    """Update user profile (username)."""
    user_id = current_user.get("id")
    updates: dict = {}

    if data.username is not None:
        name = data.username.strip()
        if len(name) < 2 or len(name) > 32:
            raise HTTPException(400, "Username must be 2-32 characters")
        if not re.match(r"^[a-zA-Z0-9_.\- ]+$", name):
            raise HTTPException(
                400, "Username can only contain letters, numbers, spaces, and _.-"
            )

        # Check uniqueness
        result = await db.query(
            "SELECT id FROM user WHERE username = $u AND id != $uid LIMIT 1",
            {"u": name, "uid": user_id},
        )
        records = result if isinstance(result, list) else [result] if result else []
        if records:
            raise HTTPException(409, "Username already taken")

        updates["username"] = name

    if not updates:
        raise HTTPException(400, "No fields to update")

    set_clauses = ", ".join(f"{k} = ${k}" for k in updates)
    await db.query(f"UPDATE type::record($uid) SET {set_clauses}", {"uid": user_id, **updates})

    return {"message": "Profile updated", **updates}
