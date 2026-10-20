"""FastAPI 入口。"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .api import auth, chat, documents, knowledge_bases, system, wiki
from .config import Settings, get_settings
from .db import Database
from .infra.embedder import build_embedder
from .infra.llm import build_llm
from .infra.milvus import build_vector_store
from .logging_config import request_id_var, setup_logging
from .models import User
from .security import hash_password
from .services.worker import IngestWorker

logger = logging.getLogger(__name__)


def seed_admin(db: Database, settings: Settings) -> None:
    if not settings.seed_admin or not settings.admin_username:
        return
    if len(settings.admin_password or "") < 8:
        logger.warning("ADMIN_PASSWORD 少于 8 位，跳过管理员种子创建")
        return
    session = db.SessionLocal()
    try:
        existing = session.query(User).filter(User.username == settings.admin_username).first()
        if existing is None:
            session.add(
                User(
                    username=settings.admin_username,
                    password_hash=hash_password(settings.admin_password),
                    role="admin",
                    is_active=True,
                )
            )
            session.commit()
            logger.info("已创建管理员账号：%s", settings.admin_username)
        else:
            logger.info("管理员账号已存在：%s", settings.admin_username)
    finally:
        session.close()


def create_app(
    settings: Settings | None = None,
    *,
    vector_store=None,
    embedder=None,
    llm=None,
    start_worker: bool | None = None,
) -> FastAPI:
    settings = settings or get_settings()
    if settings.app_env == "prod" and settings.jwt_secret.startswith("dev-change-me"):
        raise RuntimeError("生产环境必须设置独立的 JWT_SECRET")
    if settings.app_env == "prod" and settings.admin_password == "admin123456":
        logger.warning("生产环境仍在使用默认管理员密码，请尽快修改 ADMIN_PASSWORD")
    setup_logging(settings)

    db = Database(settings.database_url)
    vector_store = vector_store or build_vector_store(settings)
    embedder = embedder or build_embedder(settings)
    llm = llm or build_llm(settings)
    worker_enabled = settings.enable_worker if start_worker is None else start_worker
    worker = (
        IngestWorker(settings, db.SessionLocal, vector_store, embedder) if worker_enabled else None
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if settings.auto_create_tables:
            db.create_all()
        seed_admin(db, settings)
        try:
            vector_store.ensure_collection()
        except Exception:
            logger.exception("向量库初始化失败，服务继续启动")
        if worker is not None:
            worker.reset_stale()
            worker.start()
        if settings.embedding_preload and settings.embedding_provider != "hash":
            threading.Thread(target=embedder.preload, name="embedder-preload", daemon=True).start()
        yield
        if worker is not None:
            worker.stop()
        db.dispose()

    app = FastAPI(
        title=settings.app_title,
        version="0.1.0",
        description="MySQL + Milvus + bge-m3 + DeepSeek 的企业/政策知识问答系统。",
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.db = db
    app.state.vector_store = vector_store
    app.state.embedder = embedder
    app.state.llm = llm
    app.state.worker = worker

    origins = [item.strip() for item in settings.cors_origins.split(",") if item.strip()]
    if origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or f"req_{uuid.uuid4().hex[:16]}"
        request.state.request_id = request_id
        token = request_id_var.set(request_id)
        started = time.perf_counter()
        try:
            response = await call_next(request)
            elapsed = (time.perf_counter() - started) * 1000
            response.headers["X-Request-ID"] = request_id
            logger.info(
                "%s %s -> %s %.1fms",
                request.method,
                request.url.path,
                response.status_code,
                elapsed,
                extra={"request_id": request_id},
            )
            return response
        finally:
            request_id_var.reset(token)

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError):
        errors = [
            {
                "loc": list(item.get("loc", [])),
                "msg": str(item.get("msg", "")),
                "type": item.get("type"),
            }
            for item in exc.errors()
        ]
        return JSONResponse(
            status_code=422,
            content={
                "detail": {
                    "code": "VALIDATION_FAILED",
                    "message": "参数校验失败，请检查输入。",
                    "errors": errors,
                    "request_id": getattr(request.state, "request_id", None),
                }
            },
        )

    @app.get("/", tags=["系统"])
    def root() -> dict[str, str]:
        return {
            "app": settings.app_name,
            "title": settings.app_title,
            "docs": "/docs",
            "health": "/health",
        }

    app.include_router(system.router)
    app.include_router(auth.router)
    app.include_router(knowledge_bases.router)
    app.include_router(knowledge_bases.admin_router)
    app.include_router(documents.router)
    app.include_router(wiki.router)
    app.include_router(chat.router)
    return app


app = create_app()
