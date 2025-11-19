# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 프로젝트 개요

**Code Quality Inspector**는 Claude AI 또는 OpenAI Codex를 사용하여 GitHub 저장소를 자동으로 분석하고 품질 리포트를 제공하는 비동기 코드 검사 서비스입니다.

### 기술 스택
- **Web Framework**: FastAPI (비동기 REST API)
- **Task Queue**: Celery + Redis (백그라운드 작업 처리)
- **AI Providers**: Claude CLI 또는 Codex CLI (SOLID 원칙 기반 멀티 프로바이더 지원)
- **배포**: Docker Compose

## 핵심 아키텍처

### 처리 흐름
```
Client Request → FastAPI (/api/inspect)
    ↓
  Redis (Task Queue)
    ↓
  Celery Worker (비동기 처리)
    ↓
  1. Git Clone (GitService)
  2. Rules Load (RuleLoader)
  3. AI CLI Inspection (BaseInspector 구현체)
  4. Callback Delivery (CallbackService)
```

### SOLID 원칙 기반 AI Provider 패턴

**app/services/inspector.py**는 Factory Pattern과 Strategy Pattern을 결합하여 여러 AI 프로바이더를 지원합니다:

- `BaseInspector`: 추상 기본 클래스 (템플릿 메서드 패턴)
  - `ClaudeInspector`: Claude CLI 구현체
  - `CodexInspector`: Codex CLI 구현체
- `InspectorFactory`: 프로바이더별 인스턴스 생성

새로운 AI 프로바이더 추가 시:
1. `BaseInspector`를 상속한 클래스 생성
2. 추상 메서드 구현 (`get_cli_path`, `get_api_key`, `build_cli_command`, `get_env_vars`)
3. `InspectorFactory.create_inspector()`에 분기 추가
4. `app/config.py`에 설정 추가

### 주요 컴포넌트

- **app/api/routes.py**: `/api/inspect`, `/api/status/{task_id}` 엔드포인트
- **app/tasks/inspection.py**: `inspect_code_task` - 메인 Celery 작업 (재시도 로직 포함)
- **app/services/git_service.py**: Git clone 및 저장소 정보 추출
- **app/services/inspector.py**: AI CLI 실행 및 결과 파싱
- **app/services/rule_loader.py**: `rules/` 디렉토리에서 Markdown 규칙 로드
- **app/tasks/callbacks.py**: 검사 완료 후 webhook 콜백 전송

### 예외 처리 계층

**app/core/exceptions.py**에 정의된 커스텀 예외:
- `GitCloneException`: Git clone 실패 (재시도 가능)
- `RuleLoadException`: 규칙 파일 로드 실패 (재시도 불가)
- `APIKeyMissingException`: API 키 누락 (재시도 불가)
- `AICliException`: AI CLI 실행 실패 (재시도 가능)
- `CallbackException`: 콜백 전송 실패

`inspect_code_task`는 예외 유형에 따라 재시도 여부를 결정합니다.

## 개발 환경 설정

### 필수 도구
- Docker & Docker Compose
- Python 3.11+
- Anthropic API Key 또는 OpenAI API Key

### 환경 변수 설정
```bash
cp .env.example .env
# .env 편집하여 API 키 설정:
# - ANTHROPIC_API_KEY: Claude 사용 시 필수
# - OPENAI_API_KEY: Codex 사용 시 필수
# - DEFAULT_AI_PROVIDER: "claude" 또는 "codex"
# - API_KEYS: JSON 배열 형식의 API 키 리스트
```

### Docker Compose로 실행

```bash
# 서비스 시작
docker-compose up -d

# 로그 확인
docker-compose logs -f web      # FastAPI 서버 로그
docker-compose logs -f worker   # Celery worker 로그
docker-compose logs -f redis    # Redis 로그

# Worker 스케일링
docker-compose up -d --scale worker=5

# 서비스 중지
docker-compose down

# 볼륨까지 완전 삭제
docker-compose down -v
```

### 로컬 개발 (Docker 없이)

```bash
# 의존성 설치
pip install -r requirements-dev.txt

# Redis 실행 (별도 터미널)
redis-server

# Celery worker 실행 (별도 터미널)
celery -A app.core.celery_app worker --loglevel=info --concurrency=5

# FastAPI 서버 실행 (auto-reload)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 테스트

### 테스트 실행
```bash
# 전체 테스트
pytest

# 커버리지 포함
pytest --cov=app --cov-report=html --cov-report=term-missing

# 특정 테스트 파일
pytest tests/test_validators.py

# 마커별 실행
pytest -m unit           # 단위 테스트만
pytest -m integration    # 통합 테스트만
pytest -m "not slow"     # 느린 테스트 제외
```

### 테스트 구조
- `pytest.ini`: pytest 설정 (markers, coverage 옵션)
- `tests/test_validators.py`: 보안 검증 테스트 (GitHub URL, 브랜치명)

## 코드 품질 도구

```bash
# Black 포맷팅
black app/ tests/

# Flake8 린팅
flake8 app/ tests/

# isort import 정렬
isort app/ tests/

# mypy 타입 체크
mypy app/
```

## API 사용법

### 검사 요청
```bash
curl -X POST http://localhost:8000/api/inspect \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "github_url": "https://github.com/user/repo",
    "branch": "main",
    "callback_url": "https://your-server.com/webhook",
    "rules_files": ["quality_rules.md", "security_rules.md"],
    "ai_provider": "codex",
    "metadata": {"project_id": "123"}
  }'
```

### 상태 확인
```bash
curl http://localhost:8000/api/status/{task_id} \
  -H "X-API-Key: your-api-key"
```

### 헬스체크
```bash
curl http://localhost:8000/health
```

## 모니터링

### Flower 대시보드
- URL: `http://localhost:5555`
- Celery 작업 상태, 워커 모니터링, 작업 히스토리 확인

### 로그 위치
- Docker: `docker-compose logs -f [service]`
- 로컬: `logs/inspector.log` (structlog JSON 형식)

## 심사 규칙 커스터마이징

`rules/` 디렉토리의 Markdown 파일을 편집하거나 새 규칙 추가:
- `quality_rules.md`: 코드 구조, 네이밍, 복잡도
- `security_rules.md`: OWASP Top 10, 보안 코딩
- `performance_rules.md`: 알고리즘 효율성, 최적화

규칙 파일은 RuleLoader에 의해 로드되어 AI CLI 프롬프트에 포함됩니다.

## 보안 고려사항

- **GitHub URL 검증**: `app/core/validators.py`에서 URL 형식 및 브랜치명 보안 검증
- **API 키 인증**: `X-API-Key` 헤더 기반 인증 (`.env`의 `API_KEYS` 설정)
- **임시 디렉토리 정리**: 작업 완료 후 자동 삭제, 24시간 이상 된 디렉토리 정리
- **CORS 설정**: 프로덕션에서는 `app/main.py`의 `allow_origins` 제한 필요

## 문제 해결

### AI CLI not found
- `scripts/install_ai_cli.sh` 확인
- Docker 이미지 재빌드: `docker-compose build`
- CLI 경로 확인: `.env`의 `CLAUDE_CLI_PATH` 또는 `CODEX_CLI_PATH`

### Worker가 작업을 처리하지 않음
1. Redis 연결: `docker-compose logs redis`
2. Worker 로그: `docker-compose logs worker`
3. Flower 확인: `http://localhost:5555`
4. Celery 설정 확인: `app/core/celery_app.py`

### 콜백 전송 실패
- 콜백 URL이 Docker 네트워크에서 접근 가능한지 확인
- 콜백 엔드포인트가 POST 요청을 수락하는지 확인
- `CALLBACK_TIMEOUT` 및 `CALLBACK_MAX_RETRIES` 조정

## Git Commit 규칙

Conventional Commits 형식 준수:
```
<type>(<scope>): <subject>

feat(inspector): add support for GPT-4 provider
fix(celery): resolve task retry timeout issue
docs(readme): update API usage examples
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`, `perf`
