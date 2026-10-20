"""应用配置：全部来自环境变量，默认值只用于本地开发。"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "enterprise-rag"
    app_title: str = "知策 · 政策知识问答助手"
    app_env: Literal["dev", "test", "prod"] = "dev"
    log_level: str = "INFO"
    log_dir: Path = Path("logs")

    jwt_secret: str = "dev-change-me-to-a-long-random-string"
    jwt_expire_minutes: int = 720
    admin_username: str = "admin"
    admin_password: str = "admin123456"
    seed_admin: bool = True

    database_url: str = "mysql+pymysql://rag:rag@127.0.0.1:3306/enterprise_rag?charset=utf8mb4"
    auto_create_tables: bool = True

    milvus_uri: str = "http://127.0.0.1:19530"
    milvus_token: str = ""
    milvus_collection: str = "kb_chunks"

    embedding_provider: Literal["bge_m3", "hash"] = "bge_m3"
    embedding_model: str = "BAAI/bge-m3"
    embedding_device: str = "auto"
    embedding_dim: int = 1024
    embedding_batch_size: int = 8
    embedding_max_length: int = 1024
    embedding_cache_dir: Path = Path("data/models")
    embedding_preload: bool = True

    llm_provider: Literal["deepseek", "mock"] = "deepseek"
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-flash"
    deepseek_thinking: Literal["enabled", "disabled"] = "disabled"
    llm_timeout_s: float = 120.0

    top_k: int = Field(default=5, ge=1, le=50)
    default_temperature: float = Field(default=0.7, ge=0, le=2)
    default_top_p: float = Field(default=0.8, gt=0, le=1)
    default_max_tokens: int = Field(default=2048, ge=128, le=8192)
    default_history_rounds: int = Field(default=5, ge=0, le=20)
    max_history_rounds: int = Field(default=20, ge=0, le=50)
    history_max_chars: int = Field(default=6000, ge=500, le=50000)

    max_upload_mb: int = Field(default=50, ge=1, le=500)
    upload_dir: Path = Path("data/uploads")
    captcha_ttl_seconds: int = Field(default=300, ge=30, le=1800)
    cors_origins: str = "http://127.0.0.1:5174,http://localhost:5174"

    enable_worker: bool = True
    expose_captcha_code: bool = False


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
