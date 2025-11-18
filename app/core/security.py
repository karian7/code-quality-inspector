"""
API 인증 및 보안
"""
from fastapi import Header, HTTPException
from typing import Optional
import structlog

from app.config import settings
from app.core.exceptions import AuthenticationException

logger = structlog.get_logger()


async def verify_api_key(
    x_api_key: Optional[str] = Header(None, alias=settings.api_key_header)
) -> str:
    """
    API 키 검증

    Args:
        x_api_key: 요청 헤더의 API 키

    Returns:
        검증된 API 키

    Raises:
        AuthenticationException: API 키가 유효하지 않은 경우
    """
    # API 키 목록 가져오기
    api_keys = settings.get_api_keys_list()

    # API 키가 설정되지 않은 경우 인증 스킵 (개발 환경)
    if not api_keys:
        logger.warning("api_keys_not_configured", message="API authentication is disabled")
        return "dev-mode"

    # API 키 확인
    if not x_api_key:
        logger.warning("api_key_missing")
        raise AuthenticationException("API key is required")

    if x_api_key not in api_keys:
        logger.warning("invalid_api_key", key_prefix=x_api_key[:8] if len(x_api_key) > 8 else "***")
        raise AuthenticationException("Invalid API key")

    logger.debug("api_key_verified")
    return x_api_key
