"""文本切块：按段落/句子边界累积，保留页码与字符区间。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .parsers import TextBlock

_BOUNDARY = set("。！？；!?;\n")


@dataclass
class Chunk:
    content: str
    char_start: int
    char_end: int
    page_no: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


def _build_full_text(blocks: list[TextBlock]) -> tuple[str, list[tuple[int, int, TextBlock]]]:
    parts: list[str] = []
    ranges: list[tuple[int, int, TextBlock]] = []
    cursor = 0
    for block in blocks:
        text = block.text.strip()
        if not text:
            continue
        if parts:
            parts.append("\n\n")
            cursor += 2
        start = cursor
        parts.append(text)
        cursor += len(text)
        ranges.append((start, cursor, block))
    return "".join(parts), ranges


def _page_at(ranges: list[tuple[int, int, TextBlock]], position: int) -> int | None:
    for start, end, block in ranges:
        if start <= position < end:
            return block.page_no
    return ranges[-1][2].page_no if ranges else None


def _metadata_at(ranges: list[tuple[int, int, TextBlock]], position: int) -> dict[str, Any]:
    for start, end, block in ranges:
        if start <= position < end:
            return dict(block.metadata)
    return {}


def _find_end(text: str, start: int, target: int) -> int:
    if target >= len(text):
        return len(text)
    floor = start + max(1, (target - start) // 2)
    for index in range(target - 1, floor - 1, -1):
        if text[index] in _BOUNDARY:
            return index + 1
    return target


def chunk_blocks(blocks: list[TextBlock], chunk_size: int, chunk_overlap: int) -> list[Chunk]:
    full_text, ranges = _build_full_text(blocks)
    if not full_text:
        return []
    chunks: list[Chunk] = []
    start = 0
    length = len(full_text)
    while start < length:
        target = min(start + chunk_size, length)
        end = _find_end(full_text, start, target)
        raw = full_text[start:end]
        leading = len(raw) - len(raw.lstrip())
        trailing = len(raw) - len(raw.rstrip())
        content = raw.strip()
        if content:
            actual_start = start + leading
            actual_end = end - trailing
            chunks.append(
                Chunk(
                    content=content,
                    char_start=actual_start,
                    char_end=actual_end,
                    page_no=_page_at(ranges, actual_start),
                    metadata=_metadata_at(ranges, actual_start),
                )
            )
        if end >= length:
            break
        next_start = max(end - chunk_overlap, start + 1)
        while next_start < length and full_text[next_start].isspace():
            next_start += 1
        start = next_start
    return chunks
