"""文档解析：PDF / PPTX / Markdown / 图片 / DOCX。"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..infra.ocr import ocr_image

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {
    ".pdf": "pdf",
    ".pptx": "pptx",
    ".md": "md",
    ".markdown": "md",
    ".png": "image",
    ".jpg": "image",
    ".jpeg": "image",
    ".webp": "image",
    ".docx": "docx",
}

FILE_TYPE_LABELS = {
    "pdf": "PDF",
    "pptx": "PPTX",
    "md": "Markdown",
    "image": "图片",
    "docx": "DOCX",
}


@dataclass
class TextBlock:
    text: str
    page_no: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\x00", "")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _pdf_blocks(path: Path) -> list[TextBlock]:
    import fitz
    from PIL import Image

    blocks: list[TextBlock] = []
    with fitz.open(path) as document:
        for index, page in enumerate(document, start=1):
            text = normalize_text(page.get_text("text"))
            if len(text) < 20:
                pix = page.get_pixmap(dpi=150)
                image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                ocr_text = normalize_text(ocr_image(image))
                if ocr_text:
                    text = ocr_text
                    blocks.append(TextBlock(text=text, page_no=index, metadata={"ocr": True}))
                    continue
            if text:
                blocks.append(TextBlock(text=text, page_no=index))
    return blocks


def _pptx_blocks(path: Path) -> list[TextBlock]:
    from pptx import Presentation

    blocks: list[TextBlock] = []
    presentation = Presentation(str(path))
    for index, slide in enumerate(presentation.slides, start=1):
        parts: list[str] = []
        for shape in slide.shapes:
            if getattr(shape, "has_text_frame", False):
                text = normalize_text(shape.text_frame.text)
                if text:
                    parts.append(text)
            if getattr(shape, "has_table", False):
                for row in shape.table.rows:
                    cells = [normalize_text(cell.text) for cell in row.cells]
                    line = " | ".join(cell for cell in cells if cell)
                    if line:
                        parts.append(line)
        try:
            notes = normalize_text(slide.notes_slide.notes_text_frame.text)
            if notes:
                parts.append(f"备注：{notes}")
        except Exception:
            pass
        text = normalize_text("\n\n".join(parts))
        if text:
            blocks.append(TextBlock(text=text, page_no=index))
    return blocks


def _markdown_blocks(path: Path) -> list[TextBlock]:
    text = normalize_text(path.read_text(encoding="utf-8", errors="ignore"))
    if not text:
        return []
    # 按一级/二级标题拆块，保留标题作为元数据。
    chunks = re.split(r"(?m)^(#{1,3}\s+.+)$", text)
    blocks: list[TextBlock] = []
    current_heading = ""
    for part in chunks:
        part = part.strip()
        if not part:
            continue
        if re.match(r"^#{1,3}\s+", part):
            current_heading = part.lstrip("#").strip()
            continue
        metadata = {"heading": current_heading} if current_heading else {}
        blocks.append(TextBlock(text=part, metadata=metadata))
    if not blocks:
        blocks.append(TextBlock(text=text))
    return blocks


def _image_blocks(path: Path) -> list[TextBlock]:
    from PIL import Image

    with Image.open(path) as image:
        text = normalize_text(ocr_image(image))
    if not text:
        raise ValueError("图片中未识别到文字，请换一张更清晰的图片。")
    return [TextBlock(text=text, page_no=1, metadata={"ocr": True})]


def _docx_blocks(path: Path) -> list[TextBlock]:
    from docx import Document

    document = Document(str(path))
    parts: list[str] = []
    for paragraph in document.paragraphs:
        text = normalize_text(paragraph.text)
        if text:
            parts.append(text)
    for table in document.tables:
        for row in table.rows:
            cells = [normalize_text(cell.text) for cell in row.cells]
            line = " | ".join(cell for cell in cells if cell)
            if line:
                parts.append(line)
    text = normalize_text("\n\n".join(parts))
    return [TextBlock(text=text)] if text else []


def parse_file(path: Path, file_type: str) -> list[TextBlock]:
    path = Path(path)
    if file_type == "pdf":
        blocks = _pdf_blocks(path)
    elif file_type == "pptx":
        blocks = _pptx_blocks(path)
    elif file_type == "md":
        blocks = _markdown_blocks(path)
    elif file_type == "image":
        blocks = _image_blocks(path)
    elif file_type == "docx":
        blocks = _docx_blocks(path)
    else:
        raise ValueError(f"不支持的文件类型：{file_type}")
    blocks = [block for block in blocks if block.text.strip()]
    if not blocks:
        raise ValueError("未从文件中提取到文本，请检查文件是否为空或为扫描件。")
    return blocks
