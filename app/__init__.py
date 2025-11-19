"""
Code Quality Inspector Application

Celery 태스크 등록을 위한 패키지 초기화
"""

# Celery가 태스크를 찾을 수 있도록 명시적으로 import
# 주의: celery_app이 먼저 초기화된 후에 import되어야 함
from app.core.celery_app import celery_app  # noqa: F401

# 모든 Celery 태스크를 여기서 import하여 등록 보장
__all__ = ["celery_app"]
