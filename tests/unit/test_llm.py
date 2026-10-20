from __future__ import annotations

from types import SimpleNamespace

import pytest

from enterprise_rag.config import Settings
from enterprise_rag.infra.llm import DeepSeekLLM
from enterprise_rag.ports import LLMUnavailable


class FakeStream:
    def __init__(self) -> None:
        self.chunks = [
            SimpleNamespace(
                choices=[SimpleNamespace(delta=SimpleNamespace(content="你"), finish_reason=None)],
                usage=None,
            ),
            SimpleNamespace(
                choices=[SimpleNamespace(delta=SimpleNamespace(content="好"), finish_reason=None)],
                usage=None,
            ),
            SimpleNamespace(
                choices=[SimpleNamespace(delta=None, finish_reason="stop")],
                usage=SimpleNamespace(prompt_tokens=3, completion_tokens=2, total_tokens=5),
            ),
        ]

    def __iter__(self):
        return iter(self.chunks)


class FakeCompletions:
    def __init__(self) -> None:
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        return FakeStream()


def test_deepseek_stream_parses_chunks_and_request() -> None:
    settings = Settings(
        llm_provider="deepseek",
        deepseek_api_key="test-key",
        deepseek_model="deepseek-flash",
        deepseek_thinking="disabled",
    )
    llm = DeepSeekLLM(settings)
    completions = FakeCompletions()
    llm._client = SimpleNamespace(chat=SimpleNamespace(completions=completions))

    events = list(
        llm.stream_chat(
            [{"role": "user", "content": "你好"}],
            temperature=0.5,
            top_p=0.9,
            max_tokens=128,
        )
    )
    assert [item.get("text") for item in events if item["type"] == "delta"] == ["你", "好"]
    done = [item for item in events if item["type"] == "done"][0]
    assert done["finish_reason"] == "stop"
    assert done["usage"]["total_tokens"] == 5

    kwargs = completions.kwargs
    assert kwargs["model"] == "deepseek-flash"
    assert kwargs["temperature"] == 0.5
    assert kwargs["top_p"] == 0.9
    assert kwargs["max_tokens"] == 128
    assert kwargs["stream"] is True
    assert kwargs["extra_body"]["thinking"] == {"type": "disabled"}


def test_deepseek_without_key_raises() -> None:
    llm = DeepSeekLLM(Settings(llm_provider="deepseek", deepseek_api_key=""))
    with pytest.raises(LLMUnavailable):
        list(
            llm.stream_chat(
                [{"role": "user", "content": "hi"}],
                temperature=0.5,
                top_p=0.8,
                max_tokens=32,
            )
        )
