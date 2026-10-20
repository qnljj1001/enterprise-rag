"""系统接口：健康检查与元信息。"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Request
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..config import Settings
from ..ingest.parsers import SUPPORTED_EXTENSIONS
from ..schemas import HealthOut, MetaOut
from .deps import get_db, get_settings

logger = logging.getLogger(__name__)
router = APIRouter(tags=["系统"])

TOP_P_NOTE = (
    "DeepSeek 官方文档说明：非思考模式下 top_p 固定为 1.0，传入值会被忽略；"
    "当前固定使用 deepseek-flash 非思考模式，温度参数生效。"
)


@router.get("/health", response_model=HealthOut)
def health(
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> HealthOut:
    db_status = "ok"
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        logger.exception("数据库健康检查失败")
        db_status = "error"
    vector_store = getattr(request.app.state, "vector_store", None)
    milvus_status = "ok" if getattr(vector_store, "available", False) else "unavailable"
    llm_status = (
        "mock"
        if settings.llm_provider == "mock"
        else ("configured" if settings.deepseek_api_key else "unconfigured")
    )
    return HealthOut(
        status="ok" if db_status == "ok" else "degraded",
        db=db_status,
        milvus=milvus_status,
        llm=llm_status,
        embedding=settings.embedding_provider,
    )


@router.get("/api/v1/meta", response_model=MetaOut)
def meta(settings: Settings = Depends(get_settings)) -> MetaOut:
    return MetaOut(
        app_title=settings.app_title,
        llm_model=settings.deepseek_model,
        llm_thinking=settings.deepseek_thinking,
        embedding_model=settings.embedding_model,
        embedding_dim=settings.embedding_dim,
        retrieval_modes=["dense", "hybrid"],
        upload_types=sorted(set(SUPPORTED_EXTENSIONS.keys())),
        max_upload_mb=settings.max_upload_mb,
        top_p_note=TOP_P_NOTE,
    )
