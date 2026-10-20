"""DeepSeek 流式客户端与测试用 Mock。"""

from __future__ import annotations

import logging
from collections.abc import Iterator, Sequence
from typing import Any

from ..config import Settings
from ..ports import LLM, LLMUnavailable

logger = logging.getLogger(__name__)


class DeepSeekLLM:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._client = None

    @property
    def configured(self) -> bool:
        return bool(self.settings.deepseek_api_key)

    def _client_or_raise(self):
        if not self.settings.deepseek_api_key:
            raise LLMUnavailable("未配置 DEEPSEEK_API_KEY，无法调用大模型。")
        if self._client is None:
            from openai import OpenAI

            self._client = OpenAI(
                api_key=self.settings.deepseek_api_key,
                base_url=self.settings.deepseek_base_url,
                timeout=self.settings.llm_timeout_s,
            )
        return self._client

    def stream_chat(
        self,
        messages: Sequence[dict[str, str]],
        *,
        temperature: float,
        top_p: float,
        max_tokens: int,
    ) -> Iterator[dict[str, Any]]:
        client = self._client_or_raise()
        extra_body: dict[str, Any] = {}
        if self.settings.deepseek_thinking == "disabled":
            extra_body["thinking"] = {"type": "disabled"}
        kwargs: dict[str, Any] = {
            "model": self.settings.deepseek_model,
            "messages": list(messages),
            "stream": True,
            "temperature": temperature,
            "top_p": top_p,
            "max_tokens": max_tokens,
            "stream_options": {"include_usage": True},
        }
        if extra_body:
            kwargs["extra_body"] = extra_body
        try:
            stream = client.chat.completions.create(**kwargs)
        except Exception as exc:  # pragma: no cover - 依赖网络
            logger.exception("DeepSeek 请求失败")
            raise LLMUnavailable(f"DeepSeek 请求失败：{exc}") from exc

        finish_reason = None
        usage = None
        for chunk in stream:
            choices = getattr(chunk, "choices", None) or []
            if choices:
                choice = choices[0]
                delta = getattr(choice, "delta", None)
                text = getattr(delta, "content", None) if delta is not None else None
                if text:
                    yield {"type": "delta", "text": text}
                finish_reason = getattr(choice, "finish_reason", None) or finish_reason
            chunk_usage = getattr(chunk, "usage", None)
            if chunk_usage is not None:
                usage = {
                    "prompt_tokens": getattr(chunk_usage, "prompt_tokens", None),
                    "completion_tokens": getattr(chunk_usage, "completion_tokens", None),
                    "total_tokens": getattr(chunk_usage, "total_tokens", None),
                }
        yield {"type": "done", "finish_reason": finish_reason or "stop", "usage": usage}


class MockLLM:
    """测试用：从最后一条用户消息中提取资料，返回确定性中文回答。"""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings

    def stream_chat(
        self,
        messages: Sequence[dict[str, str]],
        *,
        temperature: float,
        top_p: float,
        max_tokens: int,
    ) -> Iterator[dict[str, Any]]:
        question = ""
        for message in reversed(messages):
            if message.get("role") == "user":
                content = message.get("content", "")
                if "【用户问题】" in content:
                    content = content.split("【用户问题】", 1)[1]
                question = content.strip()
                break
        answer = (
            "根据现有知识库，可以确认以下信息：\n\n"
            "1. 这是基于检索资料生成的演示回答，正式环境会调用 DeepSeek 生成。\n"
            f"2. 用户问题：{question[-120:]}\n"
            "3. 回答仅使用检索到的资料，并在正文中标注来源编号。"
        )
        for start in range(0, len(answer), 16):
            yield {"type": "delta", "text": answer[start : start + 16]}
        yield {
            "type": "done",
            "finish_reason": "stop",
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        }


def build_llm(settings: Settings) -> LLM:
    if settings.llm_provider == "mock":
        return MockLLM(settings)
    return DeepSeekLLM(settings)
