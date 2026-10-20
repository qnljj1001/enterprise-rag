"""API 请求/响应模型。"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class UserOut(ORMModel):
    id: str
    username: str
    role: str
    created_at: datetime
    last_login_at: datetime | None = None


class CaptchaOut(BaseModel):
    captcha_id: str
    image_base64: str
    expires_in: int
    debug_code: str | None = None


class RegisterIn(BaseModel):
    username: str = Field(min_length=3, max_length=32, pattern=r"^[A-Za-z0-9_\u4e00-\u9fff]+$")
    password: str = Field(min_length=8, max_length=128)
    confirm_password: str = Field(min_length=8, max_length=128)
    captcha_id: str
    captcha_code: str = Field(min_length=1, max_length=8)

    @model_validator(mode="after")
    def check_password(self) -> RegisterIn:
        if self.password != self.confirm_password:
            raise ValueError("两次输入的密码不一致")
        return self


class LoginIn(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)
    captcha_id: str
    captcha_code: str = Field(min_length=1, max_length=8)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserOut


RetrievalMode = Literal["dense", "hybrid"]


class KBCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str = Field(default="", max_length=500)
    default_chunk_size: int = Field(default=800, ge=100, le=4000)
    default_chunk_overlap: int = Field(default=120, ge=0, le=1000)
    retrieval_mode: RetrievalMode = "hybrid"

    @model_validator(mode="after")
    def check_overlap(self) -> KBCreate:
        if self.default_chunk_overlap >= self.default_chunk_size:
            raise ValueError("重叠大小必须小于切块大小")
        return self


class KBUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    default_chunk_size: int | None = Field(default=None, ge=100, le=4000)
    default_chunk_overlap: int | None = Field(default=None, ge=0, le=1000)
    retrieval_mode: RetrievalMode | None = None

    @model_validator(mode="after")
    def check_overlap(self) -> KBUpdate:
        if (
            self.default_chunk_size is not None
            and self.default_chunk_overlap is not None
            and self.default_chunk_overlap >= self.default_chunk_size
        ):
            raise ValueError("重叠大小必须小于切块大小")
        return self


class KBOut(ORMModel):
    id: str
    name: str
    description: str
    default_chunk_size: int
    default_chunk_overlap: int
    retrieval_mode: str
    embedding_model: str
    embedding_dim: int
    document_count: int = 0
    chunk_count: int = 0
    created_at: datetime
    updated_at: datetime


class DocumentOut(ORMModel):
    id: str
    kb_id: str
    filename: str
    file_type: str
    size_bytes: int
    chunk_size: int
    chunk_overlap: int
    status: str
    progress: int
    chunk_count: int
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime


class DocumentListOut(BaseModel):
    items: list[DocumentOut]
    total: int
    page: int
    page_size: int


class ChunkOut(ORMModel):
    id: str
    kb_id: str
    document_id: str
    chunk_index: int
    content: str
    char_start: int
    char_end: int
    page_no: int | None = None
    chunk_metadata: dict[str, Any] = Field(default_factory=dict)
    updated_at: datetime


class ChunkListOut(BaseModel):
    items: list[ChunkOut]
    total: int
    page: int
    page_size: int


class ChunkUpdateIn(BaseModel):
    content: str = Field(min_length=1, max_length=20000)


class ReparseIn(BaseModel):
    chunk_size: int | None = Field(default=None, ge=100, le=4000)
    chunk_overlap: int | None = Field(default=None, ge=0, le=1000)

    @model_validator(mode="after")
    def check_overlap(self) -> ReparseIn:
        if (
            self.chunk_size is not None
            and self.chunk_overlap is not None
            and self.chunk_overlap >= self.chunk_size
        ):
            raise ValueError("重叠大小必须小于切块大小")
        return self


class SessionCreateIn(BaseModel):
    title: str = Field(default="新对话", max_length=100)
    settings: dict[str, Any] = Field(default_factory=dict)


class SessionUpdateIn(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=100)


class SessionOut(ORMModel):
    id: str
    title: str
    settings: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class CitationOut(BaseModel):
    chunk_id: str
    document_id: str
    filename: str
    kb_name: str
    page_no: int | None = None
    content: str
    score: float


class MessageOut(ORMModel):
    id: str
    session_id: str
    role: str
    content: str
    citations: list[dict[str, Any]] = Field(default_factory=list)
    model: str
    params: dict[str, Any] = Field(default_factory=dict)
    status: str
    error_message: str | None = None
    created_at: datetime


class ChatRequestIn(BaseModel):
    content: str = Field(min_length=1, max_length=8000)
    kb_ids: list[str] = Field(min_length=1, max_length=20)
    temperature: float = Field(default=0.7, ge=0, le=2)
    top_p: float = Field(default=0.8, gt=0, le=1)
    max_tokens: int = Field(default=2048, ge=128, le=8192)
    history_rounds: int = Field(default=5, ge=0, le=20)


class WikiOut(BaseModel):
    title: str
    markdown: str
    generated_at: datetime


class MetaOut(BaseModel):
    app_title: str
    llm_model: str
    llm_thinking: str
    embedding_model: str
    embedding_dim: int
    retrieval_modes: list[str]
    upload_types: list[str]
    max_upload_mb: int
    top_p_note: str


class HealthOut(BaseModel):
    status: str
    db: str
    milvus: str
    llm: str
    embedding: str
