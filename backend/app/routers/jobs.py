import os
import uuid
from datetime import date, datetime, timedelta, timezone

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
import io
from sqlalchemy import select, update as sa_update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.middleware.auth import get_current_user
from app.models.job import Job
from app.models.project import Project
from app.models.uploaded_file import UploadedFile
from app.models.user import User
from app.models.user_quota import UserQuota
from app.schemas.jobs import JobCreateRequest, JobCreateResponse, JobStatusResponse
from app.services.storage import LocalDiskBackend

log = structlog.get_logger()

router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])


def _get_output_storage() -> LocalDiskBackend:
    base = os.getenv("OUTPUT_BASE_PATH", "/app/volumes/outputs")
    return LocalDiskBackend(base)


async def _check_and_increment_quota(db: AsyncSession, user_id: uuid.UUID) -> None:
    """Check and increment quota within the caller's transaction.

    Uses SELECT FOR UPDATE to lock the quota row so concurrent requests cannot
    both read the same counter value and both pass the limit check.
    Does NOT commit — the caller is responsible for committing the full transaction.
    """
    today = date.today()
    current_month_start = today.replace(day=1)

    # Lock the quota row for the duration of this transaction
    result = await db.execute(
        select(UserQuota).where(UserQuota.user_id == user_id).with_for_update()
    )
    quota = result.scalar_one_or_none()

    if quota is None:
        # INSERT ON CONFLICT DO NOTHING handles concurrent first-time row creation:
        # only one INSERT wins; the other silently does nothing.
        await db.execute(
            pg_insert(UserQuota).values(
                user_id=user_id,
                renders_today=0,
                renders_this_month=0,
                daily_limit=int(os.getenv("DEFAULT_DAILY_RENDER_LIMIT", "10")),
                monthly_limit=int(os.getenv("DEFAULT_MONTHLY_RENDER_LIMIT", "100")),
                day_reset_at=today,
                month_reset_at=current_month_start,
                updated_at=datetime.now(timezone.utc),
            ).on_conflict_do_nothing(index_elements=["user_id"])
        )
        # Re-select with lock so both paths always hold the row lock before modifying
        result = await db.execute(
            select(UserQuota).where(UserQuota.user_id == user_id).with_for_update()
        )
        quota = result.scalar_one()

    if quota.day_reset_at < today:
        quota.renders_today = 0
        quota.day_reset_at = today

    if quota.month_reset_at < current_month_start:
        quota.renders_this_month = 0
        quota.month_reset_at = current_month_start

    if quota.renders_today >= quota.daily_limit:
        reset_at = (today + timedelta(days=1)).isoformat()
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "quota_exceeded",
                "message": f"Daily render limit of {quota.daily_limit} reached.",
                "reset_at": reset_at,
            },
        )

    if quota.renders_this_month >= quota.monthly_limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "quota_exceeded",
                "message": f"Monthly render limit of {quota.monthly_limit} reached.",
            },
        )

    quota.renders_today += 1
    quota.renders_this_month += 1
    quota.updated_at = datetime.now(timezone.utc)


@router.post("", response_model=JobCreateResponse, status_code=202)
async def create_job(
    body: JobCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Verify file ownership BEFORE consuming quota so a bad file ID does not
    # drain the user's daily allowance
    file_result = await db.execute(
        select(UploadedFile).where(UploadedFile.id == body.source_file_id)
    )
    source_file = file_result.scalar_one_or_none()
    if source_file is None or source_file.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "not_found", "message": "Source file not found"},
        )

    # Check and increment quota — no commit here, all in the same transaction
    await _check_and_increment_quota(db, current_user.id)

    params_dict = body.parameters.model_dump()

    project = Project(
        user_id=current_user.id,
        name="Untitled",
        source_file_id=source_file.id,
        parameters=params_dict,
        status="processing",
    )
    db.add(project)
    await db.flush()

    job = Job(
        project_id=project.id,
        user_id=current_user.id,
        job_type="render",
        status="queued",
    )
    db.add(job)
    await db.flush()

    # Commit quota + project + job in one transaction before dispatching.
    # The worker must be able to find the job row, so it must exist in the DB
    # before the task is enqueued.
    await db.commit()

    from app.tasks import process_full_render
    try:
        task = process_full_render.apply_async(args=[str(job.id)], queue="render")
    except Exception as exc:
        # Broker unavailable or other dispatch error — mark the job failed so it
        # is never stuck in "queued" and the caller gets an immediate error response.
        log.error("job_dispatch_failed", job_id=str(job.id), exc_type=type(exc).__name__)
        job.status = "failed"
        job.error_message = "Dispatch failed"
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "service_unavailable", "message": "Render service is unavailable, please try again"},
        )

    # Store the Celery task ID for observability (best effort — non-critical)
    job.celery_task_id = task.id
    await db.commit()

    log.info("job_created", job_id=str(job.id), user_id=str(current_user.id))
    return JobCreateResponse(job_id=job.id)


@router.get("/{job_id}/status", response_model=JobStatusResponse)
async def get_job_status(
    job_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()

    if job is None or job.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "not_found", "message": "Job not found"},
        )

    return JobStatusResponse(
        job_id=job.id,
        status=job.status,
        queued_at=job.queued_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        duration_ms=job.duration_ms,
        error_message=job.error_message,
    )


@router.get("/{job_id}/result")
async def get_job_result(
    job_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()

    if job is None or job.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "not_found", "message": "Job not found"},
        )

    if job.status != "complete" or job.output_key is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "not_ready", "message": "Result not available yet"},
        )

    storage = _get_output_storage()
    try:
        data = await storage.load(job.output_key)
    except FileNotFoundError:
        log.error("output_file_missing", job_id=str(job_id))
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "not_found", "message": "Result file not found"},
        )

    return StreamingResponse(
        io.BytesIO(data),
        media_type="image/png",
        headers={
            "Content-Disposition": f'attachment; filename="stipple_{job_id}.png"',
            "Cache-Control": "private, no-store",
        },
    )
