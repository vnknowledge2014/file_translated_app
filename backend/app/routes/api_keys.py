"""API Key management routes — Create, List, Revoke.

All routes require JWT authentication (API keys cannot manage other API keys).
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.auth import get_current_user, generate_api_key
from app.database import db

router = APIRouter(prefix="/api/keys", tags=["API Keys"])


from pydantic import BaseModel, Field

class CreateKeyRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=64, pattern=r'^[a-zA-Z0-9_\-\s]+$')
    scope: str = "translate"  # read | translate | admin


class CreateKeyResponse(BaseModel):
    """Returned only once — contains the plaintext key."""

    id: str
    name: str
    key: str  # Plaintext key (shown once only!)
    key_prefix: str
    scope: str
    message: str = "Save this key — it will not be shown again."


class KeyInfo(BaseModel):
    """Public key info (no hash or plaintext)."""

    id: str
    name: str
    key_prefix: str
    scope: str
    requests_count: int
    requests_limit: int | None
    pages_used: int
    pages_limit: int | None
    last_used: str | None
    is_active: bool
    created_at: str


@router.post("", response_model=CreateKeyResponse)
async def create_api_key(
    data: CreateKeyRequest,
    current_user: dict = Depends(get_current_user),
) -> Any:
    """Create a new API key for the authenticated user.

    The plaintext key is returned ONCE in the response.
    Only the SHA-256 hash is stored in the database.
    """
    # Only JWT users can create keys (not API key users)
    if current_user.get("_auth_method") == "api_key":
        raise HTTPException(
            status_code=403,
            detail="API keys cannot create other API keys. Use JWT login.",
        )

    # Validate scope
    if data.scope not in ("read", "translate", "admin"):
        raise HTTPException(400, "Invalid scope. Must be: read, translate, or admin")

    # Generate key
    raw_key, key_hash, key_prefix = generate_api_key(data.scope)

    # Store in DB
    from app.models import ApiKey

    key_obj = ApiKey(
        owner_id=current_user.get("id"),
        name=data.name,
        key_hash=key_hash,
        key_prefix=key_prefix,
        scope=data.scope,
    )

    created = await db.create(
        "api_key", key_obj.model_dump(exclude={"id"}, mode="json")
    )
    record = created[0] if isinstance(created, list) else created

    return CreateKeyResponse(
        id=record.get("id"),
        name=data.name,
        key=raw_key,
        key_prefix=key_prefix,
        scope=data.scope,
    )


@router.get("")
async def list_api_keys(
    current_user: dict = Depends(get_current_user),
) -> list[KeyInfo]:
    """List all API keys for the authenticated user."""
    owner_id = current_user.get("id")

    result = await db.query(
        "SELECT * FROM api_key WHERE owner_id = $owner_id ORDER BY created_at DESC",
        {"owner_id": owner_id},
    )
    records = result if isinstance(result, list) else [result] if result else []
    if isinstance(records, dict):
        records = [records] if records else []
    elif not isinstance(records, list):
        records = list(records) if records else []

    return [
        KeyInfo(
            id=r.get("id", ""),
            name=r.get("name", ""),
            key_prefix=r.get("key_prefix", ""),
            scope=r.get("scope", "read"),
            requests_count=r.get("requests_count", 0),
            requests_limit=r.get("requests_limit"),
            pages_used=r.get("pages_used", 0),
            pages_limit=r.get("pages_limit"),
            last_used=str(r["last_used"]) if r.get("last_used") else None,
            is_active=r.get("is_active", True),
            created_at=str(r.get("created_at", "")),
        )
        for r in records
    ]


@router.delete("/{key_id}")
async def revoke_api_key(
    key_id: str,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Revoke (deactivate) an API key.

    Only the key owner can revoke their keys.
    """
    owner_id = current_user.get("id")

    # Verify ownership
    result = await db.query(
        "SELECT * FROM type::record($kid) WHERE owner_id = $owner_id LIMIT 1",
        {"kid": key_id, "owner_id": owner_id},
    )
    records = result if isinstance(result, list) else [result] if result else []
    if isinstance(records, dict):
        records = [records] if records else []
    elif not isinstance(records, list):
        records = list(records) if records else []

    if not records:
        raise HTTPException(404, "API key not found or not owned by you")

    # Deactivate
    await db.query(
        "UPDATE type::record($kid) SET is_active = false",
        {"kid": key_id},
    )

    return {"message": f"API key revoked: {key_id}"}
