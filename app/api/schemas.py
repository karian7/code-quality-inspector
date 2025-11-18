"""
API 요청/응답 스키마
"""
from pydantic import BaseModel, HttpUrl, Field, field_validator
from typing import Optional, Dict, Any, List
from datetime import datetime


class InspectionRequest(BaseModel):
    """코드 검사 요청"""

    github_url: HttpUrl = Field(
        ...,
        description="GitHub 저장소 URL",
        examples=["https://github.com/user/repo"],
    )
    branch: str = Field(
        default="main",
        description="검사할 브랜치 이름",
        examples=["main"],
        min_length=1,
        max_length=255,
    )
    callback_url: HttpUrl = Field(
        ...,
        description="결과를 전송할 콜백 URL",
        examples=["https://api.example.com/webhook/inspection"],
    )
    rules_files: List[str] = Field(
        default=["quality_rules.md"],
        description="사용할 심사 규칙 파일 목록",
        examples=[["quality_rules.md", "security_rules.md"]],
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="추가 메타데이터 (콜백 시 함께 전송됨)",
    )

    @field_validator("github_url")
    @classmethod
    def validate_github_url(cls, v):
        """GitHub URL 검증"""
        url_str = str(v)
        if "github.com" not in url_str:
            raise ValueError("Only GitHub URLs are supported")
        return v

    @field_validator("rules_files")
    @classmethod
    def validate_rules_files(cls, v):
        """규칙 파일 검증"""
        if not v:
            raise ValueError("At least one rule file must be specified")
        for file in v:
            if not file.endswith(".md"):
                raise ValueError(f"Rule file must be a .md file: {file}")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "github_url": "https://github.com/user/repo",
                "branch": "main",
                "callback_url": "https://api.example.com/webhook/inspection",
                "rules_files": ["quality_rules.md"],
                "metadata": {"project_id": "123", "user_id": "456"},
            }
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

    model_config = {
        "json_schema_extra": {
            "example": {
                "task_id": "abc123",
                "status": "success",
                "github_url": "https://github.com/user/repo",
                "branch": "main",
                "result": {
                    "score": 85,
                    "issues": [],
                    "summary": "Code quality is good",
                },
                "metadata": {"project_id": "123"},
                "completed_at": "2024-01-18T10:30:00Z",
            }
        }
    }
