"""
Git 작업 서비스
"""
import git
import shutil
from pathlib import Path
from typing import Optional
import structlog

from app.config import settings
from app.core.exceptions import GitCloneException
from app.core.validators import URLValidator

logger = structlog.get_logger()


class GitService:
    """Git 작업을 처리하는 서비스"""

    def __init__(self):
        self.timeout = settings.git_clone_timeout
        self.depth = settings.git_clone_depth

    def clone_repository(
        self, github_url: str, branch: str = "main", target_dir: Optional[Path] = None
    ) -> Path:
        """
        GitHub 저장소를 클론

        Args:
            github_url: GitHub 저장소 URL (HTTPS, 퍼블릭 레포만 허용)
            branch: 클론할 브랜치
            target_dir: 대상 디렉토리 (None인 경우 자동 생성)

        Returns:
            클론된 저장소의 경로

        Raises:
            GitCloneException: 클론 실패 시 (URL 검증 실패, 인증 실패, 네트워크 오류 등)
        """
        # 1. URL 검증 (보안: HTTPS GitHub 퍼블릭 레포만 허용)
        is_valid, error_msg = URLValidator.validate_github_url(github_url)
        if not is_valid:
            logger.error(
                "invalid_github_url",
                url=github_url,
                reason=error_msg,
            )
            raise GitCloneException(
                f"Invalid GitHub URL: {error_msg}",
                details={
                    "url": github_url,
                    "reason": error_msg,
                    "hint": "Only public GitHub repositories with HTTPS URLs are allowed",
                },
            )

        # 2. 브랜치 이름 검증 (보안: Command Injection 방지)
        is_valid, error_msg = URLValidator.validate_branch_name(branch)
        if not is_valid:
            logger.error(
                "invalid_branch_name",
                branch=branch,
                reason=error_msg,
            )
            raise GitCloneException(
                f"Invalid branch name: {error_msg}",
                details={"branch": branch, "reason": error_msg},
            )

        # 3. URL 정규화
        github_url = URLValidator.sanitize_github_url(github_url)

        if target_dir is None:
            # 임시 디렉토리 생성 (UUID로 동시 요청 충돌 방지)
            import uuid
            target_dir = settings.work_dir / str(uuid.uuid4())

        target_dir.mkdir(parents=True, exist_ok=True)

        try:
            logger.info(
                "git_clone_started",
                url=github_url,
                branch=branch,
                target_dir=str(target_dir),
            )

            # Git clone 실행
            repo = git.Repo.clone_from(
                url=github_url,
                to_path=str(target_dir),
                branch=branch,
                depth=self.depth,
                single_branch=True,
            )

            logger.info(
                "git_clone_completed",
                url=github_url,
                branch=branch,
                commit=repo.head.commit.hexsha[:8],
            )

            return target_dir

        except git.GitCommandError as e:
            error_str = str(e).lower()
            logger.error(
                "git_clone_failed",
                url=github_url,
                branch=branch,
                error=str(e),
            )
            # 실패 시 디렉토리 정리
            self.cleanup_directory(target_dir)

            # 에러 타입별 명확한 메시지 제공
            if "authentication" in error_str or "permission denied" in error_str:
                raise GitCloneException(
                    f"Access denied: This repository is private or does not exist. "
                    f"Only public GitHub repositories are supported.",
                    details={
                        "url": github_url,
                        "branch": branch,
                        "error_type": "authentication_required",
                        "hint": "Ensure the repository is public and the URL is correct",
                    },
                )
            elif "not found" in error_str or "repository not found" in error_str:
                raise GitCloneException(
                    f"Repository not found: {github_url}. "
                    f"Please check if the repository exists and is public.",
                    details={
                        "url": github_url,
                        "branch": branch,
                        "error_type": "repository_not_found",
                    },
                )
            elif "branch" in error_str or f"'{branch}'" in error_str:
                raise GitCloneException(
                    f"Branch '{branch}' not found in repository {github_url}",
                    details={
                        "url": github_url,
                        "branch": branch,
                        "error_type": "branch_not_found",
                        "hint": "Check if the branch name is correct (e.g., main, master, develop)",
                    },
                )
            else:
                raise GitCloneException(
                    f"Failed to clone repository: {github_url}",
                    details={"url": github_url, "branch": branch, "error": str(e)},
                )

        except Exception as e:
            logger.exception("git_clone_unexpected_error", url=github_url, error=str(e))
            self.cleanup_directory(target_dir)
            raise GitCloneException(
                f"Unexpected error during git clone: {str(e)}",
                details={"url": github_url, "branch": branch, "error": str(e)},
            )

    def cleanup_directory(self, directory: Path) -> None:
        """
        디렉토리 삭제

        Args:
            directory: 삭제할 디렉토리
        """
        try:
            if directory.exists():
                logger.info("cleaning_up_directory", path=str(directory))
                shutil.rmtree(directory, ignore_errors=True)
                logger.info("directory_cleaned", path=str(directory))
        except Exception as e:
            logger.warning("cleanup_failed", path=str(directory), error=str(e))

    def cleanup_old_directories(self, max_age_hours: int = 24) -> None:
        """
        오래된 임시 디렉토리 정리

        Worker가 비정상 종료되어 남은 디렉토리를 정리합니다.

        Args:
            max_age_hours: 최대 보존 시간 (시간 단위, 기본 24시간)
        """
        import time

        work_dir = settings.work_dir
        if not work_dir.exists():
            logger.info("work_directory_not_found", path=str(work_dir))
            return

        current_time = time.time()
        cleaned_count = 0

        try:
            for item in work_dir.iterdir():
                if item.is_dir():
                    # 생성 시간 확인
                    try:
                        age_seconds = current_time - item.stat().st_mtime
                        age_hours = age_seconds / 3600

                        if age_hours > max_age_hours:
                            logger.info(
                                "cleaning_old_directory",
                                path=str(item),
                                age_hours=round(age_hours, 2),
                            )
                            self.cleanup_directory(item)
                            cleaned_count += 1
                    except Exception as e:
                        logger.warning(
                            "failed_to_check_directory_age",
                            path=str(item),
                            error=str(e),
                        )

            if cleaned_count > 0:
                logger.info(
                    "old_directories_cleaned",
                    count=cleaned_count,
                    max_age_hours=max_age_hours,
                )
            else:
                logger.info("no_old_directories_to_clean", max_age_hours=max_age_hours)

        except Exception as e:
            logger.exception("cleanup_old_directories_failed", error=str(e))

    def get_repository_info(self, repo_path: Path) -> dict:
        """
        저장소 정보 조회

        Args:
            repo_path: 저장소 경로

        Returns:
            저장소 정보 딕셔너리
        """
        try:
            repo = git.Repo(repo_path)
            commit = repo.head.commit

            return {
                "commit_sha": commit.hexsha,
                "commit_message": commit.message.strip(),
                "author": str(commit.author),
                "committed_date": commit.committed_datetime.isoformat(),
                "branch": repo.active_branch.name if repo.active_branch else None,
            }
        except Exception as e:
            logger.warning("failed_to_get_repo_info", path=str(repo_path), error=str(e))
            return {}
