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
from app.models.job import Job
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

_PROJECT_LIMIT = 50


def _get_upload_storage() -> LocalDiskBackend:
    base = os.getenv("STORAGE_BASE_PATH", "/app/volumes/uploads")
    return LocalDiskBackend(base)


def _get_output_storage() -> LocalDiskBackend:
    base = os.getenv("OUTPUT_BASE_PATH", "/app/volumes/outputs")
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
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.user_id == current_user.id)
    )
    project = result.scalar_one_or_none()
    if project is None:
        raise _not_found()

    return ProjectResponse.model_validate(project)


@router.post("", response_model=ProjectResponse, status_code=201)
async def create_project(
    body: ProjectCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Lock the user row for the duration of this transaction so that concurrent
    # project-creation requests for the same user are serialized. This is the same
    # strategy used for quota enforcement in the jobs router: one winner holds the
    # lock; others wait and then see the updated count when they acquire it.
    await db.execute(
        select(User).where(User.id == current_user.id).with_for_update()
    )
    count_result = await db.execute(
        select(func.count()).select_from(Project).where(Project.user_id == current_user.id)
    )
    if count_result.scalar_one() >= _PROJECT_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "project_limit_reached",
                "message": f"Project limit of {_PROJECT_LIMIT} reached. Delete an existing project to create a new one.",
            },
        )

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
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.user_id == current_user.id)
    )
    project = result.scalar_one_or_none()
    if project is None:
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
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.user_id == current_user.id)
    )
    project = result.scalar_one_or_none()
    if project is None:
        raise _not_found()

    # Issue 3: block deletion while any job is still actively running
    active_jobs_result = await db.execute(
        select(func.count())
        .select_from(Job)
        .where(
            Job.project_id == project_id,
            Job.status.in_(["queued", "processing"]),
        )
    )
    if active_jobs_result.scalar_one() > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "render_in_progress",
                "message": "A render is still in progress. Wait for it to finish before deleting this project.",
            },
        )

    # Issue 1: collect output keys from all jobs before the cascade removes them
    output_keys_result = await db.execute(
        select(Job.id, Job.output_key).where(
            Job.project_id == project_id,
            Job.output_key.is_not(None),
        )
    )
    output_job_pairs = [(str(row[0]), row[1]) for row in output_keys_result.all()]

    # Issue 2 + original: decide whether source file is safe to delete.
    # The FK is SET NULL so the project delete will not cascade to uploaded_files.
    # Only delete the source file if no other project owned by this user references it.
    source_file_record: UploadedFile | None = None
    delete_source_file = False
    if project.source_file_id is not None:
        file_result = await db.execute(
            select(UploadedFile).where(UploadedFile.id == project.source_file_id)
        )
        source_file_record = file_result.scalar_one_or_none()

        if source_file_record is not None:
            other_ref_result = await db.execute(
                select(func.count())
                .select_from(Project)
                .where(
                    Project.source_file_id == project.source_file_id,
                    Project.user_id == current_user.id,
                    Project.id != project_id,
                )
            )
            delete_source_file = other_ref_result.scalar_one() == 0

    # Delete project — cascades to jobs via ON DELETE CASCADE in the DB
    await db.delete(project)

    # Explicitly delete the uploaded_file record only when no other project shares it
    if delete_source_file and source_file_record is not None:
        await db.delete(source_file_record)

    await db.commit()

    # Remove source file from disk only when it was safe to delete and the DB commit succeeded
    if delete_source_file and source_file_record is not None:
        upload_storage = _get_upload_storage()
        try:
            await upload_storage.delete(source_file_record.storage_key)
        except Exception:
            # Issue 4: never log the storage key — log only the project_id
            log.warning(
                "source_file_disk_delete_failed",
                project_id=str(project_id),
            )

    # Issue 1: remove output files for every completed job under this project
    if output_job_pairs:
        output_storage = _get_output_storage()
        for job_id_str, output_key in output_job_pairs:
            try:
                await output_storage.delete(output_key)
            except Exception:
                # Issue 4: never log the output key — log only the job_id
                log.warning(
                    "output_file_disk_delete_failed",
                    job_id=job_id_str,
                    project_id=str(project_id),
                )

    log.info("project_deleted", project_id=str(project_id), user_id=str(current_user.id))
