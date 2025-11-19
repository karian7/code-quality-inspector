"""
Celery 애플리케이션 설정
"""
from celery import Celery
from app.config import settings

# Celery 애플리케이션 생성
celery_app = Celery(
    "code_quality_inspector",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

# Celery 설정
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=settings.celery_task_timeout,
    task_soft_time_limit=settings.celery_task_timeout - 60,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=50,
    result_expires=3600,  # 1시간
)

# 작업 자동 발견
celery_app.autodiscover_tasks(["app.tasks"])