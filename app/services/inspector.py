"""
AI CLI를 사용한 코드 검사 서비스 (SOLID 원칙 준수)
"""
import subprocess
import json
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, Optional
import structlog

from app.config import settings
from app.core.exceptions import AICliException, APIKeyMissingException

logger = structlog.get_logger()


class BaseInspector(ABC):
    """코드 검사기 기본 추상 클래스"""

    def __init__(self, timeout: int, model: str, max_tokens: int):
        """
        Args:
            timeout: CLI 실행 타임아웃 (초)
            model: 사용할 모델 이름
            max_tokens: 최대 토큰 수
        """
        self.timeout = timeout
        self.model = model
        self.max_tokens = max_tokens

    @abstractmethod
    def get_cli_path(self) -> str:
        """CLI 실행 파일 경로 반환"""
        pass

    @abstractmethod
    def get_api_key(self) -> Optional[str]:
        """API 키 반환"""
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """제공자 이름 반환"""
        pass

    @abstractmethod
    def build_cli_command(self, code_dir: Path, prompt: str) -> list[str]:
        """
        CLI 명령어 빌드

        Args:
            code_dir: 코드 디렉토리
            prompt: 프롬프트 문자열 (명령줄 인자로 전달됨)

        Returns:
            CLI 명령어 리스트
        """
        pass

    @abstractmethod
    def get_env_vars(self) -> dict:
        """환경 변수 반환"""
        pass

    def validate_api_key(self) -> None:
        """API 키 검증"""
        api_key = self.get_api_key()
        if not api_key:
            provider = self.get_provider_name()
            logger.error(
                "api_key_missing",
                provider=provider,
            )
            raise APIKeyMissingException(
                f"{provider} API key is not configured. Please set the appropriate environment variable.",
                details={"provider": provider},
            )

    def inspect_code(
        self, code_dir: Path, rules: str, metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        코드 디렉토리를 검사

        Args:
            code_dir: 검사할 코드 디렉토리
            rules: 심사 규칙 내용
            metadata: 추가 메타데이터

        Returns:
            검사 결과 딕셔너리

        Raises:
            APIKeyMissingException: API 키가 없는 경우
            AICliException: CLI 실행 실패 시
        """
        # API 키 검증
        self.validate_api_key()

        try:
            # 프롬프트 생성
            prompt = self._build_prompt(rules, metadata)

            logger.info(
                "ai_cli_inspection_started",
                provider=self.get_provider_name(),
                code_dir=str(code_dir),
                prompt_length=len(prompt),
            )

            # CLI 실행
            result = self._execute_cli(code_dir, prompt)

            logger.info(
                "ai_cli_inspection_completed",
                provider=self.get_provider_name(),
                code_dir=str(code_dir),
                result_length=len(str(result)),
            )

            return result

        except APIKeyMissingException:
            raise
        except AICliException:
            raise
        except Exception as e:
            logger.exception("inspection_unexpected_error", provider=self.get_provider_name(), error=str(e))
            raise AICliException(
                f"Unexpected error during code inspection: {str(e)}",
                details={"provider": self.get_provider_name(), "error": str(e)},
            )

    def _build_prompt(self, rules: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        CLI에 전달할 프롬프트 생성

        Args:
            rules: 심사 규칙
            metadata: 추가 메타데이터

        Returns:
            프롬프트 문자열
        """
        prompt = f"""You are a code quality inspector. Please analyze the code in this repository according to the following rules and provide a detailed inspection report.

# Inspection Rules

{rules}

# Instructions

1. Analyze all code files in the repository
2. Check compliance with the rules above
3. Identify any issues, bugs, or areas for improvement
4. Provide a quality score (0-100)
5. Return your findings in the following JSON format:

{{
    "score": <number 0-100>,
    "summary": "<brief summary>",
    "issues": [
        {{
            "severity": "critical|high|medium|low",
            "category": "<category name>",
            "file": "<file path>",
            "line": <line number or null>,
            "description": "<issue description>",
            "recommendation": "<how to fix>"
        }}
    ],
    "strengths": ["<strength 1>", "<strength 2>", ...],
    "recommendations": ["<recommendation 1>", "<recommendation 2>", ...]
}}

Please provide only the JSON output without any additional text or markdown formatting.
"""

        if metadata:
            prompt += f"\n# Additional Context\n\n{json.dumps(metadata, indent=2)}\n"

        return prompt

    def _execute_cli(self, code_dir: Path, prompt: str) -> Dict[str, Any]:
        """
        CLI 실행

        보안 샌드박스를 위해 체크아웃 받은 디렉토리(code_dir)에서 CLI를 실행합니다.
        프롬프트는 명령줄 인자로 전달됩니다.

        Args:
            code_dir: 코드 디렉토리 (CLI 실행 위치)
            prompt: 프롬프트 (명령줄 인자로 전달)

        Returns:
            파싱된 JSON 결과

        Raises:
            AICliException: CLI 실행 실패 시
        """
        try:
            # CLI 명령어 구성 (프롬프트를 명령줄 인자로 전달)
            cmd = self.build_cli_command(code_dir, prompt)

            # 환경 변수 설정
            env = self.get_env_vars()

            logger.info(
                "executing_ai_cli",
                provider=self.get_provider_name(),
                code_dir=str(code_dir),
                prompt_length=len(prompt),
                cmd_length=len(cmd),
            )

            # CLI 실행 (체크아웃 받은 디렉토리에서 실행 - 보안 샌드박스)
            result = subprocess.run(
                cmd,
                cwd=str(code_dir),
                capture_output=True,
                text=True,
                timeout=self.timeout,
                env=env,
            )

            if result.returncode != 0:
                logger.error(
                    "ai_cli_failed",
                    provider=self.get_provider_name(),
                    returncode=result.returncode,
                    stderr=result.stderr[:500] if result.stderr else None,
                )
                raise AICliException(
                    f"{self.get_provider_name()} CLI execution failed with code {result.returncode}",
                    details={
                        "provider": self.get_provider_name(),
                        "returncode": result.returncode,
                        "stdout": result.stdout[:500] if result.stdout else None,
                        "stderr": result.stderr[:500] if result.stderr else None,
                    },
                )

            # 결과 파싱
            output = result.stdout.strip()

            # JSON 추출 (마크다운 코드 블록 제거)
            if "```json" in output:
                output = output.split("```json")[1].split("```")[0].strip()
            elif "```" in output:
                output = output.split("```")[1].split("```")[0].strip()

            try:
                parsed_result = json.loads(output)
                return parsed_result
            except json.JSONDecodeError as e:
                logger.error(
                    "failed_to_parse_json",
                    provider=self.get_provider_name(),
                    output=output[:500],
                    error=str(e),
                )
                # JSON 파싱 실패 시 기본 결과 반환
                return {
                    "score": 0,
                    "summary": "Failed to parse inspection result",
                    "issues": [{
                        "severity": "critical",
                        "category": "parsing_error",
                        "file": None,
                        "line": None,
                        "description": f"Failed to parse {self.get_provider_name()} CLI output: {str(e)}",
                        "recommendation": "Check CLI output format",
                    }],
                    "strengths": [],
                    "recommendations": [],
                    "raw_output": output[:1000],
                }

        except subprocess.TimeoutExpired:
            logger.error("ai_cli_timeout", provider=self.get_provider_name(), timeout=self.timeout)
            raise AICliException(
                f"{self.get_provider_name()} CLI execution timed out after {self.timeout} seconds",
                details={"provider": self.get_provider_name(), "timeout": self.timeout},
            )

        except AICliException:
            raise

        except Exception as e:
            logger.exception("ai_cli_execution_error", provider=self.get_provider_name(), error=str(e))
            raise AICliException(
                f"Failed to execute {self.get_provider_name()} CLI: {str(e)}",
                details={"provider": self.get_provider_name(), "error": str(e)},
            )


class ClaudeInspector(BaseInspector):
    """Claude CLI 검사기"""

    def __init__(self):
        super().__init__(
            timeout=settings.claude_timeout,
            model=settings.claude_model,
            max_tokens=settings.claude_max_tokens,
        )

    def get_cli_path(self) -> str:
        return settings.claude_cli_path

    def get_api_key(self) -> Optional[str]:
        return settings.claude_api_key

    def get_provider_name(self) -> str:
        return "claude"

    def build_cli_command(self, code_dir: Path, prompt: str) -> list[str]:
        """
        Claude CLI 명령어 빌드

        Claude Code CLI 형식: claude -p "프롬프트"
        체크아웃 받은 디렉토리(code_dir)에서 실행됩니다.

        Args:
            code_dir: 코드 디렉토리 (현재 작업 디렉토리로 설정됨)
            prompt: 프롬프트 문자열

        Returns:
            CLI 명령어 리스트
        """
        return [
            self.get_cli_path(),
            "-p",
            prompt,
        ]

    def get_env_vars(self) -> dict:
        """Claude CLI 환경 변수"""
        env = os.environ.copy()
        if self.get_api_key():
            env["ANTHROPIC_API_KEY"] = self.get_api_key()
        return env


class CodexInspector(BaseInspector):
    """Codex CLI 검사기"""

    def __init__(self):
        super().__init__(
            timeout=settings.codex_timeout,
            model=settings.codex_model,
            max_tokens=settings.codex_max_tokens,
        )

    def get_cli_path(self) -> str:
        return settings.codex_cli_path

    def get_api_key(self) -> Optional[str]:
        return settings.codex_api_key

    def get_provider_name(self) -> str:
        return "codex"

    def build_cli_command(self, code_dir: Path, prompt: str) -> list[str]:
        """
        Codex CLI 명령어 빌드

        Codex CLI 형식 (Claude와 유사): codex -p "프롬프트"
        체크아웃 받은 디렉토리(code_dir)에서 실행됩니다.

        Args:
            code_dir: 코드 디렉토리 (현재 작업 디렉토리로 설정됨)
            prompt: 프롬프트 문자열

        Returns:
            CLI 명령어 리스트
        """
        return [
            self.get_cli_path(),
            "-p",
            prompt,
        ]

    def get_env_vars(self) -> dict:
        """Codex CLI 환경 변수"""
        env = os.environ.copy()
        if self.get_api_key():
            env["OPENAI_API_KEY"] = self.get_api_key()
        return env


class InspectorFactory:
    """검사기 팩토리 클래스"""

    @staticmethod
    def create_inspector(ai_provider: str) -> BaseInspector:
        """
        AI 제공자에 따른 검사기 인스턴스 생성

        Args:
            ai_provider: AI 제공자 이름 ("claude" 또는 "codex")

        Returns:
            BaseInspector 구현체

        Raises:
            ValueError: 지원하지 않는 AI 제공자인 경우
        """
        if ai_provider == "claude":
            return ClaudeInspector()
        elif ai_provider == "codex":
            return CodexInspector()
        else:
            raise ValueError(f"Unsupported AI provider: {ai_provider}")
