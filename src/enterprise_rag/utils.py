"""通用工具：ID、时间、文件与 JSON。"""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def utcnow() -> datetime:
    return datetime.now(UTC)


def new_id(prefix: str = "") -> str:
    value = uuid.uuid4().hex[:24]
    return f"{prefix}{value}" if prefix else value


def iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat()


def as_aware(value: datetime) -> datetime:
    """SQLite 会丢掉时区；统一按 UTC 处理。"""

    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def safe_filename(name: str, fallback: str = "document") -> str:
    """保留中文与常见字符，去掉路径分隔符和危险字符。"""

    base = Path(name or "").name.strip()
    base = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", base)
    base = re.sub(r"\s+", " ", base).strip(" .")
    return base[:180] or fallback


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)] + "…"
