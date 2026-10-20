"""图片 OCR：懒加载 RapidOCR。"""

from __future__ import annotations

import logging
import threading

from PIL import Image

logger = logging.getLogger(__name__)

_engine = None
_lock = threading.Lock()


def _get_engine():
    global _engine
    if _engine is not None:
        return _engine
    with _lock:
        if _engine is None:
            try:
                from rapidocr import RapidOCR
            except Exception as exc:  # pragma: no cover - 依赖安装失败
                raise RuntimeError(f"OCR 组件不可用：{exc}") from exc
            _engine = RapidOCR()
    return _engine


def _extract_text(result: object) -> str:
    if result is None:
        return ""
    if isinstance(result, tuple):
        result = result[0] if result else None
    if result is None:
        return ""
    txts = getattr(result, "txts", None)
    if txts:
        return "\n".join(str(item) for item in txts)
    lines: list[str] = []
    items = result if isinstance(result, (list, tuple)) else []
    for item in items:
        if isinstance(item, str):
            lines.append(item)
            continue
        text = getattr(item, "txt", None)
        if text:
            lines.append(str(text))
            continue
        if isinstance(item, (list, tuple)) and len(item) >= 2:
            value = item[1]
            if isinstance(value, str):
                lines.append(value)
    return "\n".join(lines)


def ocr_image(image: Image.Image) -> str:
    engine = _get_engine()
    try:
        import numpy as np

        array = np.array(image.convert("RGB"))
    except Exception:
        array = image.convert("RGB")
    try:
        result = engine(array)
    except Exception:
        logger.exception("OCR 识别失败")
        return ""
    return _extract_text(result).strip()
