import os
import uuid
from datetime import datetime, timezone

import redis.asyncio as aioredis
import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.middleware.auth import get_current_user
from app.models.job import Job
from app.models.uploaded_file import UploadedFile
from app.models.user import User
from app.models.user_quota import UserQuota
from app.schemas.users import QuotaResponse, UserResponse, UserUpdateRequest
from app.services.storage import LocalDiskBackend

log = structlog.get_logger()

router = APIRouter(prefix="/api/v1/users", tags=["users"])


def _get_upload_storage() -> LocalDiskBackend:
    base = os.getenv("STORAGE_BASE_PATH", "/app/volumes/uploads")
    return LocalDiskBackend(base)


def _get_output_storage() -> LocalDiskBackend:
    base = os.getenv("OUTPUT_BASE_PATH", "/app/volumes/outputs")
    return LocalDiskBackend(base)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return UserResponse.model_validate(current_user)


@router.patch("/me", response_model=UserResponse)
async def update_me(
    body: UserUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if body.email is not None:
        normalized_email = body.email.strip().lower()
        existing = await db.execute(
            select(User).where(User.email == normalized_email, User.id != current_user.id)
        )
        if existing.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"error": "email_taken", "message": "Email address already in use"},
            )
        current_user.email = normalized_email
        current_user.updated_at = datetime.now(timezone.utc)
        # Issue 8: catch the unique constraint violation that can slip through
        # the pre-check under concurrent requests and return a clean 409
        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"error": "email_taken", "message": "Email address already in use"},
            )
        await db.refresh(current_user)

    return UserResponse.model_validate(current_user)


@router.delete("/me", status_code=204)
async def delete_me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user_id = current_user.id
    user_id_str = str(user_id)

    # Collect storage keys before deletion — DB cascade will remove the rows
    upload_keys_result = await db.execute(
        select(UploadedFile.storage_key).where(UploadedFile.user_id == user_id)
    )
    upload_keys = [row[0] for row in upload_keys_result.all()]

    output_keys_result = await db.execute(
        select(Job.output_key).where(
            Job.user_id == user_id,
            Job.output_key.is_not(None),
        )
    )
    output_keys = [row[0] for row in output_keys_result.all()]

    # Revoke all active refresh tokens for this user from Redis DB1 (REDIS_AUTH_URL).
    # DB1 is the auth-only database (noeviction policy) — never use the broker (DB0)
    # or cache (DB2) URL here. Refresh tokens are stored as refresh:{sha256_hash}
    # with the value set to the user_id string; scan and delete all matching keys.
    redis_url = os.getenv("REDIS_AUTH_URL")
    if redis_url:
        try:
            redis_client = aioredis.from_url(redis_url, decode_responses=True)
            try:
                keys_to_delete = []
                async for key in redis_client.scan_iter("refresh:*"):
                    value = await redis_client.get(key)
                    if value == user_id_str:
                        keys_to_delete.append(key)
                if keys_to_delete:
                    await redis_client.delete(*keys_to_delete)
            finally:
                await redis_client.aclose()
        except Exception:
            log.warning("refresh_token_revocation_failed_on_user_delete", user_id=user_id_str)

    # Delete user — cascades to projects, jobs, uploaded_files, user_quotas, email_tokens
    await db.delete(current_user)
    await db.commit()

    log.info("user_deleted", user_id=user_id_str)

    # Remove disk files after DB commit (best-effort)
    upload_storage = _get_upload_storage()
    output_storage = _get_output_storage()
    cleanup_fail_count = 0

    for _key in upload_keys:
        try:
            await upload_storage.delete(_key)
        except Exception:
            # Issue 4: never log the storage key
            cleanup_fail_count += 1

    for _key in output_keys:
        try:
            await output_storage.delete(_key)
        except Exception:
            # Issue 4: never log the output key
            cleanup_fail_count += 1

    # Issue 6: emit a single structured audit event when any disk cleanup fails
    if cleanup_fail_count > 0:
        log.warning(
            "user_deletion_cleanup_incomplete",
            user_id=user_id_str,
            failed_file_count=cleanup_fail_count,
        )


@router.get("/me/quota", response_model=QuotaResponse)
async def get_quota(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(UserQuota).where(UserQuota.user_id == current_user.id)
    )
    quota = result.scalar_one_or_none()

    if quota is None:
        # Create a default quota record on first access
        today = datetime.now(timezone.utc).date()
        await db.execute(
            pg_insert(UserQuota).values(
                user_id=current_user.id,
                renders_today=0,
                renders_this_month=0,
                daily_limit=int(os.getenv("DEFAULT_DAILY_RENDER_LIMIT", "10")),
                monthly_limit=int(os.getenv("DEFAULT_MONTHLY_RENDER_LIMIT", "100")),
                day_reset_at=today,
                month_reset_at=today.replace(day=1),
                updated_at=datetime.now(timezone.utc),
            ).on_conflict_do_nothing(index_elements=["user_id"])
        )
        await db.commit()
        result = await db.execute(
            select(UserQuota).where(UserQuota.user_id == current_user.id)
        )
        quota = result.scalar_one()

    return QuotaResponse.model_validate(quota)
