import asyncio
import os
import time
from pathlib import Path

import structlog
from sqlalchemy import select

from app.db import AsyncSessionLocal
from app.models.uploaded_file import UploadedFile
from app.services.storage import LocalDiskBackend
from app.worker import celery_app

log = structlog.get_logger()


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
    # Implemented in Layer 4
    raise NotImplementedError("process_full_render not yet implemented")


@celery_app.task(name="app.tasks.cleanup_orphan_files", acks_late=True)
def cleanup_orphan_files():
    asyncio.run(_cleanup_orphan_files())


async def _cleanup_orphan_files():
    storage_base = os.getenv("STORAGE_BASE_PATH", "/app/volumes/uploads")
    base = Path(storage_base)

    if not base.exists():
        log.warning("orphan_cleanup_storage_dir_missing")
        return

    # Collect all storage keys currently tracked in the database
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(UploadedFile.storage_key))
        db_keys = {row[0] for row in result.fetchall()}

    # Scan disk — only top-level files; subdirectories are not used by this storage backend
    now = time.time()
    min_age_seconds = 24 * 60 * 60  # 24 hours — files modified within the last 24 hours
    #                                  are skipped to avoid racing with active or delayed uploads
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
    # Implemented in Layer 4
    log.warning("cleanup_expired_outputs_not_implemented")
