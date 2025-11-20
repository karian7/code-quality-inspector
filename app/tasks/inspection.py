"""
Celery 작업 정의
"""
from typing import Dict, Any, Optional, List
from pathlib import Path
import structlog

from app.core.celery_app import celery_app
from app.services.git_service import GitService
from app.services.rule_loader import RuleLoader
from app.services.inspector import InspectorFactory
from app.tasks.callbacks import CallbackService
from app.core.exceptions import (
    GitCloneException,
    AICliException,
    APIKeyMissingException,
    RuleLoadException,
    CallbackException,
)

logger = structlog.get_logger()


@celery_app.task(
    bind=True,
    name="app.tasks.inspection.inspect_code_task",
    max_retries=3,
    default_retry_delay=60,
)
def inspect_code_task(
    self,
    github_url: str,
    branch: str,
    callback_url: Optional[str],
    rules_files: List[str],
    ai_provider: str = "codex",
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    코드 검사 Celery 작업

    Args:
        github_url: GitHub 저장소 URL
        branch: 브랜치 이름
        callback_url: 결과 콜백 URL (None이면 로그만 기록)
        rules_files: 심사 규칙 파일 목록
        ai_provider: AI 제공자 ("claude" 또는 "codex")
        metadata: 추가 메타데이터

    Returns:
        검사 결과 딕셔너리
    """
    task_id = self.request.id
    code_dir: Optional[Path] = None

    logger.info(
        "inspection_task_started",
        task_id=task_id,
        github_url=github_url,
        branch=branch,
        ai_provider=ai_provider,
    )

    # 서비스 초기화
    git_service = GitService()
    rule_loader = RuleLoader()
    inspector = InspectorFactory.create_inspector(ai_provider)
    callback_service = CallbackService()

    try:
        # 1. Git Clone
        logger.info("step_1_git_clone", task_id=task_id)
        code_dir = git_service.clone_repository(github_url, branch)

        # 저장소 정보 가져오기
        repo_info = git_service.get_repository_info(code_dir)
        logger.info("repository_info", task_id=task_id, **repo_info)

        # 2. 규칙 로드
        logger.info("step_2_load_rules", task_id=task_id, rules_files=rules_files)
        rules = rule_loader.load_rules(rules_files)

        # 3. 코드 검사
        logger.info("step_3_inspect_code", task_id=task_id)
        inspection_result = inspector.inspect_code(code_dir, rules, metadata)

        # 저장소 정보 추가
        inspection_result["repository_info"] = repo_info

        logger.info(
            "inspection_completed",
            task_id=task_id,
            score=inspection_result.get("score"),
            issues_count=len(inspection_result.get("issues", [])),
        )

        # 4. 콜백 전송 (성공)
        logger.info("step_4_send_callback", task_id=task_id, status="success")
        callback_service.send_callback_sync(
            callback_url=callback_url,
            task_id=task_id,
            status="success",
            github_url=github_url,
            branch=branch,
            ai_provider=ai_provider,
            result=inspection_result,
            metadata=metadata,
        )

        return inspection_result

    except GitCloneException as e:
        logger.error("git_clone_failed", task_id=task_id, error=str(e))

        # Git clone 실패는 일시적 네트워크 오류일 수 있으므로 재시도
        try:
            # 재시도 전 콜백 전송은 하지 않음 (재시도 중이므로)
            logger.info("retrying_git_clone", task_id=task_id, retry_count=self.request.retries)
            raise self.retry(exc=e, countdown=60, max_retries=3)
        except self.MaxRetriesExceededError:
            # 최대 재시도 횟수 초과 시 콜백 전송
            logger.error("max_retries_exceeded_git_clone", task_id=task_id)
            try:
                callback_service.send_callback_sync(
                    callback_url=callback_url,
                    task_id=task_id,
                    status="failed",
                    github_url=github_url,
                    branch=branch,
                    ai_provider=ai_provider,
                    error=str(e),
                    error_type="git_clone_error",
                    metadata=metadata,
                )
            except Exception as callback_error:
                logger.exception("callback_failed_after_git_error", error=str(callback_error))
            raise

    except RuleLoadException as e:
        logger.error("rule_load_failed", task_id=task_id, error=str(e))
        # 규칙 파일 로드 실패는 설정 문제이므로 재시도하지 않음
        # 콜백 전송 (실패)
        try:
            callback_service.send_callback_sync(
                callback_url=callback_url,
                task_id=task_id,
                status="failed",
                github_url=github_url,
                branch=branch,
                ai_provider=ai_provider,
                error=str(e),
                error_type="rule_load_error",
                metadata=metadata,
            )
        except Exception as callback_error:
            logger.exception("callback_failed_after_rule_error", error=str(callback_error))

        # 재시도하지 않고 종료
        return {"error": str(e), "error_type": "rule_load_error", "retryable": False}

    except APIKeyMissingException as e:
        logger.error("api_key_missing", task_id=task_id, ai_provider=ai_provider, error=str(e))
        # 콜백 전송 (실패)
        try:
            callback_service.send_callback_sync(
                callback_url=callback_url,
                task_id=task_id,
                status="failed",
                github_url=github_url,
                branch=branch,
                ai_provider=ai_provider,
                error=str(e),
                error_type="api_key_missing",
                metadata=metadata,
            )
        except Exception as callback_error:
            logger.exception("callback_failed_after_api_key_error", error=str(callback_error))

        # API 키 누락은 재시도해도 실패하므로 재시도하지 않음
        return {"error": str(e), "error_type": "api_key_missing", "retryable": False}

    except AICliException as e:
        logger.error("ai_cli_failed", task_id=task_id, ai_provider=ai_provider, error=str(e))

        # AI CLI 실패는 일시적 오류일 수 있으므로 재시도
        try:
            # 재시도 전 콜백 전송은 하지 않음 (재시도 중이므로)
            logger.info("retrying_ai_cli", task_id=task_id, retry_count=self.request.retries)
            raise self.retry(exc=e, countdown=60, max_retries=3)
        except self.MaxRetriesExceededError:
            # 최대 재시도 횟수 초과 시 콜백 전송
            logger.error("max_retries_exceeded_ai_cli", task_id=task_id)
            try:
                callback_service.send_callback_sync(
                    callback_url=callback_url,
                    task_id=task_id,
                    status="failed",
                    github_url=github_url,
                    branch=branch,
                    ai_provider=ai_provider,
                    error=str(e),
                    error_type="inspection_error",
                    metadata=metadata,
                )
            except Exception as callback_error:
                logger.exception("callback_failed_after_ai_cli_error", error=str(callback_error))
            raise

    except Exception as e:
        logger.exception("inspection_task_failed", task_id=task_id, error=str(e))

        # 예상치 못한 오류 - 일시적 문제일 수 있으므로 재시도
        try:
            # 재시도 전 콜백 전송은 하지 않음 (재시도 중이므로)
            logger.info("retrying_unexpected_error", task_id=task_id, retry_count=self.request.retries)
            raise self.retry(exc=e, countdown=60, max_retries=3)
        except self.MaxRetriesExceededError:
            # 최대 재시도 횟수 초과 시 콜백 전송
            logger.error("max_retries_exceeded_unexpected", task_id=task_id)
            try:
                callback_service.send_callback_sync(
                    callback_url=callback_url,
                    task_id=task_id,
                    status="failed",
                    github_url=github_url,
                    branch=branch,
                    ai_provider=ai_provider,
                    error=str(e),
                    error_type="unexpected_error",
                    metadata=metadata,
                )
            except Exception as callback_error:
                logger.exception("callback_failed_after_unexpected_error", error=str(callback_error))
            raise

    finally:
        # 정리: 임시 디렉토리 삭제
        if code_dir:
            logger.info("cleanup_started", task_id=task_id, path=str(code_dir))
            git_service.cleanup_directory(code_dir)
            logger.info("cleanup_completed", task_id=task_id)