"""
FastAPI 애플리케이션 진입점
"""
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import structlog
import shutil

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
    if not shutil.which(settings.claude_cli_path):
        logger.warning("claude_cli_not_found", path=settings.claude_cli_path)
        # 개발 환경에서는 경고만 출력
        if not settings.debug:
            raise RuntimeError(f"Claude CLI not found at {settings.claude_cli_path}")
    else:
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
        {"request": request, "app_name": settings.app_name, "version": settings.app_version}
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
