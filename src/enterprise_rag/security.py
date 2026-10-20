"""认证与密码工具。"""

from __future__ import annotations

import hashlib
from datetime import timedelta

import jwt
from pwdlib import PasswordHash

from .config import Settings
from .utils import utcnow

_password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return _password_hash.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _password_hash.verify(password, password_hash)
    except Exception:
        return False


def create_access_token(user_id: str, role: str, settings: Settings) -> str:
    now = utcnow()
    payload = {
        "sub": user_id,
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_access_token(token: str, settings: Settings) -> dict[str, object]:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except jwt.PyJWTError as exc:  # pragma: no cover - 由上层转成 401
        raise ValueError("invalid token") from exc
    if not payload.get("sub"):
        raise ValueError("missing subject")
    return payload


def hash_captcha(captcha_id: str, code: str) -> str:
    return hashlib.sha256(f"{captcha_id}:{code.upper()}".encode()).hexdigest()
