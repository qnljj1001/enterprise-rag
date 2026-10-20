"""API 依赖：数据库、配置、当前用户、管理员。"""

from __future__ import annotations

from collections.abc import Iterator

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from ..config import Settings
from ..models import User
from ..security import decode_access_token

bearer = HTTPBearer(auto_error=False)


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_db(request: Request) -> Iterator[Session]:
    db = request.app.state.db.SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=401,
            detail={"code": "UNAUTHORIZED", "message": "请先登录。"},
        )
    settings: Settings = request.app.state.settings
    try:
        payload = decode_access_token(credentials.credentials, settings)
    except ValueError as exc:
        raise HTTPException(
            status_code=401,
            detail={"code": "UNAUTHORIZED", "message": "登录已失效，请重新登录。"},
        ) from exc
    user = db.get(User, str(payload["sub"]))
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=401,
            detail={"code": "UNAUTHORIZED", "message": "账号不存在或已停用。"},
        )
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail={"code": "FORBIDDEN", "message": "需要管理员权限。"},
        )
    return user


def get_vector_store(request: Request):
    return request.app.state.vector_store


def get_embedder(request: Request):
    return request.app.state.embedder


def get_llm(request: Request):
    return request.app.state.llm
