"""
Claude CLI를 사용한 코드 검사 서비스
"""
import subprocess
import json
from pathlib import Path
from typing import Dict, Any, Optional
import structlog
import tempfile
import os

from app.config import settings
from app.core.exceptions import ClaudeCliException

logger = structlog.get_logger()


class CodeInspector:
    """Claude CLI를 사용하여 코드를 검사하는 서비스"""

    def __init__(self):
        self.cli_path = settings.claude_cli_path
        self.timeout = settings.claude_timeout
        self.model = settings.claude_model
        self.max_tokens = settings.claude_max_tokens

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
            ClaudeCliException: Claude CLI 실행 실패 시
        """
        try:
            # 프롬프트 생성
            prompt = self._build_prompt(rules, metadata)

            logger.info(
                "claude_cli_inspection_started",
                code_dir=str(code_dir),
                prompt_length=len(prompt),
            )

            # Claude CLI 실행
            result = self._execute_claude_cli(code_dir, prompt)

            logger.info(
                "claude_cli_inspection_completed",
                code_dir=str(code_dir),
                result_length=len(str(result)),
            )

            return result

        except ClaudeCliException:
            raise
        except Exception as e:
            logger.exception("inspection_unexpected_error", error=str(e))
            raise ClaudeCliException(
                f"Unexpected error during code inspection: {str(e)}",
                details={"error": str(e)},
            )

    def _build_prompt(self, rules: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Claude CLI에 전달할 프롬프트 생성

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

    def _execute_claude_cli(self, code_dir: Path, prompt: str) -> Dict[str, Any]:
        """
        Claude CLI 실행

        Args:
            code_dir: 코드 디렉토리
            prompt: 프롬프트

        Returns:
            파싱된 JSON 결과

        Raises:
            ClaudeCliException: CLI 실행 실패 시
        """
        try:
            # 프롬프트를 임시 파일에 저장
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write(prompt)
                prompt_file = f.name

            try:
                # Claude CLI 명령어 구성
                # 실제 Claude CLI의 명령어 형식에 맞게 조정 필요
                cmd = [
                    self.cli_path,
                    "analyze",
                    str(code_dir),
                    "--prompt-file", prompt_file,
                    "--format", "json",
                ]

                # 환경 변수 설정
                env = os.environ.copy()
                if settings.claude_api_key:
                    env["ANTHROPIC_API_KEY"] = settings.claude_api_key

                logger.info("executing_claude_cli", cmd=" ".join(cmd))

                # CLI 실행
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
                        "claude_cli_failed",
                        returncode=result.returncode,
                        stderr=result.stderr,
                    )
                    raise ClaudeCliException(
                        f"Claude CLI execution failed with code {result.returncode}",
                        details={
                            "returncode": result.returncode,
                            "stdout": result.stdout,
                            "stderr": result.stderr,
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
                    logger.error("failed_to_parse_json", output=output[:500], error=str(e))
                    # JSON 파싱 실패 시 기본 결과 반환
                    return {
                        "score": 0,
                        "summary": "Failed to parse inspection result",
                        "issues": [{
                            "severity": "critical",
                            "category": "parsing_error",
                            "file": None,
                            "line": None,
                            "description": f"Failed to parse Claude CLI output: {str(e)}",
                            "recommendation": "Check Claude CLI output format",
                        }],
                        "strengths": [],
                        "recommendations": [],
                        "raw_output": output[:1000],
                    }

            finally:
                # 임시 파일 삭제
                try:
                    os.unlink(prompt_file)
                except:
                    pass

        except subprocess.TimeoutExpired:
            logger.error("claude_cli_timeout", timeout=self.timeout)
            raise ClaudeCliException(
                f"Claude CLI execution timed out after {self.timeout} seconds",
                details={"timeout": self.timeout},
            )

        except Exception as e:
            logger.exception("claude_cli_execution_error", error=str(e))
            raise ClaudeCliException(
                f"Failed to execute Claude CLI: {str(e)}",
                details={"error": str(e)},
            )
