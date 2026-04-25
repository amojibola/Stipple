import os
import uuid
from datetime import datetime, timezone

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
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
        existing = await db.execute(
            select(User).where(User.email == body.email, User.id != current_user.id)
        )
        if existing.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"error": "email_taken", "message": "Email address already in use"},
            )
        current_user.email = body.email
        current_user.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(current_user)

    return UserResponse.model_validate(current_user)


@router.delete("/me", status_code=204)
async def delete_me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user_id = current_user.id

    # Collect all storage keys before deletion so we can remove files from disk
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

    # Delete user — cascades to projects, jobs, uploaded_files, user_quotas, email_tokens
    await db.delete(current_user)
    await db.commit()

    log.info("user_deleted", user_id=str(user_id))

    # Remove disk files after DB commit (best-effort)
    upload_storage = _get_upload_storage()
    output_storage = _get_output_storage()

    for key in upload_keys:
        try:
            await upload_storage.delete(key)
        except Exception:
            log.warning("storage_delete_failed_on_user_delete", storage_key=key)

    for key in output_keys:
        try:
            await output_storage.delete(key)
        except Exception:
            log.warning("output_delete_failed_on_user_delete", storage_key=key)


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
