import math
import os
import uuid
from datetime import datetime, timezone
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.middleware.auth import get_current_user
from app.models.project import Project
from app.models.uploaded_file import UploadedFile
from app.models.user import User
from app.schemas.projects import (
    ProjectCreateRequest,
    ProjectListResponse,
    ProjectResponse,
    ProjectUpdateRequest,
)
from app.services.storage import LocalDiskBackend

log = structlog.get_logger()

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])


def _get_storage() -> LocalDiskBackend:
    base = os.getenv("STORAGE_BASE_PATH", "/app/volumes/uploads")
    return LocalDiskBackend(base)


def _not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"error": "not_found", "message": "Project not found"},
    )


@router.get("", response_model=ProjectListResponse)
async def list_projects(
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    offset = (page - 1) * limit

    count_result = await db.execute(
        select(func.count()).select_from(Project).where(Project.user_id == current_user.id)
    )
    total = count_result.scalar_one()

    rows_result = await db.execute(
        select(Project)
        .where(Project.user_id == current_user.id)
        .order_by(Project.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    projects = rows_result.scalars().all()

    return ProjectListResponse(
        items=[ProjectResponse.model_validate(p) for p in projects],
        total=total,
        page=page,
        limit=limit,
        pages=math.ceil(total / limit) if total > 0 else 1,
    )


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()

    if project is None or project.user_id != current_user.id:
        raise _not_found()

    return ProjectResponse.model_validate(project)


@router.post("", response_model=ProjectResponse, status_code=201)
async def create_project(
    body: ProjectCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if body.source_file_id is not None:
        file_result = await db.execute(
            select(UploadedFile).where(UploadedFile.id == body.source_file_id)
        )
        source_file = file_result.scalar_one_or_none()
        if source_file is None or source_file.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": "not_found", "message": "Source file not found"},
            )

    project = Project(
        user_id=current_user.id,
        name=body.name,
        source_file_id=body.source_file_id,
        parameters=body.parameters or {},
        status="draft",
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)

    log.info("project_created", project_id=str(project.id), user_id=str(current_user.id))
    return ProjectResponse.model_validate(project)


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: uuid.UUID,
    body: ProjectUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()

    if project is None or project.user_id != current_user.id:
        raise _not_found()

    changed = False
    if body.name is not None:
        project.name = body.name
        changed = True
    if body.parameters is not None:
        project.parameters = body.parameters
        changed = True

    if changed:
        project.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(project)

    log.info("project_updated", project_id=str(project_id), user_id=str(current_user.id))
    return ProjectResponse.model_validate(project)


@router.delete("/{project_id}", status_code=204)
async def delete_project(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()

    if project is None or project.user_id != current_user.id:
        raise _not_found()

    # Capture source file details before deletion — the FK is SET NULL so
    # deleting the project does not cascade to uploaded_files.
    source_file_storage_key: str | None = None
    source_file_record: UploadedFile | None = None
    if project.source_file_id is not None:
        file_result = await db.execute(
            select(UploadedFile).where(UploadedFile.id == project.source_file_id)
        )
        source_file_record = file_result.scalar_one_or_none()
        if source_file_record is not None:
            source_file_storage_key = source_file_record.storage_key

    # Delete project (cascades jobs via ON DELETE CASCADE in the DB)
    await db.delete(project)

    # Explicitly delete the uploaded_file record — FK is SET NULL so it won't cascade
    if source_file_record is not None:
        await db.delete(source_file_record)

    await db.commit()

    # Remove the file from disk only after the DB commit succeeds
    if source_file_storage_key is not None:
        storage = _get_storage()
        try:
            await storage.delete(source_file_storage_key)
        except Exception:
            log.warning(
                "storage_delete_failed_after_db_commit",
                project_id=str(project_id),
                storage_key=source_file_storage_key,
            )

    log.info("project_deleted", project_id=str(project_id), user_id=str(current_user.id))
