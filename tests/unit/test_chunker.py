from __future__ import annotations

from enterprise_rag.ingest.chunker import chunk_blocks
from enterprise_rag.ingest.parsers import TextBlock


def test_chunker_respects_size_and_overlap() -> None:
    text = "第一句话。第二句话。" * 60
    chunks = chunk_blocks([TextBlock(text=text, page_no=1)], 200, 20)
    assert len(chunks) > 1
    assert all(len(item.content) <= 220 for item in chunks)
    assert chunks[0].page_no == 1
    assert chunks[0].char_start == 0
    assert chunks[-1].char_end <= len(text)


def test_chunker_handles_empty() -> None:
    assert chunk_blocks([], 200, 20) == []
    assert chunk_blocks([TextBlock(text="   ")], 200, 20) == []


def test_chunker_page_numbers() -> None:
    blocks = [
        TextBlock(text="第一页内容。" * 20, page_no=1),
        TextBlock(text="第二页内容。" * 20, page_no=2),
    ]
    chunks = chunk_blocks(blocks, 150, 20)
    assert any(item.page_no == 2 for item in chunks)
