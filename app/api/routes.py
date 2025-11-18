"""
API 엔드포인트 정의
"""
from fastapi import APIRouter, Depends, HTTPException
import structlog

from app.api.schemas import InspectionRequest, InspectionResponse, StatusResponse
from app.tasks.inspection import inspect_code_task
from app.core.security import verify_api_key
from app.core.celery_app import celery_app

logger = structlog.get_logger()
router = APIRouter()


@router.post("/inspect", response_model=InspectionResponse)
async def create_inspection(
    request: InspectionRequest,
    api_key: str = Depends(verify_api_key),
):
    """
    코드 검사 요청 생성

    Args:
        request: 검사 요청 데이터
        api_key: API 인증 키

    Returns:
        task_id와 상태를 포함한 응답

    Raises:
        HTTPException: 요청이 유효하지 않은 경우
    """
    try:
        # Celery 작업 생성
        task = inspect_code_task.apply_async(
            kwargs={
                "github_url": str(request.github_url),
                "branch": request.branch,
                "callback_url": str(request.callback_url),
                "rules_files": request.rules_files,
                "ai_provider": request.ai_provider,
                "metadata": request.metadata,
            }
        )

        logger.info(
            "inspection_task_created",
            task_id=task.id,
            github_url=str(request.github_url),
            branch=request.branch,
            ai_provider=request.ai_provider,
        )

        return InspectionResponse(
            task_id=task.id,
            status="queued",
            message="Inspection task has been queued successfully",
        )

    except Exception as e:
        logger.exception("failed_to_create_task", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to create inspection task",
        )


@router.get("/status/{task_id}", response_model=StatusResponse)
async def get_task_status(
    task_id: str,
    api_key: str = Depends(verify_api_key),
):
    """
    작업 상태 조회

    Args:
        task_id: Celery 작업 ID
        api_key: API 인증 키

    Returns:
        작업 상태 정보
    """
    try:
        task = celery_app.AsyncResult(task_id)

        response = StatusResponse(
            task_id=task_id,
            status=task.status.lower(),
        )

        if task.ready():
            if task.successful():
                response.result = task.result
            else:
                response.error = str(task.info)

        return response

    except Exception as e:
        logger.exception("failed_to_get_status", task_id=task_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve task status",
        )
