import asyncio
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import cv2
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool

# Import all models so SQLAlchemy can resolve foreign keys in the Celery worker process
from app.models.audit_log import AuditLog
from app.models.job import Job
from app.models.project import Project
from app.models.uploaded_file import UploadedFile
from app.models.user import User  # noqa: F401
from app.models.user_quota import UserQuota  # noqa: F401
from app.models.email_token import EmailToken  # noqa: F401
from app.services.stipple import compute_seed, stipple_image
from app.services.storage import LocalDiskBackend
from app.worker import celery_app

log = structlog.get_logger()

# NullPool prevents connection reuse across asyncio.run() calls in Celery workers.
# Each task invocation creates a fresh event loop via asyncio.run(), so pooled
# connections from prior runs would be attached to a defunct loop.
_task_engine = create_async_engine(
    os.getenv("DATABASE_URL", ""),
    poolclass=NullPool,
)
_TaskSession = async_sessionmaker(_task_engine, class_=AsyncSession, expire_on_commit=False)


def _get_upload_storage() -> LocalDiskBackend:
    return LocalDiskBackend(os.getenv("STORAGE_BASE_PATH", "/app/volumes/uploads"))


def _get_output_storage() -> LocalDiskBackend:
    return LocalDiskBackend(os.getenv("OUTPUT_BASE_PATH", "/app/volumes/outputs"))


@celery_app.task(
    name="app.tasks.process_full_render",
    bind=True,
    max_retries=3,
    default_retry_delay=2,
    acks_late=True,
    soft_time_limit=270,
    time_limit=300,
)
def process_full_render(self, job_id: str):
    asyncio.run(_do_full_render(self, job_id))


async def _do_full_render(task_self, job_id: str) -> None:
    # duration_ms measures total task wall time from first DB read to final DB write,
    # including database queries and file I/O — not just image processing time.
    start = time.monotonic()

    # Load all necessary data in one async context
    async with _TaskSession() as session:
        job_result = await session.execute(select(Job).where(Job.id == job_id))
        job = job_result.scalar_one_or_none()
        if job is None:
            log.error("render_job_not_found", job_id=job_id)
            return

        proj_result = await session.execute(
            select(Project).where(Project.id == job.project_id)
        )
        project = proj_result.scalar_one_or_none()
        if project is None or project.source_file_id is None:
            job.status = "failed"
            job.error_message = "Project or source file missing"
            job.completed_at = datetime.now(timezone.utc)
            await session.commit()
            return

        file_result = await session.execute(
            select(UploadedFile).where(UploadedFile.id == project.source_file_id)
        )
        source_file = file_result.scalar_one_or_none()
        if source_file is None:
            job.status = "failed"
            job.error_message = "Source file record missing"
            job.completed_at = datetime.now(timezone.utc)
            await session.commit()
            return

        source_path = _get_upload_storage().resolve_path(source_file.storage_key)
        params_dict = project.parameters
        output_size = (source_file.width_px, source_file.height_px)
        source_file_id = str(source_file.id)
        project_id = str(project.id)

        # Mark as processing
        job.status = "processing"
        job.started_at = datetime.now(timezone.utc)
        await session.commit()

    # Run stipple synchronously — we're the only coroutine in this event loop
    try:
        seed = compute_seed(source_file_id, params_dict)
        canvas = stipple_image(source_path, params_dict, output_size, seed)

        _, buf = cv2.imencode(".png", canvas)
        png_bytes = bytes(buf)

        output_key = f"{job_id}.png"
        output_storage = _get_output_storage()
        await output_storage.save(png_bytes, output_key)

        duration_ms = int((time.monotonic() - start) * 1000)

        async with _TaskSession() as session:
            job_result = await session.execute(select(Job).where(Job.id == job_id))
            job = job_result.scalar_one_or_none()
            if job is not None:
                job.status = "complete"
                job.output_key = output_key
                job.duration_ms = duration_ms
                job.completed_at = datetime.now(timezone.utc)

                proj_result = await session.execute(
                    select(Project).where(Project.id == job.project_id)
                )
                project = proj_result.scalar_one_or_none()
                if project is not None:
                    project.status = "ready"

                await session.commit()

        log.info("render_complete", job_id=job_id, duration_ms=duration_ms)

    except Exception as exc:
        log.error("render_failed", job_id=job_id, exc_type=type(exc).__name__)
        if task_self.request.retries >= task_self.max_retries:
            async with _TaskSession() as session:
                job_result = await session.execute(select(Job).where(Job.id == job_id))
                job = job_result.scalar_one_or_none()
                if job is not None:
                    job.status = "failed"
                    job.error_message = type(exc).__name__
                    job.completed_at = datetime.now(timezone.utc)

                    proj_result = await session.execute(
                        select(Project).where(Project.id == job.project_id)
                    )
                    project = proj_result.scalar_one_or_none()
                    if project is not None:
                        project.status = "failed"

                    await session.commit()
            return
        # Sanitize the exception before passing to Celery retry to prevent file paths
        # or storage keys from appearing in worker logs via the exception message.
        sanitized_exc = RuntimeError(f"{type(exc).__name__}: render processing failed")
        raise task_self.retry(exc=sanitized_exc, countdown=2 ** (task_self.request.retries + 1))


@celery_app.task(name="app.tasks.cleanup_orphan_files", acks_late=True)
def cleanup_orphan_files():
    asyncio.run(_cleanup_orphan_files())


async def _cleanup_orphan_files():
    storage_base = os.getenv("STORAGE_BASE_PATH", "/app/volumes/uploads")
    base = Path(storage_base)

    if not base.exists():
        log.warning("orphan_cleanup_storage_dir_missing")
        return

    async with _TaskSession() as session:
        result = await session.execute(select(UploadedFile.storage_key))
        db_keys = {row[0] for row in result.fetchall()}

    now = time.time()
    min_age_seconds = 24 * 60 * 60
    try:
        disk_files = [
            f.name for f in base.iterdir()
            if f.is_file() and (now - f.stat().st_mtime) > min_age_seconds
        ]
    except OSError:
        log.error("orphan_cleanup_scan_failed")
        return

    total = len(disk_files)
    orphans = [name for name in disk_files if name not in db_keys]

    log.info("orphan_cleanup_started", total_files=total, orphan_files=len(orphans))

    storage = LocalDiskBackend(storage_base)
    deleted = 0
    errors = 0

    for key in orphans:
        try:
            await storage.delete(key)
            deleted += 1
            log.info("orphan_file_deleted")
        except Exception:
            log.error("orphan_cleanup_delete_failed")
            errors += 1

    log.info(
        "orphan_cleanup_complete",
        total_scanned=total,
        orphans_found=len(orphans),
        orphans_deleted=deleted,
        errors=errors,
    )


@celery_app.task(name="app.tasks.cleanup_expired_outputs", acks_late=True)
def cleanup_expired_outputs():
    asyncio.run(_cleanup_expired_outputs())


async def _cleanup_expired_outputs():
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    output_storage = _get_output_storage()

    async with _TaskSession() as session:
        result = await session.execute(
            select(Job).where(
                Job.status == "complete",
                Job.completed_at < cutoff,
                Job.output_key.is_not(None),
            )
        )
        jobs_to_clean = result.scalars().all()

        deleted = 0
        errors = 0
        for job in jobs_to_clean:
            try:
                await output_storage.delete(job.output_key)
                job.output_key = None
                # Status set to "expired" so the status endpoint accurately reflects
                # that the job ran successfully but the output file is no longer available.
                job.status = "expired"
                deleted += 1
            except Exception:
                log.error("expired_output_delete_failed", job_id=str(job.id))
                errors += 1

        await session.commit()

    log.info(
        "expired_outputs_cleanup_complete",
        deleted=deleted,
        errors=errors,
    )


@celery_app.task(name="app.tasks.cleanup_old_audit_logs", acks_late=True)
def cleanup_old_audit_logs():
    asyncio.run(_cleanup_old_audit_logs())


async def _cleanup_old_audit_logs():
    from sqlalchemy import delete
    cutoff = datetime.now(timezone.utc) - timedelta(days=90)
    async with _TaskSession() as session:
        result = await session.execute(
            delete(AuditLog).where(AuditLog.created_at < cutoff)
        )
        deleted = result.rowcount
        await session.commit()
    log.info("audit_log_cleanup_complete", deleted=deleted)
