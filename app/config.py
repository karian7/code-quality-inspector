"""
애플리케이션 설정 관리
pydantic-settings를 사용하여 환경 변수 자동 로드
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
from pathlib import Path
import json


class Settings(BaseSettings):
    """애플리케이션 설정"""

    # 애플리케이션 기본 설정
    app_name: str = "Code Quality Inspector"
    app_version: str = "1.0.0"
    debug: bool = False
    log_level: str = "INFO"

    # FastAPI 설정
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_prefix: str = "/api"

    # Celery 설정
    celery_broker_url: str = "redis://redis:6379/0"
    celery_result_backend: str = "redis://redis:6379/0"
    celery_task_timeout: int = 900  # 15분
    celery_max_retries: int = 3
    celery_worker_concurrency: int = 5

    # Redis 설정
    redis_host: str = "redis"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: Optional[str] = None

    # Git 설정
    git_clone_timeout: int = 300  # 5분
    git_clone_depth: int = 1  # Shallow clone

    # Claude CLI 설정
    claude_cli_path: str = "claude"  # PATH에서 찾음
    claude_api_key: Optional[str] = None  # ANTHROPIC_API_KEY
    claude_model: str = "claude-3-opus-20240229"
    claude_max_tokens: int = 4096
    claude_timeout: int = 600  # 10분

    # 작업 디렉토리 설정
    work_dir: Path = Path("/tmp/code-inspection")
    rules_dir: Path = Path("/app/rules")

    # 보안 설정
    api_key_header: str = "X-API-Key"
    api_keys: str = "[]"  # JSON string of API keys

    # 콜백 설정
    callback_timeout: int = 30
    callback_max_retries: int = 3

    # 로깅 설정
    log_dir: Path = Path("/app/logs")
    log_file: str = "inspector.log"
    log_rotation: str = "100 MB"
    log_retention: str = "30 days"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 디렉토리 생성
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def get_api_keys_list(self) -> list[str]:
        """API 키 목록을 리스트로 반환"""
        try:
            return json.loads(self.api_keys)
        except (json.JSONDecodeError, TypeError):
            return []


settings = Settings()
