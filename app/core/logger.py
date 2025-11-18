"""
구조화된 로깅 설정
"""
import structlog
import logging
import sys
from pathlib import Path
from typing import Any
from app.config import settings


def setup_logging():
    """structlog 설정"""

    # 로그 레벨 설정
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    # 기본 로깅 설정
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )

    # structlog 설정
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.filter_by_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer() if not settings.debug else structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = None) -> Any:
    """로거 인스턴스 반환"""
    return structlog.get_logger(name)
