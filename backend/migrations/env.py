import asyncio
import os
import sys
from logging.config import fileConfig

from sqlalchemy.ext.asyncio import create_async_engine

from alembic import context

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db import Base  # noqa: E402 — import models so metadata is populated

# Import all models here so Alembic detects them for autogenerate
from app.models.user import User  # noqa: F401
from app.models.email_token import EmailToken  # noqa: F401
from app.models.user_quota import UserQuota  # noqa: F401
from app.models.uploaded_file import UploadedFile  # noqa: F401
from app.models.project import Project  # noqa: F401
from app.models.job import Job  # noqa: F401
from app.models.audit_log import AuditLog  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url() -> str:
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL environment variable is not set")
    return url


def run_migrations_offline() -> None:
    context.configure(
        url=get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = create_async_engine(get_url())
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
