from celery import Celery
from celery.schedules import crontab
import os

_broker = os.getenv("CELERY_BROKER_URL")
_backend = os.getenv("REDIS_BROKER_URL")
if not _broker:
    raise RuntimeError("CELERY_BROKER_URL environment variable is not set")
if not _backend:
    raise RuntimeError("REDIS_BROKER_URL environment variable is not set")

celery_app = Celery(
    "stipple",
    broker=_broker,
    backend=_backend,
    include=["app.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    task_soft_time_limit=270,
    task_time_limit=300,
    worker_max_tasks_per_child=50,
    task_routes={
        "app.tasks.process_full_render": {"queue": "render"},
        "app.tasks.cleanup_orphan_files": {"queue": "maintenance"},
        "app.tasks.cleanup_expired_outputs": {"queue": "maintenance"},
    },
    beat_schedule={
        "cleanup-orphan-files": {
            "task": "app.tasks.cleanup_orphan_files",
            "schedule": crontab(hour=3, minute=0),
        },
        "cleanup-expired-outputs": {
            "task": "app.tasks.cleanup_expired_outputs",
            "schedule": crontab(hour=3, minute=30),
        },
    },
)
