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
            github_url: GitHub 저장소 URL
            branch: 클론할 브랜치
            target_dir: 대상 디렉토리 (None인 경우 자동 생성)

        Returns:
            클론된 저장소의 경로

        Raises:
            GitCloneException: 클론 실패 시
        """
        if target_dir is None:
            # 임시 디렉토리 생성
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
            logger.error(
                "git_clone_failed",
                url=github_url,
                branch=branch,
                error=str(e),
            )
            # 실패 시 디렉토리 정리
            self.cleanup_directory(target_dir)
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
