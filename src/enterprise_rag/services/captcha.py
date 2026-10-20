"""图形验证码：生成、存储、校验。"""

from __future__ import annotations

import base64
import io
import random
from datetime import timedelta

from PIL import Image, ImageDraw, ImageFont
from sqlalchemy import delete
from sqlalchemy.orm import Session

from ..config import Settings
from ..models import CaptchaChallenge
from ..security import hash_captcha
from ..utils import as_aware, new_id, utcnow

_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def _font(size: int) -> ImageFont.ImageFont:
    for name in ("arial.ttf", "segoeui.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            continue
    return ImageFont.load_default()


def generate_code(length: int = 4) -> str:
    return "".join(random.choice(_ALPHABET) for _ in range(length))


def render_captcha(code: str) -> str:
    width, height = 140, 48
    image = Image.new("RGB", (width, height), (246, 247, 255))
    draw = ImageDraw.Draw(image)
    for _ in range(6):
        draw.line(
            (
                random.randint(0, width),
                random.randint(0, height),
                random.randint(0, width),
                random.randint(0, height),
            ),
            fill=(random.randint(140, 220), random.randint(140, 220), random.randint(190, 245)),
            width=1,
        )
    for _ in range(80):
        draw.point(
            (random.randint(0, width), random.randint(0, height)),
            fill=(random.randint(120, 220), random.randint(120, 220), random.randint(160, 240)),
        )
    font = _font(28)
    for index, char in enumerate(code):
        color = (random.randint(30, 90), random.randint(40, 100), random.randint(100, 180))
        draw.text((12 + index * 30, 7 + random.randint(-2, 2)), char, font=font, fill=color)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def create_challenge(db: Session, settings: Settings) -> tuple[CaptchaChallenge, str]:
    # 顺手清理一小时前的过期记录
    db.execute(
        delete(CaptchaChallenge).where(CaptchaChallenge.expires_at < utcnow() - timedelta(hours=1))
    )
    code = generate_code()
    challenge = CaptchaChallenge(
        id=new_id("c_"),
        code_hash=hash_captcha("", code),
        expires_at=utcnow() + timedelta(seconds=settings.captcha_ttl_seconds),
    )
    # code_hash 需要 captcha_id 参与，先生成 id 再补
    challenge.code_hash = hash_captcha(challenge.id, code)
    db.add(challenge)
    db.commit()
    return challenge, code


def verify_challenge(db: Session, captcha_id: str, code: str) -> tuple[bool, str]:
    challenge = db.get(CaptchaChallenge, captcha_id)
    if challenge is None:
        return False, "验证码不存在，请刷新验证码。"
    if challenge.consumed_at is not None:
        return False, "验证码已使用，请刷新验证码。"
    if as_aware(challenge.expires_at) < utcnow():
        return False, "验证码已过期，请刷新验证码。"
    expected = challenge.code_hash
    challenge.consumed_at = utcnow()
    db.commit()
    if expected != hash_captcha(captcha_id, code):
        return False, "验证码错误，请重新输入。"
    return True, ""
