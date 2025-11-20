"""
Callback 서비스 테스트
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from app.tasks.callbacks import CallbackService


class TestCallbackService:
    """CallbackService 테스트"""

    @pytest.mark.asyncio
    async def test_callback_skipped_when_url_is_none(self):
        """callback_url이 None일 때 전송을 건너뛰는지 테스트"""
        callback_service = CallbackService()

        # callback_url=None으로 호출
        await callback_service.send_callback(
            callback_url=None,
            task_id="test-task-123",
            status="success",
            github_url="https://github.com/user/repo",
            branch="main",
            ai_provider="codex",
            result={"score": 85},
        )

        # 예외가 발생하지 않아야 함 (정상 종료)
        # 로그만 기록되고 실제 HTTP 요청은 발생하지 않음

    @pytest.mark.asyncio
    async def test_callback_skipped_when_url_is_empty_string(self):
        """callback_url이 빈 문자열일 때 전송을 건너뛰는지 테스트"""
        callback_service = CallbackService()

        # callback_url=""으로 호출
        await callback_service.send_callback(
            callback_url="",
            task_id="test-task-456",
            status="success",
            github_url="https://github.com/user/repo",
            branch="main",
            ai_provider="codex",
            result={"score": 85},
        )

        # 예외가 발생하지 않아야 함 (정상 종료)

    @pytest.mark.asyncio
    async def test_callback_sent_when_url_is_valid(self):
        """callback_url이 유효할 때 전송되는지 테스트"""
        callback_service = CallbackService()

        with patch("httpx.AsyncClient") as mock_client_class:
            # AsyncClient의 post 메서드 모킹
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.raise_for_status = Mock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            # 유효한 callback_url로 호출
            await callback_service.send_callback(
                callback_url="https://webhook.site/test",
                task_id="test-task-789",
                status="success",
                github_url="https://github.com/user/repo",
                branch="main",
                ai_provider="codex",
                result={"score": 85},
            )

            # HTTP POST 요청이 호출되었는지 확인
            assert mock_client.post.called
            call_args = mock_client.post.call_args
            assert call_args[0][0] == "https://webhook.site/test"

    def test_send_callback_sync_with_none_url(self):
        """동기 방식에서 callback_url=None 처리 테스트"""
        callback_service = CallbackService()

        # 예외가 발생하지 않아야 함
        callback_service.send_callback_sync(
            callback_url=None,
            task_id="sync-test-123",
            status="failed",
            github_url="https://github.com/user/repo",
            branch="main",
            ai_provider="claude",
            error="Test error",
        )


class TestCallbackPayloadSerialization:
    """CallbackPayload JSON 직렬화 테스트"""

    def test_datetime_serialization(self):
        """datetime 필드가 JSON으로 정상 직렬화되는지 테스트"""
        from app.api.schemas import CallbackPayload
        from datetime import datetime

        payload = CallbackPayload(
            task_id="test-123",
            status="success",
            github_url="https://github.com/user/repo",
            branch="main",
            ai_provider="codex",
            result={"score": 85},
            completed_at=datetime(2024, 1, 18, 10, 30, 0),
        )

        # model_dump(mode='json')으로 직렬화
        json_data = payload.model_dump(mode='json')

        # datetime이 ISO 8601 문자열로 변환되었는지 확인
        assert isinstance(json_data["completed_at"], str)
        assert "2024-01-18" in json_data["completed_at"]
