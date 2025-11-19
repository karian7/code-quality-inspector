"""
입력 검증 유틸리티
"""
import re
from urllib.parse import urlparse
from typing import Tuple
import structlog

logger = structlog.get_logger()


class URLValidator:
    """URL 검증 클래스"""

    # GitHub 공개 레포지토리 URL 패턴
    GITHUB_HTTPS_PATTERN = re.compile(
        r"^https://github\.com/[\w\-\.]+/[\w\-\.]+(?:\.git)?$"
    )

    # 허용되는 브랜치 이름 패턴 (보안: command injection 방지)
    BRANCH_NAME_PATTERN = re.compile(r"^[\w\-\./]+$")

    @classmethod
    def validate_github_url(cls, url: str) -> Tuple[bool, str]:
        """
        GitHub 퍼블릭 레포지토리 URL 검증

        Args:
            url: 검증할 URL

        Returns:
            (검증 성공 여부, 에러 메시지)

        보안 검증 항목:
        1. HTTPS 프로토콜만 허용
        2. github.com 도메인만 허용
        3. 정상적인 레포지토리 경로 패턴
        4. file://, git://, ssh:// 등 차단
        """
        if not url:
            return False, "URL is required"

        # URL 파싱
        try:
            parsed = urlparse(url)
        except Exception as e:
            logger.warning("url_parse_failed", url=url, error=str(e))
            return False, "Invalid URL format"

        # 1. HTTPS 프로토콜만 허용
        if parsed.scheme != "https":
            logger.warning(
                "invalid_protocol",
                url=url,
                scheme=parsed.scheme,
                reason="Only HTTPS is allowed for security",
            )
            return False, f"Only HTTPS protocol is allowed. Got: {parsed.scheme}://"

        # 2. GitHub 도메인만 허용
        if parsed.netloc.lower() not in ["github.com", "www.github.com"]:
            logger.warning(
                "invalid_domain",
                url=url,
                domain=parsed.netloc,
                reason="Only github.com is allowed",
            )
            return (
                False,
                f"Only GitHub repositories are allowed. Got domain: {parsed.netloc}",
            )

        # 3. 레포지토리 경로 패턴 검증
        if not cls.GITHUB_HTTPS_PATTERN.match(url):
            logger.warning(
                "invalid_repo_pattern",
                url=url,
                reason="URL does not match GitHub repository pattern",
            )
            return (
                False,
                "Invalid GitHub repository URL format. "
                "Expected: https://github.com/owner/repo or https://github.com/owner/repo.git",
            )

        # 4. 추가 보안 체크: 쿼리 파라미터나 프래그먼트 차단
        if parsed.query or parsed.fragment:
            logger.warning(
                "url_has_query_or_fragment",
                url=url,
                query=parsed.query,
                fragment=parsed.fragment,
            )
            return False, "URL must not contain query parameters or fragments"

        logger.info("github_url_validated", url=url)
        return True, ""

    @classmethod
    def validate_branch_name(cls, branch: str) -> Tuple[bool, str]:
        """
        브랜치 이름 검증 (Command Injection 방지)

        Args:
            branch: 브랜치 이름

        Returns:
            (검증 성공 여부, 에러 메시지)
        """
        if not branch:
            return False, "Branch name is required"

        # 길이 제한
        if len(branch) > 255:
            return False, "Branch name is too long (max 255 characters)"

        # 패턴 검증: 알파벳, 숫자, 하이픈, 언더스코어, 슬래시, 점만 허용
        if not cls.BRANCH_NAME_PATTERN.match(branch):
            logger.warning(
                "invalid_branch_name",
                branch=branch,
                reason="Branch name contains invalid characters",
            )
            return (
                False,
                "Branch name contains invalid characters. "
                "Allowed: letters, numbers, -, _, /, .",
            )

        # 위험한 패턴 차단
        dangerous_patterns = [
            "..",  # 디렉토리 탐색
            ";",  # 명령어 체이닝
            "|",  # 파이프
            "&",  # 백그라운드 실행
            "$",  # 변수 치환
            "`",  # 명령어 치환
            "\\",  # 이스케이프 (슬래시는 허용하지 않음)
        ]

        for pattern in dangerous_patterns:
            if pattern in branch:
                logger.warning(
                    "dangerous_branch_pattern",
                    branch=branch,
                    pattern=pattern,
                )
                return False, f"Branch name contains dangerous pattern: {pattern}"

        return True, ""

    @classmethod
    def sanitize_github_url(cls, url: str) -> str:
        """
        GitHub URL 정규화

        .git 확장자 제거 및 URL 정리

        Args:
            url: GitHub URL

        Returns:
            정규화된 URL
        """
        url = url.strip()
        if url.endswith(".git"):
            url = url[:-4]
        return url
