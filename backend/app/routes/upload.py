"""Upload route — POST /api/upload → save file + create job + queue to worker pool."""

import logging
import os
import uuid

from fastapi import APIRouter, File, Request, UploadFile, Form, Depends, HTTPException
from app.auth import get_current_user
from app.config import settings
from app.database import create_job
from app.storage import storage
from app.utils.file_detect import detect_file_type
from app.worker import JobItem

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/upload")
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    export_xliff: bool = Form(False),
    xliff_version: str = Form("2.1"),
    no_translate: bool = Form(False),
    webhook_url: str = Form(None),
    domain: str = Form(None),
    source_lang: str = Form(None),
    target_lang: str = Form(None),
    current_user: dict = Depends(get_current_user),
):
    """Upload a document for translation.

    Validates file type, saves to upload dir, creates job record,
    and submits to the worker pool queue.

    Returns:
        {"job_id": str, "filename": str, "file_type": str, "status": "queued",
         "queue_position": int}
    """
    # Validate file type
    safe_filename = (file.filename or "unknown").replace("/", "").replace("\\", "")
    file_type = detect_file_type(safe_filename)
    if not file_type:
        return {"error": f"Unsupported file type: {safe_filename}"}

    # ── Plan enforcement (lazy evaluation — no cron needed) ──
    from app.routes.billing import PLAN_LIMITS
    from app.database import db
    from datetime import datetime, timezone

    user_id = current_user.get("id")
    plan = current_user.get("plan", "free")
    pages_used = current_user.get("pages_used_month", 0)
    needs_db_update = False
    update_fields: dict = {}

    # 1. Plan expiry check — auto-downgrade to free if expired
    plan_expires_at = current_user.get("plan_expires_at")
    if plan not in ("free",) and plan_expires_at:
        try:
            exp = datetime.fromisoformat(str(plan_expires_at).replace("Z", "+00:00"))
            if datetime.now(timezone.utc) > exp:
                logger.info(f"Plan expired for user {user_id}: {plan} → free")
                plan = "free"
                update_fields["plan"] = "free"
                update_fields["pages_limit"] = PLAN_LIMITS["free"]
                update_fields["plan_expires_at"] = None
                needs_db_update = True
        except (ValueError, TypeError):
            pass

    # 2. Monthly usage reset — reset counter on new calendar month
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
        # No reset date set yet — initialize it
        should_reset = True

    if should_reset:
        pages_used = 0
        # Next reset = 1st of next month at 00:00 UTC
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
        needs_db_update = True

    # Persist any changes
    if needs_db_update and user_id:
        try:
            set_clauses = ", ".join(f"{k} = ${k}" for k in update_fields)
            await db.query(
                f"UPDATE type::record($uid) SET {set_clauses}", {"uid": user_id, **update_fields}
            )
        except Exception as e:
            logger.warning(f"Failed to update user plan/usage: {e}")

    # 3. Quota check
    page_limit = PLAN_LIMITS.get(plan, 100)
    if pages_used >= page_limit:
        raise HTTPException(
            status_code=429,
            detail=f"Monthly page limit reached ({pages_used}/{page_limit}). "
            f"Upgrade your plan to continue translating.",
        )

    # Save to temp directory first
    unique_prefix = uuid.uuid4().hex[:8]
    object_name = f"{unique_prefix}_{safe_filename}"
    temp_path = os.path.join(settings.TEMP_DIR, object_name)
    os.makedirs(os.path.dirname(temp_path), exist_ok=True)

    # Stream file to disk in chunks to avoid loading entire file into memory (OOM prevention)
    total_size = 0
    chunk_size = 64 * 1024  # 64KB chunks
    try:
        with open(temp_path, "wb") as f:
            while True:
                chunk = await file.read(chunk_size)
                if not chunk:
                    break
                total_size += len(chunk)
                if settings.MAX_FILE_SIZE and total_size > settings.MAX_FILE_SIZE:
                    f.close()
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                    raise HTTPException(
                        status_code=413,
                        detail=f"File too large. Maximum size: {settings.MAX_FILE_SIZE // (1024 * 1024)}MB",
                    )
                f.write(chunk)
    except HTTPException:
        raise
    except Exception:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise

    # Upload to MinIO
    try:
        s3_uri = storage.upload_file(storage.uploads_bucket, object_name, temp_path)
    finally:
        # Clean up temp file
        if os.path.exists(temp_path):
            os.remove(temp_path)

    # Create job record
    job = await create_job(
        filename=safe_filename,
        file_type=file_type,
        file_path=s3_uri,
        domain=domain or settings.DEFAULT_DOMAIN,
        source_lang=source_lang or settings.SOURCE_LANG,
        target_lang=target_lang or settings.TARGET_LANG,
        owner_id=current_user.get("id"),
    )
    job_id = job.id

    # Submit to worker pool (bounded by MAX_WORKERS)
    pool = request.app.state.worker_pool
    await pool.submit(
        JobItem(
            app=request.app,
            job_id=job_id,
            file_path=s3_uri,
            file_type=file_type,
            filename=safe_filename,
            export_xliff=export_xliff,
            xliff_version=xliff_version,
            no_translate=no_translate,
            webhook_url=webhook_url,
            domain=domain or settings.DEFAULT_DOMAIN,
            source_lang=source_lang or settings.SOURCE_LANG,
            target_lang=target_lang or settings.TARGET_LANG,
            owner_id=current_user.get("id"),
        )
    )

    return {
        "job_id": job_id,
        "filename": safe_filename,
        "file_type": file_type,
        "status": "queued",
        "queue_depth": pool.queue_size,
        "active_jobs": pool.active_count,
    }
