"""
결과 전송 로직
"""
import httpx
from typing import Dict, Any, Optional
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings
from app.api.schemas import CallbackPayload
from app.core.exceptions import CallbackException

logger = structlog.get_logger()


class CallbackService:
    """콜백 전송 서비스"""

    def __init__(self):
        self.timeout = settings.callback_timeout
        self.max_retries = settings.callback_max_retries

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def send_callback(
        self,
        callback_url: str,
        task_id: str,
        status: str,
        github_url: str,
        branch: str,
        ai_provider: str,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        error_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        콜백 URL로 결과 전송

        Args:
            callback_url: 콜백 URL
            task_id: 작업 ID
            status: 작업 상태 (success/failed)
            github_url: GitHub 저장소 URL
            branch: 브랜치 이름
            ai_provider: 사용된 AI 제공자
            result: 검사 결과
            error: 에러 메시지
            error_type: 에러 타입
            metadata: 추가 메타데이터

        Raises:
            CallbackException: 콜백 전송 실패 시
        """
        payload = CallbackPayload(
            task_id=task_id,
            status=status,
            github_url=github_url,
            branch=branch,
            ai_provider=ai_provider,
            result=result,
            error=error,
            error_type=error_type,
            metadata=metadata,
        )

        try:
            logger.info(
                "sending_callback",
                url=callback_url,
                task_id=task_id,
                status=status,
            )

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    callback_url,
                    json=payload.model_dump(mode='json'),  # mode='json'으로 datetime 자동 직렬화
                    headers={"Content-Type": "application/json"},
                )

                response.raise_for_status()

                logger.info(
                    "callback_sent_successfully",
                    url=callback_url,
                    task_id=task_id,
                    status_code=response.status_code,
                )

        except httpx.HTTPStatusError as e:
            logger.error(
                "callback_http_error",
                url=callback_url,
                status_code=e.response.status_code,
                error=str(e),
            )
            raise CallbackException(
                f"Callback failed with HTTP {e.response.status_code}",
                details={
                    "url": callback_url,
                    "status_code": e.response.status_code,
                    "response": e.response.text[:500],
                },
            )

        except httpx.TimeoutException:
            logger.error("callback_timeout", url=callback_url, timeout=self.timeout)
            raise CallbackException(
                f"Callback timed out after {self.timeout} seconds",
                details={"url": callback_url, "timeout": self.timeout},
            )

        except Exception as e:
            logger.exception("callback_unexpected_error", url=callback_url, error=str(e))
            raise CallbackException(
                f"Unexpected error during callback: {str(e)}",
                details={"url": callback_url, "error": str(e)},
            )

    def send_callback_sync(self, *args, **kwargs) -> None:
        """
        동기 방식 콜백 전송 (Celery 작업에서 사용)

        Args:
            *args, **kwargs: send_callback과 동일한 인자

        Note:
            Celery worker는 동기 컨텍스트에서 실행되므로
            새 이벤트 루프를 생성하여 비동기 함수를 실행합니다.
        """
        import asyncio

        # 새 이벤트 루프 생성 및 실행
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self.send_callback(*args, **kwargs))
        except Exception as e:
            logger.exception("sync_callback_execution_failed", error=str(e))
            raise
        finally:
            loop.close()
