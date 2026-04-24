import hashlib
import os
import uuid
import io

import structlog
from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from PIL import Image
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.middleware.auth import get_current_user
from app.models.uploaded_file import UploadedFile
from app.models.user import User
from app.schemas.images import FileUploadResponse
from app.services.storage import LocalDiskBackend

# Module-level — must be set before any Image.open() call
Image.MAX_IMAGE_PIXELS = 8_000_000

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_DIMENSION = 4000
MAX_MEGAPIXELS = 8.0

log = structlog.get_logger()

router = APIRouter(prefix="/api/v1/images", tags=["images"])


def _get_storage() -> LocalDiskBackend:
    base = os.getenv("STORAGE_BASE_PATH", "/app/volumes/uploads")
    return LocalDiskBackend(base)


def _detect_mime(header: bytes) -> str | None:
    if header[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if header[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if header[:4] == b"RIFF" and header[8:12] == b"WEBP":
        return "image/webp"
    return None


@router.post("/upload", response_model=FileUploadResponse, status_code=201)
async def upload_image(
    file: UploadFile,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    data = await file.read()

    if len(data) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail={"error": "file_too_large", "message": "File exceeds 10 MB limit"},
        )

    mime = _detect_mime(data[:16])
    if mime is None:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail={
                "error": "unsupported_type",
                "message": "File must be JPEG, PNG, or WebP (validated by content)",
            },
        )

    # Open lazily — PIL reads only the header to determine dimensions, no pixel decode yet
    try:
        img = Image.open(io.BytesIO(data))
        width, height = img.size
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": "invalid_image", "message": "File could not be decoded as an image"},
        )

    if width > MAX_DIMENSION or height > MAX_DIMENSION:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": "image_too_large",
                "message": f"Image dimensions must not exceed {MAX_DIMENSION}px per side",
            },
        )

    megapixels = (width * height) / 1_000_000
    if megapixels > MAX_MEGAPIXELS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": "image_too_large",
                "message": "Image exceeds 8 megapixel limit",
            },
        )

    # Force full decode now that dimensions are confirmed safe — triggers bomb detection
    try:
        img.load()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": "invalid_image", "message": "File could not be decoded as an image"},
        )

    sha256 = hashlib.sha256(data).hexdigest()
    file_id = uuid.uuid4()
    ext = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}[mime]
    storage_key = f"{file_id}{ext}"

    storage = _get_storage()
    # Storage write happens before the DB commit intentionally: writing DB first then
    # crashing before the file is saved would leave a record pointing to a missing file.
    # Writing to disk first means the only failure mode is an orphan disk file with no
    # DB row.  Cleanup on commit failure below is best effort — in rare crash scenarios
    # (process killed between storage.save and the except block) the file may remain on
    # disk without a matching DB record.  The scheduled cleanup_orphan_files task finds
    # and removes those orphan files.
    await storage.save(data, storage_key)

    record = UploadedFile(
        id=file_id,
        user_id=current_user.id,
        storage_key=storage_key,
        original_sha256=sha256,
        mime_type=mime,
        file_size_bytes=len(data),
        width_px=width,
        height_px=height,
        megapixels=round(megapixels, 2),
    )
    db.add(record)
    try:
        await db.commit()
    except Exception:
        # DB commit failed — best-effort removal of the file we just wrote
        await storage.delete(storage_key)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "internal_error", "message": "An internal error occurred"},
        )
    await db.refresh(record)

    log.info("file_uploaded", user_id=str(current_user.id), file_id=str(file_id), mime=mime)
    return record


@router.delete("/{file_id}", status_code=204)
async def delete_image(
    file_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(UploadedFile).where(UploadedFile.id == file_id)
    )
    record = result.scalar_one_or_none()

    # Return 404 whether the file does not exist or belongs to a different user —
    # avoids revealing whether a given UUID corresponds to a real file
    if record is None or record.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "not_found", "message": "File not found"},
        )

    storage = _get_storage()
    storage_key = record.storage_key

    # DB row is deleted and committed before disk removal intentionally: this ensures
    # the file is no longer reachable via the API before the disk file is removed.  If
    # storage deletion fails after the DB commit the error is logged and the request
    # still succeeds — the orphan file poses no security risk because the DB record is
    # gone and the file cannot be retrieved through the API.  The scheduled
    # cleanup_orphan_files task is responsible for removing any such orphan disk files.
    await db.delete(record)
    await db.commit()

    try:
        await storage.delete(storage_key)
    except Exception:
        log.warning("storage_delete_failed_after_db_commit", file_id=str(file_id))

    log.info("file_deleted", user_id=str(current_user.id), file_id=str(file_id))


@router.get("/{file_id}")
async def get_image(
    file_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(UploadedFile).where(UploadedFile.id == file_id)
    )
    record = result.scalar_one_or_none()

    # Return 404 whether the file does not exist or belongs to a different user —
    # avoids revealing whether a given UUID corresponds to a real file
    if record is None or record.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "not_found", "message": "File not found"},
        )

    storage = _get_storage()
    try:
        data = await storage.load(record.storage_key)
    except FileNotFoundError:
        log.error("file_missing_in_storage", file_id=str(file_id), user_id=str(current_user.id))
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "not_found", "message": "File not found"},
        )

    return StreamingResponse(
        io.BytesIO(data),
        media_type=record.mime_type,
        headers={
            "Content-Length": str(record.file_size_bytes),
            "Cache-Control": "private, no-store",
        },
    )
