"""
커스텀 예외 클래스
"""
from typing import Optional, Dict, Any


class InspectorException(Exception):
    """기본 Inspector 예외"""

    def __init__(
        self,
        message: str,
        error_code: str = "INSPECTOR_ERROR",
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class GitCloneException(InspectorException):
    """Git clone 실패 예외"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="GIT_CLONE_FAILED",
            status_code=500,
            details=details,
        )


class ClaudeCliException(InspectorException):
    """Claude CLI 실행 실패 예외"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="CLAUDE_CLI_FAILED",
            status_code=500,
            details=details,
        )


class RuleLoadException(InspectorException):
    """규칙 파일 로드 실패 예외"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="RULE_LOAD_FAILED",
            status_code=500,
            details=details,
        )


class CallbackException(InspectorException):
    """콜백 전송 실패 예외"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="CALLBACK_FAILED",
            status_code=500,
            details=details,
        )


class ValidationException(InspectorException):
    """입력 검증 실패 예외"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="VALIDATION_FAILED",
            status_code=400,
            details=details,
        )


class AuthenticationException(InspectorException):
    """인증 실패 예외"""

    def __init__(self, message: str = "Authentication failed"):
        super().__init__(
            message=message,
            error_code="AUTHENTICATION_FAILED",
            status_code=401,
        )
