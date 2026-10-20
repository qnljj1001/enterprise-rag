from __future__ import annotations

import os
from pathlib import Path

import pytest

from enterprise_rag.ingest.parsers import parse_file

SAMPLES = Path(__file__).resolve().parents[2] / "data" / "samples"


def test_parse_markdown() -> None:
    blocks = parse_file(SAMPLES / "policy_faq.md", "md")
    text = "\n".join(block.text for block in blocks)
    assert "服务期" in text
    assert "生活补贴" in text


def test_parse_pptx() -> None:
    blocks = parse_file(SAMPLES / "policy_slides.pptx", "pptx")
    text = "\n".join(block.text for block in blocks)
    assert "西部计划政策要点" in text
    assert any(block.page_no == 1 for block in blocks)


def test_parse_pdf() -> None:
    blocks = parse_file(SAMPLES / "L1-2022-002.pdf", "pdf")
    text = "\n".join(block.text for block in blocks)
    assert "西部计划" in text
    assert blocks[0].page_no == 1


@pytest.mark.integration
def test_parse_image_ocr() -> None:
    if os.getenv("RUN_OCR") != "1":
        pytest.skip("设置 RUN_OCR=1 后运行（首次会下载 OCR 模型）")
    blocks = parse_file(SAMPLES / "ocr_policy.png", "image")
    text = "\n".join(block.text for block in blocks)
    assert "服务期" in text or "社会保险" in text
