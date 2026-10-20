"""认证接口。"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..config import Settings
from ..models import User
from ..schemas import CaptchaOut, LoginIn, RegisterIn, TokenOut, UserOut
from ..security import create_access_token, hash_password, verify_password
from ..services.captcha import create_challenge, render_captcha, verify_challenge
from ..utils import utcnow
from .deps import get_current_user, get_db, get_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/auth", tags=["认证"])


@router.get("/captcha", response_model=CaptchaOut)
def captcha(
    db: Session = Depends(get_db), settings: Settings = Depends(get_settings)
) -> CaptchaOut:
    challenge, code = create_challenge(db, settings)
    expose = settings.expose_captcha_code or settings.app_env == "test"
    return CaptchaOut(
        captcha_id=challenge.id,
        image_base64=render_captcha(code),
        expires_in=settings.captcha_ttl_seconds,
        debug_code=code if expose else None,
    )


def _issue_token(user: User, settings: Settings) -> TokenOut:
    token = create_access_token(user.id, user.role, settings)
    return TokenOut(
        access_token=token,
        expires_in=settings.jwt_expire_minutes * 60,
        user=UserOut.model_validate(user),
    )


@router.post("/register", response_model=TokenOut, status_code=201)
def register(
    payload: RegisterIn,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> TokenOut:
    ok, message = verify_challenge(db, payload.captcha_id, payload.captcha_code)
    if not ok:
        raise HTTPException(status_code=400, detail={"code": "CAPTCHA_INVALID", "message": message})
    existing = db.query(User).filter(User.username == payload.username).first()
    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail={"code": "USERNAME_TAKEN", "message": "用户名已被占用，请换一个。"},
        )
    user = User(
        username=payload.username,
        password_hash=hash_password(payload.password),
        role="user",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info("新用户注册：%s", user.username)
    return _issue_token(user, settings)


@router.post("/login", response_model=TokenOut)
def login(
    payload: LoginIn,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> TokenOut:
    ok, message = verify_challenge(db, payload.captcha_id, payload.captcha_code)
    if not ok:
        raise HTTPException(status_code=400, detail={"code": "CAPTCHA_INVALID", "message": message})
    user = db.query(User).filter(User.username == payload.username).first()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=401,
            detail={"code": "INVALID_CREDENTIALS", "message": "账号或密码错误。"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=403, detail={"code": "FORBIDDEN", "message": "账号已停用。"}
        )
    user.last_login_at = utcnow()
    db.commit()
    logger.info("用户登录：%s", user.username)
    return _issue_token(user, settings)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> UserOut:
    return UserOut.model_validate(user)


@router.post("/logout", status_code=204)
def logout() -> None:
    return None
