"""Authentication module — JWT + API Key dual auth with RBAC.

Supports two authentication methods:
1. JWT Bearer token (for Web UI users via Phantom wallet)
2. API Key via X-API-Key header or ?api_key= query param (for API integrations)

Role hierarchy:
    user < admin < superadmin

The superadmin is identified by wallet address configured in SUPERADMIN_WALLET env var.

Usage:
    # Standard auth (accepts both JWT and API Key)
    @router.get("/resource")
    async def get_resource(user = Depends(get_current_user)):
        ...

    # Scope-restricted auth
    @router.post("/upload")
    async def upload(user = Depends(require_scope("translate"))):
        ...

    # Role-restricted auth (admin endpoints)
    @router.get("/admin/stats")
    async def stats(user = Depends(require_role("superadmin"))):
        ...
"""

import hashlib
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, Header, Query, status
from fastapi.security import OAuth2PasswordBearer

from app.config import settings

SECRET_KEY = settings.SECRET_KEY
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/auth/wallet/verify", auto_error=False
)

# ── Scope hierarchy ──
SCOPE_HIERARCHY = {"read": 0, "translate": 1, "admin": 2}

# ── Role hierarchy ──
ROLE_HIERARCHY = {"user": 0, "admin": 1, "superadmin": 2}

# Superadmin wallet address (highest platform privileges)
SUPERADMIN_WALLET = settings.SUPERADMIN_WALLET


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def hash_api_key(raw_key: str) -> str:
    """Hash an API key using SHA-256."""
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def generate_api_key(scope: str = "translate") -> tuple[str, str, str]:
    """Generate a new API key.

    Returns:
        Tuple of (raw_key, key_hash, key_prefix).
    """
    random_part = os.urandom(16).hex()  # 32 hex chars
    raw_key = f"itk_{scope}_{random_part}"
    key_hash = hash_api_key(raw_key)
    key_prefix = raw_key[:20]  # "itk_translate_a1b2c3"
    return raw_key, key_hash, key_prefix


def _apply_role_promotion(user: dict) -> dict:
    """Auto-promote user to superadmin if their wallet matches SUPERADMIN_WALLET."""
    if SUPERADMIN_WALLET and user.get("wallet_address") == SUPERADMIN_WALLET:
        user["role"] = "superadmin"
    return user


async def _resolve_jwt(token: str) -> dict:
    """Resolve user from JWT token."""
    from app.database import db

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception

    # Fetch user from SurrealDB
    result = await db.query(
        "SELECT * FROM user WHERE username = $username LIMIT 1", {"username": username}
    )
    # SDK v2 returns records directly
    records = result
    if not isinstance(records, list):
        records = [records] if records else []

    if not records:
        raise credentials_exception

    user = records[0]
    # JWT users get full admin scope
    user["_api_key_scope"] = "admin"
    user["_auth_method"] = "jwt"
    # Auto-promote superadmin by wallet address
    _apply_role_promotion(user)
    return user


async def authenticate_token(token: str) -> dict:
    """Manually authenticate a raw JWT token (used for SSE)."""
    return await _resolve_jwt(token)


async def _resolve_api_key(raw_key: str) -> dict:
    """Resolve user from API key."""
    from app.database import db

    key_h = hash_api_key(raw_key)

    result = await db.query(
        "SELECT * FROM api_key WHERE key_hash = $hash AND is_active = true LIMIT 1",
        {"hash": key_h},
    )
    records = result
    if not isinstance(records, list):
        records = [records] if records else []

    if not records:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or revoked API key",
        )

    api_key_record = records[0]

    # Check quota
    if api_key_record.get("requests_limit") is not None:
        if api_key_record.get("requests_count", 0) >= api_key_record["requests_limit"]:
            raise HTTPException(
                status_code=429,
                detail="API key request quota exceeded",
            )

    # Update usage stats (fire-and-forget)
    key_id = api_key_record.get("id")
    try:
        await db.query(
            "UPDATE type::record($kid) SET requests_count += 1, last_used = time::now()",
            {"kid": key_id},
        )
    except Exception:
        pass

    # Fetch the owner user
    owner_id = api_key_record.get("owner_id")
    user_result = await db.query(
        "SELECT * FROM type::record($uid) LIMIT 1", {"uid": owner_id}
    )
    user_records = user_result
    if not isinstance(user_records, list):
        user_records = [user_records] if user_records else []

    if not user_records:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key owner not found",
        )

    user = user_records[0]
    user["_api_key_scope"] = api_key_record.get("scope", "read")
    user["_api_key_id"] = key_id
    user["_auth_method"] = "api_key"
    # Auto-promote superadmin by wallet address
    _apply_role_promotion(user)
    return user


async def get_current_user(
    authorization: Optional[str] = Header(None),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    api_key_param: Optional[str] = Query(None, alias="api_key"),
    token: Optional[str] = Depends(oauth2_scheme),
) -> dict:
    """Resolve user from JWT Bearer token or API Key.

    Priority:
    1. Authorization: Bearer <JWT>
    2. X-API-Key: itk_xxx header
    3. ?api_key=itk_xxx query param
    4. OAuth2 scheme (Bearer from Authorization header)
    """
    # 1. Check X-API-Key header first
    key = x_api_key or api_key_param
    if key and key.startswith("itk_"):
        return await _resolve_api_key(key)

    # 2. JWT from Authorization header or OAuth2 scheme
    jwt_token = None
    if authorization and authorization.startswith("Bearer "):
        jwt_token = authorization[7:]
    elif token:
        jwt_token = token

    if jwt_token:
        return await _resolve_jwt(jwt_token)

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required. Connect your Phantom wallet or provide an API key.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def require_scope(required: str):
    """FastAPI dependency that checks API key scope.

    Usage:
        @router.post("/upload")
        async def upload(user = Depends(require_scope("translate"))):
            ...
    """

    async def checker(user: dict = Depends(get_current_user)):
        scope = user.get("_api_key_scope", "admin")
        if SCOPE_HIERARCHY.get(scope, 0) < SCOPE_HIERARCHY.get(required, 0):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient scope. Required: '{required}', got: '{scope}'",
            )
        return user

    return checker


def require_role(required: str):
    """FastAPI dependency that checks user role.

    Role hierarchy: user < admin < superadmin

    Usage:
        @router.get("/admin/stats")
        async def stats(user = Depends(require_role("superadmin"))):
            ...
    """

    async def checker(user: dict = Depends(get_current_user)):
        user_role = user.get("role", "user")
        if ROLE_HIERARCHY.get(user_role, 0) < ROLE_HIERARCHY.get(required, 0):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient role. Required: '{required}', got: '{user_role}'",
            )
        return user

    return checker
