from __future__ import annotations

import os

import pytest

from enterprise_rag.config import Settings
from enterprise_rag.infra.embedder import BgeM3Embedder
from enterprise_rag.infra.llm import DeepSeekLLM


@pytest.mark.bge_m3
def test_bge_m3_dense_embedding() -> None:
    if os.getenv("RUN_BGE_M3") != "1":
        pytest.skip("设置 RUN_BGE_M3=1 后运行（首次需下载约 2.2GB 模型）")
    settings = Settings(embedding_provider="bge_m3", embedding_device="auto")
    embedder = BgeM3Embedder(settings)
    vectors = embedder.embed(["西部计划服务期一般为 1 至 3 年。", "志愿者生活补贴按当年文件执行。"])
    assert len(vectors) == 2
    assert len(vectors[0]) == 1024
    assert abs(sum(value * value for value in vectors[0]) - 1.0) < 1e-3
    assert vectors[0] != vectors[1]


@pytest.mark.deepseek
def test_deepseek_stream() -> None:
    key = os.getenv("DEEPSEEK_API_KEY", "")
    if os.getenv("RUN_DEEPSEEK") != "1" or not key:
        pytest.skip("设置 RUN_DEEPSEEK=1 和 DEEPSEEK_API_KEY 后运行")
    settings = Settings(llm_provider="deepseek", deepseek_api_key=key)
    llm = DeepSeekLLM(settings)
    chunks = list(
        llm.stream_chat(
            [{"role": "user", "content": "用一句中文说明什么是 RAG。"}],
            temperature=0.3,
            top_p=0.8,
            max_tokens=128,
        )
    )
    text = "".join(item.get("text", "") for item in chunks if item.get("type") == "delta")
    assert text.strip()
    assert any(item.get("type") == "done" for item in chunks)
