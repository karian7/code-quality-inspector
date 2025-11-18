# 코드품질 검사기 서비스 PRD (Product Requirements Document)
# Python + FastAPI + Celery 구현 방안

## 문서 정보
- **버전**: 1.0.0
- **작성일**: 2025-01-18
- **대상 독자**: AI 개발 에이전트, DevOps 엔지니어
- **구현 난이도**: 중급
- **예상 구현 시간**: 3-4주

---

## 목차
1. [시스템 개요](#1-시스템-개요)
2. [기술 스택 및 의존성](#2-기술-스택-및-의존성)
3. [시스템 아키텍처](#3-시스템-아키텍처)
4. [디렉토리 구조](#4-디렉토리-구조)
5. [상세 구현 명세](#5-상세-구현-명세)
6. [Docker 환경 구성](#6-docker-환경-구성)
7. [환경 변수 및 설정](#7-환경-변수-및-설정)
8. [에러 처리 및 예외 상황](#8-에러-처리-및-예외-상황)
9. [보안 및 인증](#9-보안-및-인증)
10. [테스트 전략](#10-테스트-전략)
11. [모니터링 및 로깅](#11-모니터링-및-로깅)
12. [배포 및 운영](#12-배포-및-운영)

---

## 1. 시스템 개요

### 1.1 목적
GitHub 저장소의 코드를 자동으로 체크아웃하여 사전 정의된 심사 규칙에 따라 품질을 검사하고, 결과를 REST API로 전송하는 Docker 기반 마이크로서비스

### 1.2 핵심 기능
1. **코드 수신**: GitHub 저장소 URL 및 메타데이터 수신
2. **코드 체크아웃**: Git clone을 통한 소스코드 다운로드
3. **품질 검사**: Claude Code CLI 기반 자동화된 코드 리뷰
4. **결과 전송**: REST API를 통한 검사 결과 전달
5. **예외 처리**: 모든 실패 시나리오 대응 및 알림

### 1.3 비기능 요구사항
- **가용성**: 99% uptime
- **성능**: 단일 검사 최대 10분 이내 완료
- **동시성**: 최대 10개 작업 동시 처리
- **확장성**: Worker 수평 확장 가능
- **보안**: API 인증, 임시 파일 자동 삭제
- **관찰성**: 구조화된 로깅, 메트릭 수집

---

## 2. 기술 스택 및 의존성

### 2.1 핵심 기술 스택
```
언어: Python 3.11.7
웹 프레임워크: FastAPI 0.109.0
작업 큐: Celery 5.3.4 + Redis 7.2
프로세스 관리: Supervisor 4.2.5
HTTP 클라이언트: httpx 0.26.0
Git 클라이언트: GitPython 3.1.40
컨테이너: Docker 24.0+ / Docker Compose 2.23+
```

### 2.2 Python 패키지 의존성 (requirements.txt)
```txt
# Web Framework
fastapi==0.109.0
uvicorn[standard]==0.27.0
pydantic==2.5.3
pydantic-settings==2.1.0

# Task Queue
celery==5.3.4
redis==5.0.1
flower==2.0.1  # Celery monitoring

# Git Operations
GitPython==3.1.40

# HTTP Client
httpx==0.26.0

# Logging & Monitoring
structlog==24.1.0
python-json-logger==2.0.7

# Template Engine
jinja2==3.1.3

# Security
cryptography==42.0.0
python-dotenv==1.0.0

# Testing (dev)
pytest==7.4.4
pytest-asyncio==0.23.3
pytest-cov==4.1.0
httpx-mock==0.15.0
fakeredis==2.21.1
```

### 2.3 시스템 의존성 (apt packages)
```bash
# 필수 패키지
git                    # Git clone 작업
curl                   # Claude CLI 설치
ca-certificates        # HTTPS 통신
build-essential        # Python 패키지 빌드
libssl-dev             # OpenSSL 라이브러리
libffi-dev             # FFI 라이브러리
supervisor             # 프로세스 관리

# 선택 패키지 (디버깅용)
vim                    # 텍스트 편집
net-tools              # 네트워크 진단
procps                 # 프로세스 모니터링
```

### 2.4 Claude CLI 설치 요구사항
```bash
# Claude CLI 공식 설치 방법
# 주의: 실제 설치 URL은 Claude 공식 문서 확인 필요
# 현재 가상의 URL로 작성됨

# 설치 방법 1: curl을 통한 설치
curl -fsSL https://claude.ai/install.sh | bash

# 설치 방법 2: pip을 통한 설치 (존재할 경우)
pip install claude-cli

# 설치 방법 3: 바이너리 다운로드 (존재할 경우)
wget https://github.com/anthropics/claude-cli/releases/download/vX.Y.Z/claude-linux-amd64
chmod +x claude-linux-amd64
mv claude-linux-amd64 /usr/local/bin/claude
```

### 2.5 Claude CLI 인증 설정
```bash
# API Key 기반 인증
export ANTHROPIC_API_KEY="sk-ant-xxxxx"

# 또는 설정 파일 기반
mkdir -p ~/.config/claude
cat > ~/.config/claude/config.yaml <<EOF
api_key: ${ANTHROPIC_API_KEY}
model: claude-3-opus-20240229
max_tokens: 4096
EOF
```

---

## 3. 시스템 아키텍처

### 3.1 전체 시스템 아키텍처
```
┌─────────────────────────────────────────────────────────────┐
│                      Docker Compose 환경                      │
│                                                               │
│  ┌──────────────┐      ┌──────────────┐      ┌──────────┐  │
│  │   Nginx      │      │   FastAPI    │      │  Redis   │  │
│  │   (선택)     │─────▶│   Web API    │◀─────│  Broker  │  │
│  │   :80        │      │   :8000      │      │  :6379   │  │
│  └──────────────┘      └──────┬───────┘      └────▲─────┘  │
│         │                     │                    │         │
│         │              ┌──────▼─────────┐         │         │
│         │              │  Celery Worker │─────────┘         │
│         │              │  (5 instances) │                   │
│         │              └──────┬─────────┘                   │
│         │                     │                             │
│         │              ┌──────▼─────────┐                   │
│         │              │   Inspector    │                   │
│         │              │     Module     │                   │
│         │              └──────┬─────────┘                   │
│         │                     │                             │
│         │              ┌──────▼─────────┐                   │
│         │              │  Claude CLI    │                   │
│         │              │   subprocess   │                   │
│         │              └────────────────┘                   │
│         │                                                    │
│         └──────────▶ /tmp/code-inspection/                  │
│                      (임시 작업 디렉토리)                     │
└─────────────────────────────────────────────────────────────┘
         │                                          │
         ▼                                          ▼
  ┌─────────────┐                           ┌─────────────┐
  │   클라이언트  │                           │   Callback  │
  │   (HTTP)    │                           │   Server    │
  └─────────────┘                           └─────────────┘
```

### 3.2 데이터 플로우
```
1. 클라이언트 요청
   POST /api/inspect
   {
     "github_url": "https://github.com/user/repo",
     "branch": "main",
     "callback_url": "https://api.example.com/result"
   }
   ↓

2. FastAPI (요청 검증 및 큐잉)
   - 입력 데이터 검증
   - Task ID 생성
   - Celery 작업 큐에 추가
   - 즉시 응답: {"task_id": "uuid", "status": "queued"}
   ↓

3. Redis (작업 큐)
   - 작업 저장 및 대기열 관리
   - Worker에 작업 분배
   ↓

4. Celery Worker (비동기 처리)
   - 작업 수신 및 실행
   - 임시 디렉토리 생성
   - Git clone 실행
   - 심사 규칙 로드
   - Claude CLI 호출
   - 결과 파싱
   ↓

5. Inspector Module (코드 검사)
   - Claude CLI에 프롬프트 전달
   - 코드 분석 수행
   - JSON 결과 수신
   ↓

6. 결과 전송
   - 성공 시: POST callback_url with result
   - 실패 시: POST callback_url with error
   ↓

7. 정리
   - 임시 디렉토리 삭제
   - 작업 완료 로그 기록
```

### 3.3 컴포넌트 역할

#### 3.3.1 FastAPI Web Server
- **포트**: 8000
- **역할**: REST API 제공, 요청 검증, 작업 큐잉
- **엔드포인트**:
  - `GET /`: 웹 UI (상태 확인)
  - `GET /health`: Health check
  - `POST /api/inspect`: 검사 요청
  - `GET /api/status/{task_id}`: 작업 상태 조회
- **프로세스 관리**: Uvicorn (비동기 ASGI 서버)

#### 3.3.2 Celery Worker
- **인스턴스**: 5개 (동시 처리)
- **역할**: 비동기 작업 실행, Git 작업, CLI 호출
- **Concurrency**: 1 (worker당 1개 작업)
- **타임아웃**: 작업당 15분
- **재시도**: 실패 시 최대 3회

#### 3.3.3 Redis
- **포트**: 6379
- **역할**: 
  - Celery 메시지 브로커
  - 작업 결과 백엔드
  - 작업 상태 캐싱
- **데이터 영속성**: RDB + AOF

#### 3.3.4 Flower (모니터링, 선택)
- **포트**: 5555
- **역할**: Celery 작업 모니터링 대시보드

---

## 4. 디렉토리 구조

---

## 4. 디렉토리 구조

```
code-quality-inspector/
├── README.md
├── requirements.txt
├── requirements-dev.txt
├── .env.example
├── .gitignore
├── .dockerignore
├── docker-compose.yml
├── Dockerfile.web
├── Dockerfile.worker
├── pytest.ini
├── setup.py
│
├── app/
│   ├── __init__.py
│   ├── main.py                  # FastAPI 애플리케이션 진입점
│   ├── config.py                # 설정 관리 (pydantic-settings)
│   ├── dependencies.py          # FastAPI 의존성 주입
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes.py            # API 라우트
│   │   └── schemas.py           # Pydantic 스키마
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── celery_app.py        # Celery 설정
│   │   ├── logger.py            # 구조화된 로깅
│   │   ├── exceptions.py        # 커스텀 예외
│   │   └── security.py          # API 인증
│   │
│   ├── tasks/
│   │   ├── __init__.py
│   │   ├── inspection.py        # Celery 작업 정의
│   │   └── callbacks.py         # 결과 전송 로직
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── git_service.py       # Git 작업
│   │   ├── inspector.py         # Claude CLI 호출
│   │   └── rule_loader.py       # 심사 규칙 로더
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   └── task_result.py       # 작업 결과 모델
│   │
│   └── templates/
│       ├── index.html           # 웹 UI
│       └── status.html          # 작업 상태 페이지
│
├── rules/
│   ├── quality_rules.md         # 기본 품질 검사 규칙
│   ├── security_rules.md        # 보안 검사 규칙
│   └── performance_rules.md     # 성능 검사 규칙
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py              # pytest 설정
│   ├── test_api.py              # API 테스트
│   ├── test_tasks.py            # Celery 작업 테스트
│   ├── test_git_service.py      # Git 서비스 테스트
│   └── test_inspector.py        # Inspector 테스트
│
├── scripts/
│   ├── install_claude.sh        # Claude CLI 설치 스크립트
│   ├── healthcheck.sh           # Docker 헬스체크
│   └── wait-for-it.sh           # 서비스 대기 스크립트
│
├── docker/
│   ├── supervisor/
│   │   ├── supervisord.conf     # Supervisor 설정
│   │   ├── web.conf             # FastAPI 프로세스 설정
│   │   └── worker.conf          # Celery Worker 설정
│   │
│   └── nginx/
│       └── nginx.conf           # Nginx 설정 (선택)
│
└── logs/
    └── .gitkeep
```

### 4.1 디렉토리 설명

#### `/app`
핵심 애플리케이션 코드. FastAPI 서버와 Celery 작업 로직 포함.

#### `/rules`
코드 품질 검사 규칙을 정의한 Markdown 파일들. Claude CLI에 전달됨.

#### `/tests`
단위 테스트 및 통합 테스트. pytest 기반.

#### `/scripts`
설치, 배포, 헬스체크 등 유틸리티 스크립트.

#### `/docker`
Docker 관련 설정 파일. Supervisor, Nginx 등.

---

## 5. 상세 구현 명세

---

## 5. 상세 구현 명세

### 5.1 설정 관리 (app/config.py)

```python
"""
애플리케이션 설정 관리
pydantic-settings를 사용하여 환경 변수 자동 로드
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
from pathlib import Path


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
    api_keys: list[str] = []  # 허용된 API 키 목록
    
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


settings = Settings()
```

### 5.2 FastAPI 애플리케이션 (app/main.py)

```python
"""
FastAPI 애플리케이션 진입점
"""
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import structlog

from app.config import settings
from app.core.logger import setup_logging
from app.api.routes import router as api_router
from app.core.exceptions import InspectorException

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 시작/종료 시 실행"""
    # 시작
    setup_logging()
    logger.info(
        "application_started",
        app_name=settings.app_name,
        version=settings.app_version,
    )
    
    # Claude CLI 존재 확인
    import shutil
    if not shutil.which(settings.claude_cli_path):
        logger.error("claude_cli_not_found", path=settings.claude_cli_path)
        raise RuntimeError(f"Claude CLI not found at {settings.claude_cli_path}")
    
    logger.info("claude_cli_found", path=settings.claude_cli_path)
    
    yield
    
    # 종료
    logger.info("application_shutting_down")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
    lifespan=lifespan,
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 제한 필요
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 템플릿 설정
templates = Jinja2Templates(directory="app/templates")

# API 라우터 등록
app.include_router(api_router, prefix=settings.api_prefix)


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """메인 페이지"""
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "app_name": settings.app_name}
    )


@app.get("/health")
async def health_check():
    """헬스체크 엔드포인트"""
    return {
        "status": "healthy",
        "version": settings.app_version,
    }


@app.exception_handler(InspectorException)
async def inspector_exception_handler(request: Request, exc: InspectorException):
    """커스텀 예외 핸들러"""
    logger.error(
        "inspector_exception",
        error=str(exc),
        error_code=exc.error_code,
        path=request.url.path,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.error_code,
            "message": str(exc),
            "details": exc.details,
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """일반 예외 핸들러"""
    logger.exception("unhandled_exception", error=str(exc))
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "message": "An unexpected error occurred",
        },
    )
```

### 5.3 API 라우트 (app/api/routes.py)

```python
"""
API 엔드포인트 정의
"""
from fastapi import APIRouter, Depends, HTTPException, Header
from typing import Optional
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
                "metadata": request.metadata,
            }
        )
        
        logger.info(
            "inspection_task_created",
            task_id=task.id,
            github_url=str(request.github_url),
            branch=request.branch,
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
```

### 5.4 API 스키마 (app/api/schemas.py)

```python
"""
API 요청/응답 스키마
"""
from pydantic import BaseModel, HttpUrl, Field, validator
from typing import Optional, Dict, Any, List
from datetime import datetime


class InspectionRequest(BaseModel):
    """코드 검사 요청"""
    github_url: HttpUrl = Field(
        ...,
        description="GitHub 저장소 URL",
        example="https://github.com/user/repo",
    )
    branch: str = Field(
        default="main",
        description="검사할 브랜치 이름",
        example="main",
        min_length=1,
        max_length=255,
    )
    callback_url: HttpUrl = Field(
        ...,
        description="결과를 전송할 콜백 URL",
        example="https://api.example.com/webhook/inspection",
    )
    rules_files: List[str] = Field(
        default=["quality_rules.md"],
        description="사용할 심사 규칙 파일 목록",
        example=["quality_rules.md", "security_rules.md"],
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="추가 메타데이터 (콜백 시 함께 전송됨)",
    )
    
    @validator("github_url")
    def validate_github_url(cls, v):
        """GitHub URL 검증"""
        url_str = str(v)
        if "github.com" not in url_str:
            raise ValueError("Only GitHub URLs are supported")
        return v
    
    @validator("rules_files")
    def validate_rules_files(cls, v):
        """규칙 파일 검증"""
        if not v:
            raise ValueError("At least one rule file must be specified")
        for file in v:
            if not file.endswith(".md"):
                raise ValueError(f"Rule file must be a .md file: {file}")
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "github_url": "https://github.com/user/repo",
                "branch": "main",
                "callback_url": "https://api.example.com/webhook/inspection",
                "rules_files": ["quality_rules.md"],
                "metadata": {"project_id": "123", "user_id": "456"},
            }
        }


class InspectionResponse(BaseModel):
    """코드 검사 응답"""
    task_id: str = Field(..., description="작업 ID")
    status: str = Field(..., description="작업 상태")
    message: str = Field(..., description="응답 메시지")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class StatusResponse(BaseModel):
    """작업 상태 응답"""
    task_id: str
    status: str  # queued, pending, started, success, failure
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class CallbackPayload(BaseModel):
    """콜백 페이로드"""
    task_id: str
    status: str  # success, failed
    github_url: str
    branch: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    error_type: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    completed_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_schema_extra = {
            "example_success": {
                "task_id": "abc-123",
                "status": "success",
                "github_url": "https://github.com/user/repo",
                "branch": "main",
                "result": {
                    "score": 85,
                    "issues": [],
                    "recommendations": [],
                },
                "metadata": {"project_id": "123"},
                "completed_at": "2025-01-18T12:00:00Z",
            },
            "example_failed": {
                "task_id": "abc-123",
                "status": "failed",
                "github_url": "https://github.com/user/repo",
                "branch": "main",
                "error": "Git clone failed: Repository not found",
                "error_type": "GitCloneError",
                "metadata": {"project_id": "123"},
                "completed_at": "2025-01-18T12:00:00Z",
            },
        }
```

### 5.5 Celery 설정 (app/core/celery_app.py)

```python
"""
Celery 애플리케이션 설정
"""
from celery import Celery
from celery.signals import task_prerun, task_postrun, task_failure
import structlog

from app.config import settings

logger = structlog.get_logger()

# Celery 앱 생성
celery_app = Celery(
    "inspector",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.tasks.inspection"],
)

# Celery 설정
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=settings.celery_task_timeout,
    task_soft_time_limit=settings.celery_task_timeout - 60,
    worker_prefetch_multiplier=1,  # 한 번에 하나씩
    worker_max_tasks_per_child=50,  # 메모리 누수 방지
    broker_connection_retry_on_startup=True,
    result_expires=3600,  # 1시간 후 결과 삭제
)


@task_prerun.connect
def task_prerun_handler(task_id, task, *args, **kwargs):
    """작업 시작 전 로깅"""
    logger.info(
        "task_started",
        task_id=task_id,
        task_name=task.name,
    )


@task_postrun.connect
def task_postrun_handler(task_id, task, *args, **kwargs):
    """작업 완료 후 로깅"""
    logger.info(
        "task_completed",
        task_id=task_id,
        task_name=task.name,
    )


@task_failure.connect
def task_failure_handler(task_id, exception, *args, **kwargs):
    """작업 실패 로깅"""
    logger.error(
        "task_failed",
        task_id=task_id,
        exception=str(exception),
    )
```

### 5.6 Celery 작업 (app/tasks/inspection.py)

```python
"""
코드 검사 Celery 작업
"""
from celery import Task
from typing import Dict, Any, List, Optional
import tempfile
import shutil
from pathlib import Path
import structlog

from app.core.celery_app import celery_app
from app.config import settings
from app.services.git_service import GitService
from app.services.inspector import Inspector
from app.services.rule_loader import RuleLoader
from app.tasks.callbacks import send_callback
from app.core.exceptions import (
    GitCloneError,
    ClaudeCLIError,
    RuleLoadError,
    CallbackError,
)

logger = structlog.get_logger()


class InspectionTask(Task):
    """검사 작업 베이스 클래스"""
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """작업 실패 시 콜백 전송"""
        logger.error(
            "inspection_task_failed",
            task_id=task_id,
            exception=str(exc),
            traceback=str(einfo),
        )
        
        # 콜백 URL로 실패 알림
        callback_url = kwargs.get("callback_url")
        if callback_url:
            try:
                send_callback(
                    callback_url=callback_url,
                    task_id=task_id,
                    status="failed",
                    github_url=kwargs.get("github_url"),
                    branch=kwargs.get("branch"),
                    error=str(exc),
                    error_type=exc.__class__.__name__,
                    metadata=kwargs.get("metadata"),
                )
            except Exception as callback_exc:
                logger.error(
                    "failed_to_send_failure_callback",
                    task_id=task_id,
                    error=str(callback_exc),
                )


@celery_app.task(
    bind=True,
    base=InspectionTask,
    max_retries=settings.celery_max_retries,
    soft_time_limit=settings.celery_task_timeout - 60,
    time_limit=settings.celery_task_timeout,
)
def inspect_code_task(
    self,
    github_url: str,
    branch: str,
    callback_url: str,
    rules_files: List[str],
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    코드 검사 작업
    
    Args:
        github_url: GitHub 저장소 URL
        branch: 브랜치 이름
        callback_url: 결과 전송 URL
        rules_files: 심사 규칙 파일 목록
        metadata: 추가 메타데이터
    
    Returns:
        검사 결과
    
    Raises:
        GitCloneError: Git clone 실패
        ClaudeCLIError: Claude CLI 실행 실패
        RuleLoadError: 규칙 로드 실패
    """
    task_id = self.request.id
    temp_dir = None
    
    logger.info(
        "inspection_started",
        task_id=task_id,
        github_url=github_url,
        branch=branch,
    )
    
    try:
        # 1. 임시 디렉토리 생성
        temp_dir = Path(tempfile.mkdtemp(
            prefix="code-",
            dir=settings.work_dir,
        ))
        logger.debug("temp_directory_created", path=str(temp_dir))
        
        # 2. Git clone
        git_service = GitService()
        repo_path = git_service.clone_repository(
            url=github_url,
            branch=branch,
            target_dir=temp_dir,
        )
        logger.info("repository_cloned", path=str(repo_path))
        
        # 3. 심사 규칙 로드
        rule_loader = RuleLoader(rules_dir=settings.rules_dir)
        rules = rule_loader.load_rules(rules_files)
        logger.info("rules_loaded", files=rules_files)
        
        # 4. 코드 검사 실행
        inspector = Inspector()
        result = inspector.inspect(
            code_path=repo_path,
            rules=rules,
            task_id=task_id,
        )
        logger.info(
            "inspection_completed",
            task_id=task_id,
            score=result.get("score"),
        )
        
        # 5. 성공 콜백 전송
        send_callback(
            callback_url=callback_url,
            task_id=task_id,
            status="success",
            github_url=github_url,
            branch=branch,
            result=result,
            metadata=metadata,
        )
        logger.info("callback_sent", task_id=task_id)
        
        return result
        
    except Exception as e:
        logger.exception(
            "inspection_failed",
            task_id=task_id,
            error=str(e),
        )
        # on_failure 콜백에서 처리됨
        raise
        
    finally:
        # 6. 임시 디렉토리 정리
        if temp_dir and temp_dir.exists():
            try:
                shutil.rmtree(temp_dir)
                logger.debug("temp_directory_cleaned", path=str(temp_dir))
            except Exception as cleanup_error:
                logger.error(
                    "failed_to_cleanup",
                    path=str(temp_dir),
                    error=str(cleanup_error),
                )
```

### 5.7 Git 서비스 (app/services/git_service.py)

```python
"""
Git 작업 서비스
"""
from git import Repo, GitCommandError
from pathlib import Path
from typing import Optional
import structlog

from app.config import settings
from app.core.exceptions import GitCloneError

logger = structlog.get_logger()


class GitService:
    """Git 작업을 처리하는 서비스"""
    
    def __init__(self):
        self.timeout = settings.git_clone_timeout
        self.depth = settings.git_clone_depth
    
    def clone_repository(
        self,
        url: str,
        branch: str,
        target_dir: Path,
    ) -> Path:
        """
        저장소 클론
        
        Args:
            url: 저장소 URL
            branch: 브랜치 이름
            target_dir: 클론할 디렉토리
        
        Returns:
            클론된 저장소 경로
        
        Raises:
            GitCloneError: 클론 실패 시
        """
        try:
            logger.info(
                "cloning_repository",
                url=url,
                branch=branch,
                target=str(target_dir),
            )
            
            # Shallow clone으로 빠른 다운로드
            repo = Repo.clone_from(
                url=url,
                to_path=str(target_dir),
                branch=branch,
                depth=self.depth,
                single_branch=True,
                # Git 환경 변수 설정
                env={
                    "GIT_TERMINAL_PROMPT": "0",  # 비밀번호 프롬프트 비활성화
                    "GIT_ASKPASS": "echo",  # 인증 스킵
                },
            )
            
            # 클론 성공 검증
            if not target_dir.exists() or not (target_dir / ".git").exists():
                raise GitCloneError(
                    f"Repository clone failed: directory not created",
                    details={"url": url, "branch": branch},
                )
            
            logger.info(
                "repository_cloned_successfully",
                url=url,
                commit=repo.head.commit.hexsha[:8],
            )
            
            return target_dir
            
        except GitCommandError as e:
            error_msg = str(e.stderr) if e.stderr else str(e)
            
            # 에러 타입 분류
            if "Repository not found" in error_msg or "404" in error_msg:
                raise GitCloneError(
                    f"Repository not found: {url}",
                    error_code="repository_not_found",
                    details={"url": url, "branch": branch},
                ) from e
            elif "Could not resolve host" in error_msg:
                raise GitCloneError(
                    "Network error: Could not resolve host",
                    error_code="network_error",
                    details={"url": url},
                ) from e
            elif "Authentication failed" in error_msg:
                raise GitCloneError(
                    "Authentication failed: Private repository requires credentials",
                    error_code="authentication_error",
                    details={"url": url},
                ) from e
            elif "timeout" in error_msg.lower():
                raise GitCloneError(
                    f"Clone timeout after {self.timeout} seconds",
                    error_code="clone_timeout",
                    details={"url": url, "timeout": self.timeout},
                ) from e
            else:
                raise GitCloneError(
                    f"Git clone failed: {error_msg}",
                    details={"url": url, "branch": branch, "error": error_msg},
                ) from e
                
        except Exception as e:
            logger.exception("unexpected_git_error", error=str(e))
            raise GitCloneError(
                f"Unexpected error during git clone: {str(e)}",
                details={"url": url, "branch": branch},
            ) from e
```

### 5.8 Inspector 서비스 (app/services/inspector.py)

```python
"""
Claude CLI를 사용한 코드 검사 서비스
"""
import subprocess
import json
from pathlib import Path
from typing import Dict, Any
import structlog

from app.config import settings
from app.core.exceptions import ClaudeCLIError

logger = structlog.get_logger()


class Inspector:
    """코드 검사를 수행하는 서비스"""
    
    def __init__(self):
        self.cli_path = settings.claude_cli_path
        self.timeout = settings.claude_timeout
        self.max_tokens = settings.claude_max_tokens
        self.model = settings.claude_model
    
    def inspect(
        self,
        code_path: Path,
        rules: str,
        task_id: str,
    ) -> Dict[str, Any]:
        """
        코드 검사 실행
        
        Args:
            code_path: 검사할 코드 경로
            rules: 심사 규칙 텍스트
            task_id: 작업 ID
        
        Returns:
            검사 결과 딕셔너리
        
        Raises:
            ClaudeCLIError: Claude CLI 실행 실패
        """
        try:
            logger.info(
                "starting_code_inspection",
                task_id=task_id,
                code_path=str(code_path),
            )
            
            # 프롬프트 생성
            prompt = self._create_prompt(code_path, rules)
            
            # Claude CLI 실행
            output = self._run_claude_cli(prompt, task_id)
            
            # 결과 파싱
            result = self._parse_output(output, task_id)
            
            logger.info(
                "inspection_completed_successfully",
                task_id=task_id,
            )
            
            return result
            
        except ClaudeCLIError:
            raise
        except Exception as e:
            logger.exception("inspection_error", task_id=task_id, error=str(e))
            raise ClaudeCLIError(
                f"Code inspection failed: {str(e)}",
                details={"task_id": task_id, "code_path": str(code_path)},
            ) from e
    
    def _create_prompt(self, code_path: Path, rules: str) -> str:
        """검사 프롬프트 생성"""
        return f"""
당신은 코드 품질 검사 전문가입니다. 다음 규칙에 따라 코드를 분석하세요.

## 코드 경로
{code_path}

## 심사 규칙
{rules}

## 분석 요구사항
1. 위 경로의 모든 코드 파일을 재귀적으로 분석하세요
2. 심사 규칙에 명시된 모든 기준을 적용하세요
3. 발견된 문제점과 개선 사항을 구체적으로 기록하세요
4. 반드시 아래 JSON 형식으로만 응답하세요

## 응답 형식 (JSON)
{{
  "score": 0-100 사이의 점수,
  "summary": "전체 평가 요약 (200자 이내)",
  "issues": [
    {{
      "severity": "critical|high|medium|low",
      "category": "문제 카테고리",
      "file": "파일 경로",
      "line": 라인 번호 (선택),
      "description": "문제 설명",
      "recommendation": "개선 방안"
    }}
  ],
  "recommendations": [
    {{
      "category": "개선 카테고리",
      "priority": "high|medium|low",
      "description": "개선 제안",
      "benefit": "기대 효과"
    }}
  ],
  "metrics": {{
    "files_analyzed": 분석한 파일 수,
    "critical_issues": 심각한 문제 수,
    "high_issues": 높은 우선순위 문제 수,
    "medium_issues": 중간 우선순위 문제 수,
    "low_issues": 낮은 우선순위 문제 수
  }}
}}

이제 분석을 시작하세요. JSON 형식만 출력하세요.
""".strip()
    
    def _run_claude_cli(self, prompt: str, task_id: str) -> str:
        """
        Claude CLI 실행
        
        Returns:
            Claude의 응답 텍스트
        
        Raises:
            ClaudeCLIError: 실행 실패 시
        """
        try:
            # 환경 변수 설정
            env = {}
            if settings.claude_api_key:
                env["ANTHROPIC_API_KEY"] = settings.claude_api_key
            
            # CLI 명령 구성
            cmd = [
                self.cli_path,
                "--model", self.model,
                "--max-tokens", str(self.max_tokens),
                "--message", prompt,
            ]
            
            logger.debug(
                "executing_claude_cli",
                task_id=task_id,
                model=self.model,
                max_tokens=self.max_tokens,
            )
            
            # subprocess 실행
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                env={**subprocess.os.environ, **env},
                check=False,
            )
            
            # 에러 체크
            if result.returncode != 0:
                error_msg = result.stderr or result.stdout or "Unknown error"
                
                # API 키 오류
                if "authentication" in error_msg.lower() or "api key" in error_msg.lower():
                    raise ClaudeCLIError(
                        "Claude API authentication failed. Check your API key.",
                        error_code="authentication_error",
                        details={"task_id": task_id},
                    )
                
                # Rate limit
                if "rate limit" in error_msg.lower() or "429" in error_msg:
                    raise ClaudeCLIError(
                        "Claude API rate limit exceeded. Please try again later.",
                        error_code="rate_limit_error",
                        details={"task_id": task_id},
                    )
                
                # 일반 오류
                raise ClaudeCLIError(
                    f"Claude CLI failed: {error_msg}",
                    error_code="cli_execution_error",
                    details={
                        "task_id": task_id,
                        "return_code": result.returncode,
                        "stderr": result.stderr,
                    },
                )
            
            output = result.stdout.strip()
            
            if not output:
                raise ClaudeCLIError(
                    "Claude CLI returned empty output",
                    error_code="empty_output",
                    details={"task_id": task_id},
                )
            
            logger.debug(
                "claude_cli_completed",
                task_id=task_id,
                output_length=len(output),
            )
            
            return output
            
        except subprocess.TimeoutExpired as e:
            logger.error(
                "claude_cli_timeout",
                task_id=task_id,
                timeout=self.timeout,
            )
            raise ClaudeCLIError(
                f"Claude CLI timeout after {self.timeout} seconds",
                error_code="cli_timeout",
                details={"task_id": task_id, "timeout": self.timeout},
            ) from e
            
        except FileNotFoundError as e:
            raise ClaudeCLIError(
                f"Claude CLI not found at path: {self.cli_path}",
                error_code="cli_not_found",
                details={"cli_path": self.cli_path},
            ) from e
    
    def _parse_output(self, output: str, task_id: str) -> Dict[str, Any]:
        """
        Claude 출력 파싱
        
        Args:
            output: Claude CLI 출력
            task_id: 작업 ID
        
        Returns:
            파싱된 결과 딕셔너리
        
        Raises:
            ClaudeCLIError: 파싱 실패 시
        """
        try:
            # JSON 추출 (```json ... ``` 형식 처리)
            json_start = output.find("{")
            json_end = output.rfind("}") + 1
            
            if json_start == -1 or json_end == 0:
                raise ClaudeCLIError(
                    "No JSON found in Claude output",
                    error_code="json_not_found",
                    details={"task_id": task_id, "output_preview": output[:200]},
                )
            
            json_str = output[json_start:json_end]
            result = json.loads(json_str)
            
            # 필수 필드 검증
            required_fields = ["score", "summary", "issues", "recommendations", "metrics"]
            for field in required_fields:
                if field not in result:
                    raise ClaudeCLIError(
                        f"Missing required field in result: {field}",
                        error_code="invalid_result_format",
                        details={"task_id": task_id, "missing_field": field},
                    )
            
            # 점수 범위 검증
            if not (0 <= result["score"] <= 100):
                logger.warning(
                    "invalid_score",
                    task_id=task_id,
                    score=result["score"],
                )
                result["score"] = max(0, min(100, result["score"]))
            
            return result
            
        except json.JSONDecodeError as e:
            logger.error(
                "json_parse_error",
                task_id=task_id,
                error=str(e),
                output_preview=output[:500],
            )
            raise ClaudeCLIError(
                f"Failed to parse Claude output as JSON: {str(e)}",
                error_code="json_parse_error",
                details={"task_id": task_id, "parse_error": str(e)},
            ) from e
```

계속해서 나머지 구현 명세를 작성하겠습니다...
```python
# main.py
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel, HttpUrl

app = FastAPI()

class InspectionRequest(BaseModel):
    github_url: HttpUrl
    branch: str = "main"
    callback_url: HttpUrl

@app.post("/api/inspect")
async def create_inspection(request: InspectionRequest):
    task = inspect_code.delay(
        str(request.github_url),
        request.branch,
        str(request.callback_url)
    )
    return {"task_id": task.id, "status": "queued"}

@app.get("/")
async def root():
    return templates.TemplateResponse("index.html")
```

#### 2. Worker Layer (Celery)
```python
# tasks.py
from celery import Celery
import subprocess
import tempfile
import shutil

celery = Celery('inspector', broker='redis://redis:6379')

@celery.task(bind=True)
def inspect_code(self, github_url, branch, callback_url):
    temp_dir = None
    try:
        # 1. 코드 체크아웃
        temp_dir = tempfile.mkdtemp()
        clone_repository(github_url, branch, temp_dir)
        
        # 2. 심사 규칙 로드
        rules = load_inspection_rules('rules/quality_rules.md')
        
        # 3. Claude CLI 실행
        result = run_claude_inspection(temp_dir, rules)
        
        # 4. 결과 전송
        send_result(callback_url, {
            "status": "success",
            "task_id": self.request.id,
            "result": result
        })
        
    except Exception as e:
        # 5. 실패 처리
        send_result(callback_url, {
            "status": "failed",
            "task_id": self.request.id,
            "error": str(e)
        })
    finally:
        if temp_dir:
            shutil.rmtree(temp_dir, ignore_errors=True)
```

#### 3. Inspector Module
```python
# inspector.py
def run_claude_inspection(code_path, rules):
    prompt = f"""
    코드 경로: {code_path}
    
    심사 규칙:
    {rules}
    
    위 규칙에 따라 코드를 분석하고 JSON 형식으로 결과를 제공하세요.
    """
    
    result = subprocess.run(
        ['claude', '--message', prompt],
        capture_output=True,
        text=True,
        timeout=600
    )
    
    return parse_claude_output(result.stdout)
```

### Docker 구성
```dockerfile
# Dockerfile
FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Claude CLI 설치
RUN curl -fsSL https://claude.ai/install.sh | sh

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```yaml
# docker-compose.yml
version: '3.8'
services:
  web:
    build: .
    ports:
      - "8000:8000"
    environment:
      - CELERY_BROKER_URL=redis://redis:6379
    depends_on:
      - redis
  
  worker:
    build: .
    command: celery -A tasks worker --loglevel=info
    environment:
      - CELERY_BROKER_URL=redis://redis:6379
    depends_on:
      - redis
  
  redis:
    image: redis:7-alpine
```

### 장점
- Python의 간결한 문법으로 빠른 개발
- subprocess로 Claude CLI 실행 용이
- FastAPI의 자동 문서화 (Swagger UI)
- Celery로 안정적인 비동기 처리
- 풍부한 Git/HTTP 라이브러리

### 단점
- Python의 상대적으로 느린 실행 속도
- GIL로 인한 멀티스레딩 제약

---

## 방안 2: Node.js + Express + BullMQ

### 아키텍처
```
┌─────────────┐
│   Express   │ ← 웹 서버 + API
└──────┬──────┘
       │
       ↓
┌─────────────┐
│   BullMQ    │ ← 작업 큐
│   Worker    │
└──────┬──────┘
       │
       ↓
┌─────────────┐
│ Child Process│ ← Claude CLI
└─────────────┘
```

### 기술 스택
- **언어**: Node.js 20+ (TypeScript)
- **웹 프레임워크**: Express
- **작업 큐**: BullMQ + Redis
- **Git 작업**: simple-git
- **프로세스 실행**: child_process
- **템플릿**: EJS
- **컨테이너**: Docker

### 주요 컴포넌트

#### 1. Web Server
```typescript
// src/server.ts
import express from 'express';
import { Queue } from 'bullmq';

const app = express();
const inspectionQueue = new Queue('code-inspection');

app.post('/api/inspect', async (req, res) => {
  const { github_url, branch, callback_url } = req.body;
  
  const job = await inspectionQueue.add('inspect', {
    githubUrl: github_url,
    branch: branch || 'main',
    callbackUrl: callback_url
  });
  
  res.json({ taskId: job.id, status: 'queued' });
});

app.listen(3000);
```

#### 2. Worker
```typescript
// src/worker.ts
import { Worker } from 'bullmq';
import { spawn } from 'child_process';
import simpleGit from 'simple-git';
import fs from 'fs/promises';
import os from 'os';
import path from 'path';
import axios from 'axios';

const worker = new Worker('code-inspection', async (job) => {
  const { githubUrl, branch, callbackUrl } = job.data;
  let tempDir: string | null = null;
  
  try {
    // 1. 임시 디렉토리 생성
    tempDir = await fs.mkdtemp(path.join(os.tmpdir(), 'code-'));
    
    // 2. Git Clone
    const git = simpleGit();
    await git.clone(githubUrl, tempDir, ['--branch', branch, '--depth', '1']);
    
    // 3. 심사 규칙 로드
    const rules = await fs.readFile('rules/quality_rules.md', 'utf-8');
    
    // 4. Claude CLI 실행
    const result = await runClaudeInspection(tempDir, rules);
    
    // 5. 성공 결과 전송
    await axios.post(callbackUrl, {
      status: 'success',
      taskId: job.id,
      result
    });
    
  } catch (error) {
    // 6. 실패 결과 전송
    await axios.post(callbackUrl, {
      status: 'failed',
      taskId: job.id,
      error: error.message
    });
    throw error;
  } finally {
    // 7. 정리
    if (tempDir) {
      await fs.rm(tempDir, { recursive: true, force: true });
    }
  }
});

function runClaudeInspection(codePath: string, rules: string): Promise<any> {
  return new Promise((resolve, reject) => {
    const prompt = `코드 경로: ${codePath}\n\n심사 규칙:\n${rules}\n\n위 규칙에 따라 코드를 분석하세요.`;
    
    const claude = spawn('claude', ['--message', prompt]);
    let output = '';
    
    claude.stdout.on('data', (data) => {
      output += data.toString();
    });
    
    claude.on('close', (code) => {
      if (code === 0) {
        resolve(JSON.parse(output));
      } else {
        reject(new Error(`Claude CLI exited with code ${code}`));
      }
    });
    
    setTimeout(() => {
      claude.kill();
      reject(new Error('Claude CLI timeout'));
    }, 600000);
  });
}
```

### Docker 구성
```dockerfile
FROM node:20-slim

RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Claude CLI 설치
RUN curl -fsSL https://claude.ai/install.sh | sh

WORKDIR /app
COPY package*.json ./
RUN npm ci --production

COPY . .
RUN npm run build

CMD ["node", "dist/server.js"]
```

### 장점
- 비동기 I/O에 최적화
- child_process로 CLI 실행 용이
- npm 생태계의 풍부한 패키지
- TypeScript로 타입 안정성 확보
- 상대적으로 가벼운 메모리 사용

### 단점
- 콜백/Promise 체이닝 복잡도
- Python 대비 데이터 처리 라이브러리 부족

---

## 방안 3: Go + Gin + 네이티브 고루틴

### 아키텍처
```
┌─────────────┐
│  Gin Server │ ← HTTP 서버
└──────┬──────┘
       │
       ↓
┌─────────────┐
│  Goroutine  │ ← 동시성 작업
│   Workers   │
└──────┬──────┘
       │
       ↓
┌─────────────┐
│ exec.Command│ ← Claude CLI
└─────────────┘
```

### 기술 스택
- **언어**: Go 1.21+
- **웹 프레임워크**: Gin
- **Git 작업**: go-git
- **프로세스 실행**: os/exec
- **템플릿**: html/template
- **컨테이너**: Docker (멀티스테이지 빌드)

### 주요 컴포넌트

#### 1. Web Server
```go
// main.go
package main

import (
    "github.com/gin-gonic/gin"
    "github.com/google/uuid"
)

type InspectionRequest struct {
    GithubURL   string `json:"github_url" binding:"required"`
    Branch      string `json:"branch"`
    CallbackURL string `json:"callback_url" binding:"required"`
}

var jobQueue = make(chan InspectionJob, 100)

func main() {
    // Worker pool 시작
    for i := 0; i < 5; i++ {
        go worker(jobQueue)
    }
    
    r := gin.Default()
    
    r.POST("/api/inspect", func(c *gin.Context) {
        var req InspectionRequest
        if err := c.ShouldBindJSON(&req); err != nil {
            c.JSON(400, gin.H{"error": err.Error()})
            return
        }
        
        if req.Branch == "" {
            req.Branch = "main"
        }
        
        taskID := uuid.New().String()
        job := InspectionJob{
            ID:          taskID,
            GithubURL:   req.GithubURL,
            Branch:      req.Branch,
            CallbackURL: req.CallbackURL,
        }
        
        jobQueue <- job
        
        c.JSON(200, gin.H{
            "task_id": taskID,
            "status":  "queued",
        })
    })
    
    r.Run(":8080")
}
```

#### 2. Worker
```go
// worker.go
package main

import (
    "bytes"
    "context"
    "encoding/json"
    "fmt"
    "io/ioutil"
    "net/http"
    "os"
    "os/exec"
    "path/filepath"
    "time"
    
    "github.com/go-git/go-git/v5"
)

type InspectionJob struct {
    ID          string
    GithubURL   string
    Branch      string
    CallbackURL string
}

type Result struct {
    Status string      `json:"status"`
    TaskID string      `json:"task_id"`
    Result interface{} `json:"result,omitempty"`
    Error  string      `json:"error,omitempty"`
}

func worker(jobs <-chan InspectionJob) {
    for job := range jobs {
        processJob(job)
    }
}

func processJob(job InspectionJob) {
    var tempDir string
    
    defer func() {
        if tempDir != "" {
            os.RemoveAll(tempDir)
        }
    }()
    
    result := Result{
        TaskID: job.ID,
    }
    
    // 1. 임시 디렉토리 생성
    var err error
    tempDir, err = ioutil.TempDir("", "code-")
    if err != nil {
        result.Status = "failed"
        result.Error = err.Error()
        sendResult(job.CallbackURL, result)
        return
    }
    
    // 2. Git Clone
    _, err = git.PlainClone(tempDir, false, &git.CloneOptions{
        URL:           job.GithubURL,
        ReferenceName: fmt.Sprintf("refs/heads/%s", job.Branch),
        Depth:         1,
    })
    if err != nil {
        result.Status = "failed"
        result.Error = fmt.Sprintf("Clone failed: %v", err)
        sendResult(job.CallbackURL, result)
        return
    }
    
    // 3. 심사 규칙 로드
    rules, err := ioutil.ReadFile("rules/quality_rules.md")
    if err != nil {
        result.Status = "failed"
        result.Error = fmt.Sprintf("Rules load failed: %v", err)
        sendResult(job.CallbackURL, result)
        return
    }
    
    // 4. Claude CLI 실행
    inspectionResult, err := runClaudeInspection(tempDir, string(rules))
    if err != nil {
        result.Status = "failed"
        result.Error = fmt.Sprintf("Inspection failed: %v", err)
        sendResult(job.CallbackURL, result)
        return
    }
    
    // 5. 성공 결과
    result.Status = "success"
    result.Result = inspectionResult
    sendResult(job.CallbackURL, result)
}

func runClaudeInspection(codePath, rules string) (interface{}, error) {
    prompt := fmt.Sprintf("코드 경로: %s\n\n심사 규칙:\n%s\n\n위 규칙에 따라 코드를 분석하세요.", codePath, rules)
    
    ctx, cancel := context.WithTimeout(context.Background(), 10*time.Minute)
    defer cancel()
    
    cmd := exec.CommandContext(ctx, "claude", "--message", prompt)
    
    var stdout, stderr bytes.Buffer
    cmd.Stdout = &stdout
    cmd.Stderr = &stderr
    
    err := cmd.Run()
    if err != nil {
        return nil, fmt.Errorf("claude error: %v, stderr: %s", err, stderr.String())
    }
    
    var result interface{}
    if err := json.Unmarshal(stdout.Bytes(), &result); err != nil {
        return nil, fmt.Errorf("parse error: %v", err)
    }
    
    return result, nil
}

func sendResult(url string, result Result) error {
    data, err := json.Marshal(result)
    if err != nil {
        return err
    }
    
    resp, err := http.Post(url, "application/json", bytes.NewBuffer(data))
    if err != nil {
        return err
    }
    defer resp.Body.Close()
    
    return nil
}
```

### Docker 구성
```dockerfile
# 멀티스테이지 빌드
FROM golang:1.21-alpine AS builder

RUN apk add --no-cache git

WORKDIR /build
COPY go.mod go.sum ./
RUN go mod download

COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -o inspector .

FROM alpine:latest

RUN apk add --no-cache git curl
RUN curl -fsSL https://claude.ai/install.sh | sh

WORKDIR /app
COPY --from=builder /build/inspector .
COPY rules ./rules
COPY templates ./templates

EXPOSE 8080
CMD ["./inspector"]
```

### 장점
- 네이티브 컴파일로 빠른 실행 속도
- 고루틴으로 효율적인 동시성
- 외부 의존성 최소화 (단일 바이너리)
- 낮은 메모리 사용량
- 강력한 타입 시스템

### 단점
- Python/Node.js 대비 개발 생산성 낮음
- 템플릿/프론트엔드 생태계 부족
- Claude CLI 통합 시 바이너리 크기 증가 가능

---

## 4. 방안 비교표

| 항목 | Python + FastAPI | Node.js + Express | Go + Gin |
|------|-----------------|-------------------|----------|
| **개발 속도** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| **실행 성능** | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **메모리 효율** | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **CLI 통합** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **웹 UI 구현** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| **Docker 최적화** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **동시성 처리** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **커뮤니티/자료** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **유지보수성** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Docker 이미지 크기** | ~500MB | ~300MB | ~50MB |

## 5. 권장사항

### 🏆 추천: Python + FastAPI + Celery

**추천 이유:**
1. **빠른 프로토타이핑**: 요구사항 변경에 유연하게 대응
2. **CLI 통합 용이**: subprocess로 간단하게 Claude CLI 실행
3. **풍부한 생태계**: Git, HTTP, 데이터 처리 라이브러리 완비
4. **자동 문서화**: FastAPI의 Swagger UI로 API 문서 자동 생성
5. **안정적인 작업 큐**: Celery의 검증된 비동기 처리

**사용 시나리오:**
- MVP 빠르게 개발하고 피드백 수집
- 심사 규칙이 자주 변경되는 경우
- 데이터 분석/리포팅 기능 추가 예정
- 팀이 Python에 익숙한 경우

### 대안 선택 가이드

**Node.js를 선택하는 경우:**
- 프론트엔드가 React/Vue 등 JS 기반
- 팀이 JavaScript/TypeScript에 더 익숙
- 실시간 웹소켓 기능 필요

**Go를 선택하는 경우:**
- 초고성능/대규모 동시 요청 처리 필요
- Docker 이미지 크기 최소화 중요
- 시스템 리소스 효율 최우선
- 장기 운영 안정성 중시

## 6. 구현 로드맵

### Phase 1: MVP (2-3주)
- 기본 웹 서버 + API 구현
- GitHub clone 기능
- Claude CLI 연동
- 결과 전송 기능

### Phase 2: 안정화 (2주)
- 예외 처리 강화
- 로깅/모니터링
- 작업 큐 안정화
- Docker 최적화

### Phase 3: 고도화 (3-4주)
- 웹 UI 개선
- 심사 이력 저장
- 재시도 메커니즘
- 성능 최적화

## 7. 추가 고려사항

### 보안
- GitHub 토큰 안전한 저장 (환경변수/Secrets)
- 임시 파일 자동 삭제
- API 인증/인가
- Rate limiting

### 모니터링
- 작업 큐 상태 모니터링
- 실패율/성공률 추적
- Claude CLI 응답 시간 측정
- 리소스 사용량 알림

### 확장성
- Worker 수평 확장
- Redis 클러스터
- 결과 캐싱
- CDN 활용 (정적 파일)

### 5.9 Rule Loader (app/services/rule_loader.py)

```python
"""
심사 규칙 로더 서비스
"""
from pathlib import Path
from typing import List
import structlog

from app.core.exceptions import RuleLoadError

logger = structlog.get_logger()


class RuleLoader:
    """심사 규칙 파일을 로드하는 서비스"""
    
    def __init__(self, rules_dir: Path):
        self.rules_dir = rules_dir
    
    def load_rules(self, files: List[str]) -> str:
        """
        여러 규칙 파일을 로드하여 결합
        
        Args:
            files: 규칙 파일 이름 목록
        
        Returns:
            결합된 규칙 텍스트
        
        Raises:
            RuleLoadError: 파일 로드 실패
        """
        rules_content = []
        
        for filename in files:
            filepath = self.rules_dir / filename
            
            if not filepath.exists():
                raise RuleLoadError(
                    f"Rule file not found: {filename}",
                    error_code="file_not_found",
                    details={"filename": filename, "path": str(filepath)},
                )
            
            try:
                content = filepath.read_text(encoding="utf-8")
                rules_content.append(f"# {filename}\n\n{content}")
                logger.debug("rule_file_loaded", filename=filename, size=len(content))
            except Exception as e:
                raise RuleLoadError(
                    f"Failed to read rule file: {filename}",
                    details={"filename": filename, "error": str(e)},
                ) from e
        
        combined = "\n\n---\n\n".join(rules_content)
        logger.info("rules_loaded", file_count=len(files), total_size=len(combined))
        
        return combined
```

### 5.10 Callback 서비스 (app/tasks/callbacks.py)

```python
"""
결과 콜백 전송 서비스
"""
import httpx
from typing import Dict, Any, Optional
from datetime import datetime
import structlog

from app.config import settings
from app.api.schemas import CallbackPayload
from app.core.exceptions import CallbackError

logger = structlog.get_logger()


def send_callback(
    callback_url: str,
    task_id: str,
    status: str,
    github_url: str,
    branch: str,
    result: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None,
    error_type: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """
    콜백 URL로 결과 전송
    
    Args:
        callback_url: 콜백 URL
        task_id: 작업 ID
        status: 상태 (success/failed)
        github_url: GitHub URL
        branch: 브랜치
        result: 검사 결과 (성공 시)
        error: 에러 메시지 (실패 시)
        error_type: 에러 타입 (실패 시)
        metadata: 추가 메타데이터
    
    Raises:
        CallbackError: 콜백 전송 실패
    """
    payload = CallbackPayload(
        task_id=task_id,
        status=status,
        github_url=github_url,
        branch=branch,
        result=result,
        error=error,
        error_type=error_type,
        metadata=metadata,
    )
    
    max_retries = settings.callback_max_retries
    timeout = settings.callback_timeout
    
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(
                "sending_callback",
                task_id=task_id,
                url=callback_url,
                attempt=attempt,
                status=status,
            )
            
            with httpx.Client(timeout=timeout) as client:
                response = client.post(
                    callback_url,
                    json=payload.model_dump(mode="json", exclude_none=True),
                    headers={"Content-Type": "application/json"},
                )
                
                response.raise_for_status()
                
                logger.info(
                    "callback_sent_successfully",
                    task_id=task_id,
                    status_code=response.status_code,
                    attempt=attempt,
                )
                return
                
        except httpx.TimeoutException as e:
            logger.warning(
                "callback_timeout",
                task_id=task_id,
                attempt=attempt,
                timeout=timeout,
            )
            if attempt == max_retries:
                raise CallbackError(
                    f"Callback timeout after {max_retries} attempts",
                    error_code="callback_timeout",
                    details={"task_id": task_id, "url": callback_url},
                ) from e
                
        except httpx.HTTPStatusError as e:
            logger.warning(
                "callback_http_error",
                task_id=task_id,
                status_code=e.response.status_code,
                attempt=attempt,
            )
            if attempt == max_retries:
                raise CallbackError(
                    f"Callback HTTP error: {e.response.status_code}",
                    error_code="callback_http_error",
                    details={
                        "task_id": task_id,
                        "status_code": e.response.status_code,
                        "response": e.response.text,
                    },
                ) from e
                
        except Exception as e:
            logger.error(
                "callback_unexpected_error",
                task_id=task_id,
                error=str(e),
                attempt=attempt,
            )
            if attempt == max_retries:
                raise CallbackError(
                    f"Callback failed: {str(e)}",
                    details={"task_id": task_id, "error": str(e)},
                ) from e
        
        # 재시도 전 대기 (exponential backoff)
        if attempt < max_retries:
            import time
            wait_time = 2 ** attempt  # 2, 4, 8 seconds
            logger.debug("retrying_callback", wait_time=wait_time)
            time.sleep(wait_time)
```

### 5.11 예외 처리 (app/core/exceptions.py)

```python
"""
커스텀 예외 클래스
"""
from typing import Optional, Dict, Any


class InspectorException(Exception):
    """기본 예외 클래스"""
    
    def __init__(
        self,
        message: str,
        error_code: str = "internal_error",
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class GitCloneError(InspectorException):
    """Git clone 실패"""
    
    def __init__(self, message: str, **kwargs):
        kwargs.setdefault("error_code", "git_clone_error")
        kwargs.setdefault("status_code", 400)
        super().__init__(message, **kwargs)


class ClaudeCLIError(InspectorException):
    """Claude CLI 실행 실패"""
    
    def __init__(self, message: str, **kwargs):
        kwargs.setdefault("error_code", "claude_cli_error")
        kwargs.setdefault("status_code", 500)
        super().__init__(message, **kwargs)


class RuleLoadError(InspectorException):
    """규칙 로드 실패"""
    
    def __init__(self, message: str, **kwargs):
        kwargs.setdefault("error_code", "rule_load_error")
        kwargs.setdefault("status_code", 500)
        super().__init__(message, **kwargs)


class CallbackError(InspectorException):
    """콜백 전송 실패"""
    
    def __init__(self, message: str, **kwargs):
        kwargs.setdefault("error_code", "callback_error")
        kwargs.setdefault("status_code", 500)
        super().__init__(message, **kwargs)
```

### 5.12 로깅 설정 (app/core/logger.py)

```python
"""
구조화된 로깅 설정
"""
import logging
import sys
import structlog
from pathlib import Path

from app.config import settings


def setup_logging():
    """로깅 시스템 초기화"""
    
    # 로그 디렉토리 생성
    settings.log_dir.mkdir(parents=True, exist_ok=True)
    
    # structlog 설정
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer() if not settings.debug 
            else structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelName(settings.log_level)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # 표준 로깅 설정
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.log_level),
    )
```

### 5.13 보안 (app/core/security.py)

```python
"""
API 보안 및 인증
"""
from fastapi import Header, HTTPException, status
from typing import Optional
import structlog

from app.config import settings

logger = structlog.get_logger()


async def verify_api_key(
    x_api_key: Optional[str] = Header(None, alias=settings.api_key_header)
) -> str:
    """
    API 키 검증
    
    Args:
        x_api_key: 헤더의 API 키
    
    Returns:
        검증된 API 키
    
    Raises:
        HTTPException: 인증 실패
    """
    # API 키 검증이 비활성화된 경우
    if not settings.api_keys:
        return "not_required"
    
    # API 키가 없는 경우
    if not x_api_key:
        logger.warning("api_key_missing")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key is required",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    # API 키 검증
    if x_api_key not in settings.api_keys:
        logger.warning("api_key_invalid", key_prefix=x_api_key[:8])
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key",
        )
    
    logger.debug("api_key_validated", key_prefix=x_api_key[:8])
    return x_api_key
```

---

## 6. Docker 환경 구성

### 6.1 Dockerfile (Web/API)

```dockerfile
# Dockerfile.web
FROM python:3.11.7-slim

# 메타데이터
LABEL maintainer="Code Quality Inspector Team"
LABEL version="1.0.0"
LABEL description="Code Quality Inspector - Web API"

# 환경 변수
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive

# 작업 디렉토리
WORKDIR /app

# 시스템 패키지 설치
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    ca-certificates \
    build-essential \
    libssl-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Claude CLI 설치
# 주의: 실제 설치 방법은 Claude 공식 문서 확인 필요
# 아래는 예시입니다
COPY scripts/install_claude.sh /tmp/
RUN chmod +x /tmp/install_claude.sh && \
    /tmp/install_claude.sh && \
    rm /tmp/install_claude.sh

# Claude CLI 설치 확인
RUN claude --version || echo "Claude CLI 설치 확인 필요"

# Python 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY app/ ./app/
COPY rules/ ./rules/
COPY scripts/ ./scripts/

# 로그 및 임시 디렉토리 생성
RUN mkdir -p /app/logs /tmp/code-inspection && \
    chmod 777 /tmp/code-inspection

# 헬스체크
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health', timeout=5)" || exit 1

# 포트 노출
EXPOSE 8000

# 실행 명령
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
```

### 6.2 Dockerfile (Worker)

```dockerfile
# Dockerfile.worker
FROM python:3.11.7-slim

# 메타데이터
LABEL maintainer="Code Quality Inspector Team"
LABEL version="1.0.0"
LABEL description="Code Quality Inspector - Celery Worker"

# 환경 변수
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive \
    C_FORCE_ROOT=true

# 작업 디렉토리
WORKDIR /app

# 시스템 패키지 설치
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    ca-certificates \
    build-essential \
    libssl-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Claude CLI 설치
COPY scripts/install_claude.sh /tmp/
RUN chmod +x /tmp/install_claude.sh && \
    /tmp/install_claude.sh && \
    rm /tmp/install_claude.sh

# Claude CLI 설치 확인
RUN claude --version || echo "Claude CLI 설치 확인 필요"

# Python 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY app/ ./app/
COPY rules/ ./rules/
COPY scripts/ ./scripts/

# 로그 및 임시 디렉토리 생성
RUN mkdir -p /app/logs /tmp/code-inspection && \
    chmod 777 /tmp/code-inspection

# 헬스체크 (Celery inspect)
HEALTHCHECK --interval=60s --timeout=10s --start-period=60s --retries=3 \
    CMD celery -A app.core.celery_app inspect ping -d celery@$HOSTNAME || exit 1

# 실행 명령
CMD ["celery", "-A", "app.core.celery_app", "worker", \
     "--loglevel=info", \
     "--concurrency=5", \
     "--max-tasks-per-child=50"]
```

### 6.3 docker-compose.yml

```yaml
version: '3.8'

services:
  redis:
    image: redis:7.2-alpine
    container_name: inspector-redis
    restart: unless-stopped
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: >
      redis-server
      --appendonly yes
      --appendfsync everysec
      --maxmemory 512mb
      --maxmemory-policy allkeys-lru
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - inspector-network

  web:
    build:
      context: .
      dockerfile: Dockerfile.web
    container_name: inspector-web
    restart: unless-stopped
    ports:
      - "8000:8000"
    environment:
      - DEBUG=false
      - LOG_LEVEL=INFO
      - CELERY_BROKER_URL=redis://redis:6379/0
      - CELERY_RESULT_BACKEND=redis://redis:6379/0
      - REDIS_HOST=redis
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - API_KEYS=${API_KEYS}
    volumes:
      - ./rules:/app/rules:ro
      - logs_data:/app/logs
      - temp_data:/tmp/code-inspection
    depends_on:
      redis:
        condition: service_healthy
    networks:
      - inspector-network

  worker:
    build:
      context: .
      dockerfile: Dockerfile.worker
    restart: unless-stopped
    deploy:
      replicas: 5
    environment:
      - DEBUG=false
      - LOG_LEVEL=INFO
      - CELERY_BROKER_URL=redis://redis:6379/0
      - CELERY_RESULT_BACKEND=redis://redis:6379/0
      - REDIS_HOST=redis
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - GIT_CLONE_TIMEOUT=300
      - CLAUDE_TIMEOUT=600
    volumes:
      - ./rules:/app/rules:ro
      - logs_data:/app/logs
      - temp_data:/tmp/code-inspection
    depends_on:
      redis:
        condition: service_healthy
    networks:
      - inspector-network

  flower:
    image: mher/flower:2.0.1
    container_name: inspector-flower
    restart: unless-stopped
    ports:
      - "5555:5555"
    environment:
      - CELERY_BROKER_URL=redis://redis:6379/0
      - CELERY_RESULT_BACKEND=redis://redis:6379/0
      - FLOWER_PORT=5555
    depends_on:
      - redis
      - worker
    networks:
      - inspector-network

volumes:
  redis_data:
    driver: local
  logs_data:
    driver: local
  temp_data:
    driver: local

networks:
  inspector-network:
    driver: bridge
```

### 6.4 Claude CLI 설치 스크립트 (scripts/install_claude.sh)

```bash
#!/bin/bash
set -e

echo "Installing Claude CLI..."

# 방법 1: 공식 설치 스크립트 (URL 확인 필요)
# curl -fsSL https://claude.ai/install.sh | bash

# 방법 2: pip 설치 (존재할 경우)
# pip install claude-cli

# 방법 3: 바이너리 다운로드 (예시)
CLAUDE_VERSION="1.0.0"  # 실제 버전으로 변경
ARCH="$(uname -m)"

if [ "$ARCH" = "x86_64" ]; then
    ARCH="amd64"
elif [ "$ARCH" = "aarch64" ]; then
    ARCH="arm64"
fi

# 임시: Claude CLI가 아직 공개되지 않았으므로 mock 생성
# 실제 구현 시 아래 부분을 실제 설치 명령으로 교체
cat > /usr/local/bin/claude << 'EOF'
#!/bin/bash
# Mock Claude CLI for testing
# TODO: Replace with actual Claude CLI

if [ "$1" = "--version" ]; then
    echo "claude version 1.0.0 (mock)"
    exit 0
fi

if [ "$1" = "--model" ]; then
    shift 2
fi

if [ "$1" = "--max-tokens" ]; then
    shift 2
fi

if [ "$1" = "--message" ]; then
    MESSAGE="$2"
    # Mock response
    cat << RESPONSE
{
  "score": 75,
  "summary": "Mock inspection result",
  "issues": [],
  "recommendations": [],
  "metrics": {
    "files_analyzed": 10,
    "critical_issues": 0,
    "high_issues": 2,
    "medium_issues": 5,
    "low_issues": 3
  }
}
RESPONSE
    exit 0
fi

echo "Usage: claude [options]"
exit 1
EOF

chmod +x /usr/local/bin/claude

echo "Claude CLI installed successfully"
claude --version
```

### 6.5 환경 변수 (.env.example)

```env
# Application
DEBUG=false
LOG_LEVEL=INFO
APP_NAME=Code Quality Inspector

# FastAPI
API_HOST=0.0.0.0
API_PORT=8000
API_PREFIX=/api

# Celery
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0
CELERY_TASK_TIMEOUT=900
CELERY_MAX_RETRIES=3
CELERY_WORKER_CONCURRENCY=5

# Redis
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=

# Git
GIT_CLONE_TIMEOUT=300
GIT_CLONE_DEPTH=1

# Claude CLI
ANTHROPIC_API_KEY=sk-ant-xxxxx
CLAUDE_MODEL=claude-3-opus-20240229
CLAUDE_MAX_TOKENS=4096
CLAUDE_TIMEOUT=600

# Security
API_KEYS=key1,key2,key3

# Callback
CALLBACK_TIMEOUT=30
CALLBACK_MAX_RETRIES=3

# Directories
WORK_DIR=/tmp/code-inspection
RULES_DIR=/app/rules
LOG_DIR=/app/logs
```

---

## 7. 환경 변수 및 설정

### 7.1 필수 환경 변수

| 변수명 | 필수 | 기본값 | 설명 |
|--------|------|--------|------|
| `ANTHROPIC_API_KEY` | ✅ | - | Claude API 인증 키 |
| `CELERY_BROKER_URL` | ✅ | redis://redis:6379/0 | Celery 브로커 URL |

### 7.2 선택 환경 변수

| 변수명 | 기본값 | 설명 |
|--------|--------|------|
| `DEBUG` | false | 디버그 모드 |
| `LOG_LEVEL` | INFO | 로그 레벨 (DEBUG/INFO/WARNING/ERROR) |
| `API_KEYS` | [] | 허용된 API 키 목록 (쉼표 구분) |
| `CELERY_WORKER_CONCURRENCY` | 5 | Worker 동시 작업 수 |
| `GIT_CLONE_TIMEOUT` | 300 | Git clone 타임아웃 (초) |
| `CLAUDE_TIMEOUT` | 600 | Claude CLI 타임아웃 (초) |

---

## 8. 에러 처리 및 예외 상황

### 8.1 예외 상황 및 대응

| 예외 상황 | 에러 코드 | 대응 방안 |
|-----------|-----------|-----------|
| GitHub 저장소 없음 | `repository_not_found` | 사용자에게 URL 확인 요청 |
| Private 저장소 접근 실패 | `authentication_error` | 인증 토큰 설정 안내 |
| Git clone 타임아웃 | `clone_timeout` | 타임아웃 증가 또는 저장소 크기 확인 |
| 네트워크 오류 | `network_error` | 재시도 또는 연결 확인 |
| Claude API 키 오류 | `authentication_error` | API 키 확인 및 재설정 |
| Claude API rate limit | `rate_limit_error` | 대기 후 재시도 또는 요금제 업그레이드 |
| Claude CLI 타임아웃 | `cli_timeout` | 타임아웃 증가 또는 코드 규모 축소 |
| Claude CLI 없음 | `cli_not_found` | Docker 이미지 재빌드 |
| 심사 규칙 파일 없음 | `file_not_found` | 규칙 파일 확인 및 추가 |
| JSON 파싱 실패 | `json_parse_error` | Claude 프롬프트 개선 |
| 콜백 URL 오류 | `callback_error` | 콜백 URL 확인 및 재시도 |
| 디스크 공간 부족 | `disk_full` | 임시 파일 정리 또는 볼륨 확장 |
| 메모리 부족 | `out_of_memory` | Worker 수 감소 또는 메모리 증설 |
| Redis 연결 실패 | `redis_connection_error` | Redis 서비스 상태 확인 |

### 8.2 재시도 전략

```python
# Celery 작업 재시도 설정
@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,  # 60초 대기
    retry_backoff=True,  # Exponential backoff
    retry_backoff_max=600,  # 최대 10분
    retry_jitter=True,  # Jitter 추가
)
```

### 8.3 타임아웃 설정

```
Git Clone: 5분
Claude CLI: 10분
전체 작업: 15분
콜백 전송: 30초
```

---

## 9. 보안 및 인증

### 9.1 API 인증

```bash
# 요청 예시
curl -X POST http://localhost:8000/api/inspect \
  -H "X-API-Key: your-api-key-here" \
  -H "Content-Type: application/json" \
  -d '{
    "github_url": "https://github.com/user/repo",
    "branch": "main",
    "callback_url": "https://api.example.com/callback"
  }'
```

### 9.2 보안 체크리스트

- ✅ API 키 인증
- ✅ HTTPS 사용 (프로덕션)
- ✅ 임시 파일 자동 삭제
- ✅ API 키 환경 변수 저장
- ✅ 로그에 민감 정보 제외
- ✅ Rate limiting (TODO)
- ✅ CORS 설정 (프로덕션에서 제한)
- ✅ Input validation

### 9.3 민감 정보 관리

```yaml
# Docker Compose에서 secrets 사용
services:
  web:
    secrets:
      - anthropic_api_key
      - api_keys

secrets:
  anthropic_api_key:
    file: ./secrets/anthropic_api_key.txt
  api_keys:
    file: ./secrets/api_keys.txt
```

---

## 10. 테스트 전략

### 10.1 테스트 구조

```
tests/
├── unit/
│   ├── test_git_service.py
│   ├── test_inspector.py
│   ├── test_rule_loader.py
│   └── test_callbacks.py
├── integration/
│   ├── test_api_endpoints.py
│   ├── test_celery_tasks.py
│   └── test_end_to_end.py
└── conftest.py
```

### 10.2 테스트 실행

```bash
# 전체 테스트
pytest

# 커버리지 포함
pytest --cov=app --cov-report=html

# 특정 테스트만
pytest tests/unit/test_git_service.py

# 마커 기반 실행
pytest -m "not slow"
```

### 10.3 Mock 사용

```python
# tests/conftest.py
import pytest
from unittest.mock import Mock, patch

@pytest.fixture
def mock_claude_cli():
    """Claude CLI Mock"""
    with patch('subprocess.run') as mock_run:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = '{"score": 85, ...}'
        yield mock_run

@pytest.fixture
def mock_git_clone():
    """Git Clone Mock"""
    with patch('git.Repo.clone_from') as mock_clone:
        yield mock_clone
```

---

## 11. 모니터링 및 로깅

### 11.1 로그 구조

```json
{
  "timestamp": "2025-01-18T12:00:00.000Z",
  "level": "info",
  "event": "inspection_started",
  "task_id": "abc-123",
  "github_url": "https://github.com/user/repo",
  "branch": "main"
}
```

### 11.2 메트릭 수집

```
- 작업 완료율
- 평균 처리 시간
- 에러 발생률
- API 응답 시간
- Worker 활용률
- Redis 메모리 사용량
```

### 11.3 Flower 대시보드

```
http://localhost:5555

- 실시간 작업 모니터링
- Worker 상태
- 작업 히스토리
- 실패 작업 재시도
```

---

## 12. 배포 및 운영

### 12.1 배포 명령

```bash
# 1. 환경 변수 설정
cp .env.example .env
vi .env  # ANTHROPIC_API_KEY 설정

# 2. Docker Compose 실행
docker-compose up -d

# 3. 로그 확인
docker-compose logs -f

# 4. 상태 확인
curl http://localhost:8000/health
```

### 12.2 스케일링

```bash
# Worker 수 증가
docker-compose up -d --scale worker=10

# Worker 수 감소
docker-compose up -d --scale worker=3
```

### 12.3 백업 및 복구

```bash
# Redis 백업
docker exec inspector-redis redis-cli BGSAVE

# 로그 백업
tar -czf logs_backup_$(date +%Y%m%d).tar.gz logs/
```

### 12.4 프로덕션 체크리스트

- ✅ ANTHROPIC_API_KEY 설정
- ✅ API_KEYS 설정
- ✅ DEBUG=false
- ✅ HTTPS 설정 (Nginx 등)
- ✅ 로그 로테이션 설정
- ✅ 디스크 모니터링 알림
- ✅ 헬스체크 엔드포인트 확인
- ✅ 백업 스케줄 설정

---

## 부록 A: 심사 규칙 예시 (rules/quality_rules.md)

```markdown
# 코드 품질 검사 규칙

## 1. 코드 구조 (25점)
- 모듈화와 관심사의 분리
- 적절한 디렉토리 구조
- 파일 크기 및 함수 길이
- 순환 의존성 부재

## 2. 코드 스타일 (15점)
- 일관된 네이밍 컨벤션
- 코드 포매팅 (PEP8, ESLint 등)
- 주석 및 문서화
- 불필요한 코드 제거

## 3. 에러 처리 (20점)
- 적절한 예외 처리
- 에러 로깅
- Fail-fast 원칙
- Recovery 메커니즘

## 4. 테스트 (20점)
- 단위 테스트 존재
- 테스트 커버리지 (70% 이상 권장)
- 통합 테스트
- E2E 테스트

## 5. 보안 (20점)
- 입력 검증
- SQL Injection 방어
- XSS 방어
- 민감 정보 하드코딩 금지
- 의존성 취약점 확인
```

---

## 부록 B: API 사용 예시

### 검사 요청

```bash
curl -X POST http://localhost:8000/api/inspect \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "github_url": "https://github.com/user/repo",
    "branch": "main",
    "callback_url": "https://api.example.com/webhook",
    "rules_files": ["quality_rules.md", "security_rules.md"],
    "metadata": {"project_id": "123"}
  }'
```

### 상태 조회

```bash
curl -X GET http://localhost:8000/api/status/abc-123 \
  -H "X-API-Key: your-key"
```

### 콜백 수신 예시

```json
{
  "task_id": "abc-123",
  "status": "success",
  "github_url": "https://github.com/user/repo",
  "branch": "main",
  "result": {
    "score": 85,
    "summary": "전반적으로 양호한 코드 품질...",
    "issues": [
      {
        "severity": "high",
        "category": "보안",
        "file": "src/auth.py",
        "line": 42,
        "description": "하드코딩된 비밀번호 발견",
        "recommendation": "환경 변수 사용 권장"
      }
    ],
    "recommendations": [...],
    "metrics": {
      "files_analyzed": 45,
      "critical_issues": 0,
      "high_issues": 3,
      "medium_issues": 8,
      "low_issues": 12
    }
  },
  "metadata": {"project_id": "123"},
  "completed_at": "2025-01-18T12:05:30Z"
}
```

---

## 부록 C: 트러블슈팅

### Claude CLI 설치 실패

```bash
# 수동 설치 확인
docker exec -it inspector-web bash
which claude
claude --version

# 재설치
cd /tmp
bash /app/scripts/install_claude.sh
```

### Redis 연결 실패

```bash
# Redis 상태 확인
docker-compose ps redis
docker-compose logs redis

# Redis 재시작
docker-compose restart redis
```

### Worker가 작업을 처리하지 않음

```bash
# Worker 로그 확인
docker-compose logs worker

# Celery inspect
docker exec -it inspector-worker-1 celery -A app.core.celery_app inspect active

# Worker 재시작
docker-compose restart worker
```

### 디스크 공간 부족

```bash
# 임시 파일 정리
docker exec -it inspector-worker-1 rm -rf /tmp/code-inspection/*

# Docker 볼륨 정리
docker volume prune
```

---

## 결론

이 PRD는 Python + FastAPI + Celery 기반 코드품질 검사기 서비스의 완전한 구현 명세입니다. 
AI 개발 에이전트는 이 문서만으로 전체 시스템을 구현할 수 있으며, 모든 예외 상황과 
엣지 케이스가 고려되어 있습니다.

### 구현 순서 권장
1. 기본 FastAPI 서버 및 API (5.2, 5.3, 5.4)
2. Celery 설정 및 작업 (5.5, 5.6)
3. Git 서비스 (5.7)
4. Inspector 서비스 (5.8)
5. 예외 처리 및 로깅 (5.11, 5.12)
6. Docker 환경 (6.1-6.5)
7. 테스트 작성 (10장)
8. 배포 및 모니터링 (11-12장)

