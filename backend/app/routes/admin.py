"""Admin Dashboard API — Platform management for superadmin.

All routes require `superadmin` role (identified by SUPERADMIN_WALLET).

Endpoints:
    GET  /api/admin/stats                → Platform overview stats
    GET  /api/admin/users                → List all users (paginated, filterable)
    GET  /api/admin/users/{id}           → User detail + stats
    PUT  /api/admin/users/{id}           → Update user (role, plan, limits, active)
    POST /api/admin/users/{id}/disable   → Disable/enable user account
    GET  /api/admin/jobs                 → List all jobs (filterable)
    GET  /api/admin/jobs/{id}            → Job detail (any user's job)
    DELETE /api/admin/jobs/{id}          → Delete a job
    GET  /api/admin/billing/revenue      → Revenue analytics
    GET  /api/admin/billing/payments     → All payment records
    GET  /api/admin/system/health        → Extended system health
    GET  /api/admin/system/config        → Current platform config (non-sensitive)
    PUT  /api/admin/system/config        → Update runtime config
"""

import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from app.auth import require_role
from app.config import settings
from app.database import db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["Admin"])


# ── Request/Response Models ──


class AdminUserUpdate(BaseModel):
    role: Optional[str] = None  # user | admin | superadmin
    plan: Optional[str] = None  # free | pro | enterprise
    pages_limit: Optional[int] = None
    is_active: Optional[bool] = None
    username: Optional[str] = None


class AdminUserDisable(BaseModel):
    is_active: bool


class AdminConfigUpdate(BaseModel):
    registration_enabled: Optional[bool] = None
    max_file_size: Optional[int] = None
    max_workers: Optional[int] = None


# ── Helper: parse SurrealDB query results ──


def _parse_result(result) -> list:
    """Parse SurrealDB query result into a list of records."""
    if isinstance(result, list):
        return result
    return [result] if result else []


def _parse_count(result) -> int:
    """Parse SurrealDB count() result."""
    records = _parse_result(result)
    if records and isinstance(records[0], dict):
        return records[0].get("count", 0)
    return 0


# ══════════════════════════════════════════════════════
#  Platform Stats
# ══════════════════════════════════════════════════════


@router.get("/stats")
async def platform_stats(
    current_user: dict = Depends(require_role("superadmin")),
) -> Any:
    """Platform-wide statistics for the admin dashboard."""
    try:
        # User counts
        users_total = await db.query("SELECT count() FROM user GROUP ALL")
        users_active = await db.query(
            "SELECT count() FROM user WHERE is_active = true OR is_active IS NONE GROUP ALL"
        )

        # Job counts
        jobs_total = await db.query("SELECT count() FROM jobs GROUP ALL")
        jobs_by_status = await db.query(
            "SELECT status, count() FROM jobs GROUP BY status"
        )

        # Revenue
        revenue_total = await db.query(
            "SELECT math::sum(amount_usdc) AS total FROM payment GROUP ALL"
        )
        revenue_month = await db.query(
            "SELECT math::sum(amount_usdc) AS total FROM payment "
            "WHERE verified_at >= time::now() - 30d GROUP ALL"
        )

        # Recent jobs (last 10)
        recent_jobs = await db.query(
            "SELECT id, filename, status, progress, owner_id, "
            "source_lang, target_lang, duration_seconds, created_at "
            "FROM jobs ORDER BY created_at DESC LIMIT 10"
        )

        # Parse results
        total_users = _parse_count(users_total)
        active_users = _parse_count(users_active)
        total_jobs = _parse_count(jobs_total)

        status_breakdown = {}
        for rec in _parse_result(jobs_by_status):
            status_breakdown[rec.get("status", "unknown")] = rec.get("count", 0)

        revenue_records = _parse_result(revenue_total)
        total_revenue = revenue_records[0].get("total", 0) if revenue_records else 0

        month_records = _parse_result(revenue_month)
        month_revenue = month_records[0].get("total", 0) if month_records else 0

        # Storage stats (best-effort)
        storage_info = _get_storage_stats()

        return {
            "users": {
                "total": total_users,
                "active": active_users,
            },
            "jobs": {
                "total": total_jobs,
                "by_status": status_breakdown,
            },
            "revenue": {
                "total_usdc": total_revenue or 0,
                "this_month_usdc": month_revenue or 0,
            },
            "storage": storage_info,
            "recent_jobs": _parse_result(recent_jobs),
        }
    except Exception as e:
        logger.error(f"Admin stats error: {e}", exc_info=True)
        raise HTTPException(500, "Failed to fetch platform stats")


def _get_storage_stats() -> dict:
    """Get storage usage stats (best-effort, non-failing)."""
    try:
        from app.storage import storage

        uploads_size = 0
        outputs_size = 0
        uploads_count = 0
        outputs_count = 0
        for obj in storage.client.list_objects(storage.uploads_bucket, recursive=True):
            uploads_size += obj.size or 0
            uploads_count += 1
        for obj in storage.client.list_objects(storage.outputs_bucket, recursive=True):
            outputs_size += obj.size or 0
            outputs_count += 1
        return {
            "uploads_bytes": uploads_size,
            "uploads_count": uploads_count,
            "outputs_bytes": outputs_size,
            "outputs_count": outputs_count,
            "total_bytes": uploads_size + outputs_size,
        }
    except Exception:
        return {
            "uploads_bytes": 0,
            "outputs_bytes": 0,
            "total_bytes": 0,
            "error": "Storage unavailable",
        }


# ══════════════════════════════════════════════════════
#  User Management
# ══════════════════════════════════════════════════════


@router.get("/users")
async def list_all_users(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    plan: Optional[str] = None,
    role: Optional[str] = None,
    is_active: Optional[bool] = None,
    current_user: dict = Depends(require_role("superadmin")),
) -> Any:
    """List all users with filtering and pagination."""
    conditions = []
    params: dict = {}

    if search:
        conditions.append(
            "(username CONTAINS $search OR wallet_address CONTAINS $search)"
        )
        params["search"] = search
    if plan:
        conditions.append("plan = $plan")
        params["plan"] = plan
    if role:
        conditions.append("role = $role")
        params["role"] = role
    if is_active is not None:
        conditions.append("is_active = $is_active")
        params["is_active"] = is_active

    where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""

    # Count total
    count_result = await db.query(
        f"SELECT count() FROM user{where_clause} GROUP ALL", params
    )
    total = _parse_count(count_result)

    # Paginated query
    offset = (page - 1) * limit
    params["limit"] = limit
    params["start"] = offset

    result = await db.query(
        f"SELECT id, username, wallet_address, role, plan, pages_used_month, "
        f"pages_limit, is_active, created_at "
        f"FROM user{where_clause} "
        f"ORDER BY created_at DESC LIMIT $limit START $start",
        params,
    )

    return {
        "users": _parse_result(result),
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit if total > 0 else 0,
    }


@router.get("/users/{user_id}")
async def get_user_detail(
    user_id: str,
    current_user: dict = Depends(require_role("superadmin")),
) -> Any:
    """Get detailed info for a specific user."""
    # Ensure user_id has table prefix
    uid = user_id if user_id.startswith("user:") else f"user:{user_id}"

    result = await db.query("SELECT * FROM type::record($uid)", {"uid": uid})
    records = _parse_result(result)
    if not records:
        raise HTTPException(404, "User not found")

    user_data = records[0]

    # Get user's job count
    jobs_result = await db.query(
        "SELECT count() FROM jobs WHERE owner_id = $uid GROUP ALL",
        {"uid": uid},
    )
    user_data["jobs_count"] = _parse_count(jobs_result)

    # Get user's recent jobs
    recent_jobs = await db.query(
        "SELECT id, filename, status, created_at FROM jobs "
        "WHERE owner_id = $uid ORDER BY created_at DESC LIMIT 5",
        {"uid": uid},
    )
    user_data["recent_jobs"] = _parse_result(recent_jobs)

    # Get user's payment history
    payments = await db.query(
        "SELECT * FROM payment WHERE user_id = $uid ORDER BY verified_at DESC LIMIT 10",
        {"uid": uid},
    )
    user_data["payments"] = _parse_result(payments)

    return user_data


@router.put("/users/{user_id}")
async def update_user(
    user_id: str,
    data: AdminUserUpdate,
    current_user: dict = Depends(require_role("superadmin")),
) -> Any:
    """Update user properties (role, plan, limits, active status)."""
    uid = user_id if user_id.startswith("user:") else f"user:{user_id}"

    # Build update fields
    update_fields: dict = {}
    if data.role is not None:
        if data.role not in ("user", "admin", "superadmin"):
            raise HTTPException(
                400, "Invalid role. Must be: user, admin, or superadmin"
            )
        update_fields["role"] = data.role
    if data.plan is not None:
        from app.routes.billing import PLAN_LIMITS

        if data.plan not in PLAN_LIMITS:
            raise HTTPException(
                400, f"Invalid plan. Must be one of: {list(PLAN_LIMITS.keys())}"
            )
        update_fields["plan"] = data.plan
        update_fields["pages_limit"] = PLAN_LIMITS[data.plan]
    if data.pages_limit is not None:
        update_fields["pages_limit"] = data.pages_limit
    if data.is_active is not None:
        update_fields["is_active"] = data.is_active
    if data.username is not None:
        update_fields["username"] = data.username

    if not update_fields:
        raise HTTPException(400, "No fields to update")

    # Build SET clause
    set_clauses = ", ".join(f"{k} = ${k}" for k in update_fields)
    await db.query(
        f"UPDATE type::record($uid) SET {set_clauses}",
        {"uid": uid, **update_fields},
    )

    logger.info(
        f"Admin {current_user.get('username')} updated user {uid}: {update_fields}"
    )

    return {
        "message": f"User {user_id} updated",
        "updated_fields": list(update_fields.keys()),
    }


@router.post("/users/{user_id}/disable")
async def disable_user(
    user_id: str,
    data: AdminUserDisable,
    current_user: dict = Depends(require_role("superadmin")),
) -> Any:
    """Disable or enable a user account."""
    uid = user_id if user_id.startswith("user:") else f"user:{user_id}"

    # Prevent self-disable
    if uid == current_user.get("id"):
        raise HTTPException(400, "Cannot disable your own account")

    await db.query(
        "UPDATE type::record($uid) SET is_active = $active",
        {"uid": uid, "active": data.is_active},
    )

    action = "enabled" if data.is_active else "disabled"
    logger.info(f"Admin {current_user.get('username')} {action} user {uid}")

    return {"message": f"User {user_id} {action}"}


# ══════════════════════════════════════════════════════
#  Job Monitor
# ══════════════════════════════════════════════════════


@router.get("/jobs")
async def list_all_jobs(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    owner_id: Optional[str] = None,
    source_lang: Optional[str] = None,
    target_lang: Optional[str] = None,
    current_user: dict = Depends(require_role("superadmin")),
) -> Any:
    """List all jobs across the platform with filters."""
    conditions = []
    params: dict = {}

    if status:
        conditions.append("status = $status")
        params["status"] = status
    if owner_id:
        conditions.append("owner_id = $owner_id")
        params["owner_id"] = owner_id
    if source_lang:
        conditions.append("source_lang = $source_lang")
        params["source_lang"] = source_lang
    if target_lang:
        conditions.append("target_lang = $target_lang")
        params["target_lang"] = target_lang

    where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""

    # Count
    count_result = await db.query(
        f"SELECT count() FROM jobs{where_clause} GROUP ALL", params
    )
    total = _parse_count(count_result)

    # Paginated query
    offset = (page - 1) * limit
    params["limit"] = limit
    params["start"] = offset

    result = await db.query(
        f"SELECT * FROM jobs{where_clause} "
        f"ORDER BY created_at DESC LIMIT $limit START $start",
        params,
    )

    return {
        "jobs": _parse_result(result),
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit if total > 0 else 0,
    }


@router.get("/jobs/{job_id}")
async def get_job_detail(
    job_id: str,
    current_user: dict = Depends(require_role("superadmin")),
) -> Any:
    """Get job detail (admin can view any user's job)."""
    clean_id = job_id.split(":")[-1]
    jid = f"jobs:{clean_id}"

    result = await db.select(jid)
    if not result:
        raise HTTPException(404, "Job not found")

    return result[0] if isinstance(result, list) and len(result) > 0 else result


@router.delete("/jobs/{job_id}")
async def delete_job(
    job_id: str,
    current_user: dict = Depends(require_role("superadmin")),
) -> Any:
    """Delete a job and its associated data."""
    clean_id = job_id.split(":")[-1]
    jid = f"jobs:{clean_id}"

    # Delete associated segments
    await db.query(
        "DELETE segment_reviews WHERE job_id = $jid",
        {"jid": job_id},
    )

    # Delete job attempts
    await db.query(
        "DELETE job_attempts WHERE job_id = $jid",
        {"jid": job_id},
    )

    # Delete the job
    await db.delete(jid)

    logger.info(f"Admin {current_user.get('username')} deleted job {jid}")

    return {"message": f"Job {job_id} deleted"}


# ══════════════════════════════════════════════════════
#  Billing / Revenue Analytics
# ══════════════════════════════════════════════════════


@router.get("/billing/revenue")
async def revenue_analytics(
    period: str = Query("30d", regex="^(7d|30d|90d|365d|all)$"),
    current_user: dict = Depends(require_role("superadmin")),
) -> Any:
    """Revenue analytics — total USDC by period."""
    time_filter = ""
    if period != "all":
        time_filter = f" WHERE verified_at >= time::now() - {period}"

    # Total revenue for period
    total_result = await db.query(
        f"SELECT math::sum(amount_usdc) AS total, count() AS count "
        f"FROM payment{time_filter} GROUP ALL"
    )
    total_records = _parse_result(total_result)
    total = total_records[0] if total_records else {"total": 0, "count": 0}

    # Revenue by plan
    by_plan = await db.query(
        f"SELECT plan, math::sum(amount_usdc) AS total, count() AS count "
        f"FROM payment{time_filter} GROUP BY plan"
    )

    # Users by plan (current distribution)
    users_by_plan = await db.query("SELECT plan, count() FROM user GROUP BY plan")

    return {
        "period": period,
        "total_usdc": total.get("total", 0) or 0,
        "total_payments": total.get("count", 0) or 0,
        "by_plan": _parse_result(by_plan),
        "users_by_plan": _parse_result(users_by_plan),
    }


@router.get("/billing/payments")
async def list_all_payments(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(require_role("superadmin")),
) -> Any:
    """List all payment records across the platform."""
    offset = (page - 1) * limit

    count_result = await db.query("SELECT count() FROM payment GROUP ALL")
    total = _parse_count(count_result)

    result = await db.query(
        "SELECT * FROM payment ORDER BY verified_at DESC LIMIT $limit START $start",
        {"limit": limit, "start": offset},
    )

    return {
        "payments": _parse_result(result),
        "total": total,
        "page": page,
        "limit": limit,
    }


# ══════════════════════════════════════════════════════
#  System Health & Config
# ══════════════════════════════════════════════════════


@router.get("/system/health")
async def system_health(
    current_user: dict = Depends(require_role("superadmin")),
) -> Any:
    """Extended system health — more detail than /api/health."""
    from app.llm.factory import create_llm_client

    # LLM health
    llm_ok = False
    try:
        client = create_llm_client(
            url=settings.OLLAMA_URL,
            timeout=10,
        )
        llm_ok = await client.health_check()
        await client.close()
    except Exception:
        pass

    # DB health
    db_ok = False
    db_info = {}
    try:
        result = await db.query("INFO FOR DB;")
        raw = result[0] if isinstance(result, list) and result else result
        db_info = raw if isinstance(raw, dict) else {}
        db_ok = True
    except Exception:
        pass

    # Table counts
    table_counts = {}
    if db_ok:
        for table in [
            "user",
            "jobs",
            "glossary",
            "payment",
            "api_key",
            "segment_reviews",
        ]:
            try:
                count_res = await db.query(f"SELECT count() FROM {table} GROUP ALL")
                table_counts[table] = _parse_count(count_res)
            except Exception:
                table_counts[table] = -1

    # Storage health
    storage_ok = False
    storage_info = {}
    try:
        from app.storage import storage as s

        s.client.list_buckets()
        storage_ok = True
        storage_info = _get_storage_stats()
    except Exception:
        pass

    return {
        "status": "ok" if (llm_ok and db_ok and storage_ok) else "degraded",
        "llm": {
            "status": "connected" if llm_ok else "disconnected",
            "backend": settings.LLM_BACKEND,
            "model": settings.MODEL,
            "url": settings.OLLAMA_URL,
        },
        "database": {
            "status": "connected" if db_ok else "disconnected",
            "url": settings.SURREALDB_URL,
            "tables": table_counts,
        },
        "storage": {
            "status": "connected" if storage_ok else "disconnected",
            "url": settings.MINIO_URL,
            **storage_info,
        },
        "config": {
            "max_workers": settings.MAX_WORKERS,
            "max_file_size_mb": settings.MAX_FILE_SIZE // (1024 * 1024),
            "registration_enabled": settings.REGISTRATION_ENABLED,
            "source_lang": settings.SOURCE_LANG,
            "target_lang": settings.TARGET_LANG,
            "default_domain": settings.DEFAULT_DOMAIN,
        },
    }


@router.get("/system/config")
async def get_platform_config(
    current_user: dict = Depends(require_role("superadmin")),
) -> Any:
    """Get current platform configuration (non-sensitive values only)."""
    return {
        "llm": {
            "backend": settings.LLM_BACKEND,
            "model": settings.MODEL,
            "ollama_url": settings.OLLAMA_URL,
            "ollama_timeout": settings.OLLAMA_TIMEOUT,
            "ollama_think": settings.OLLAMA_THINK,
        },
        "translation": {
            "temperature": settings.TRANSLATION_TEMPERATURE,
            "num_ctx": settings.TRANSLATION_NUM_CTX,
            "max_retries": settings.TRANSLATION_MAX_RETRIES,
            "max_concurrent_batches": settings.MAX_CONCURRENT_BATCHES,
            "top_k": settings.TOP_K,
            "top_p": settings.TOP_P,
            "repetition_penalty": settings.REPETITION_PENALTY,
        },
        "extraction": {
            "max_inline_tags": settings.MAX_INLINE_TAGS,
            "max_segment_chars": settings.MAX_SEGMENT_CHARS,
            "batch_max_chars": settings.BATCH_MAX_CHARS,
            "batch_max_segments": settings.BATCH_MAX_SEGMENTS,
        },
        "security": {
            "max_file_size": settings.MAX_FILE_SIZE,
            "max_file_size_mb": settings.MAX_FILE_SIZE // (1024 * 1024),
            "registration_enabled": settings.REGISTRATION_ENABLED,
            "file_retention_days": settings.FILE_RETENTION_DAYS,
            "cors_origins": settings.CORS_ORIGINS,
        },
        "workers": {
            "max_workers": settings.MAX_WORKERS,
        },
        "language": {
            "source_lang": settings.SOURCE_LANG,
            "target_lang": settings.TARGET_LANG,
            "default_domain": settings.DEFAULT_DOMAIN,
        },
    }


@router.put("/system/config")
async def update_platform_config(
    request: Request,
    data: AdminConfigUpdate,
    current_user: dict = Depends(require_role("superadmin")),
) -> Any:
    """Update runtime platform configuration.

    Note: These changes are runtime-only and will be reset on restart.
    For persistent changes, update the .env file.
    """
    changes = {}

    if data.registration_enabled is not None:
        settings.REGISTRATION_ENABLED = data.registration_enabled
        changes["registration_enabled"] = data.registration_enabled

    if data.max_file_size is not None:
        if data.max_file_size < 1024 * 1024:  # minimum 1MB
            raise HTTPException(400, "max_file_size must be at least 1MB")
        settings.MAX_FILE_SIZE = data.max_file_size
        changes["max_file_size"] = data.max_file_size

    if data.max_workers is not None:
        if data.max_workers < 1 or data.max_workers > 16:
            raise HTTPException(400, "max_workers must be between 1 and 16")
        settings.MAX_WORKERS = data.max_workers
        changes["max_workers"] = data.max_workers
        
        # Actually resize the worker pool
        pool = request.app.state.worker_pool
        await pool.resize(data.max_workers)

    if not changes:
        raise HTTPException(400, "No configuration changes provided")

    logger.info(
        f"Admin {current_user.get('username')} updated platform config: {changes}"
    )

    return {
        "message": "Configuration updated (runtime only, restart will reset)",
        "changes": changes,
    }
