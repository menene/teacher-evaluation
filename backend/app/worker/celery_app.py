from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "teacher_analysis",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.worker.tasks"],
)

celery_app.conf.update(
    task_track_started=True,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="America/Guatemala",
    enable_utc=True,
)
