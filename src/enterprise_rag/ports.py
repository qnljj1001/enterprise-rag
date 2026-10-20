"""可替换端口：向量库、编码器、大模型。"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from typing import Any, Protocol


class VectorStoreUnavailable(RuntimeError):
    pass


class VectorHit(dict):
    """向量检索结果；至少包含 chunk_id / document_id / kb_id / content / score。"""


class VectorStore(Protocol):
    available: bool

    def ensure_collection(self) -> None: ...

    def insert_chunks(self, rows: Sequence[dict[str, Any]], *, flush: bool = True) -> None: ...

    def flush(self) -> None: ...

    def delete_chunks(self, chunk_ids: Sequence[str]) -> None: ...

    def delete_document(self, document_id: str) -> None: ...

    def delete_knowledge_base(self, kb_id: str) -> None: ...

    def search_dense(
        self, query_vector: Sequence[float], kb_ids: Sequence[str], limit: int
    ) -> list[dict[str, Any]]: ...

    def search_hybrid(
        self,
        query_vector: Sequence[float],
        query_text: str,
        kb_ids: Sequence[str],
        limit: int,
    ) -> list[dict[str, Any]]: ...


class Embedder(Protocol):
    dim: int

    def embed(self, texts: Sequence[str]) -> list[list[float]]: ...


class LLM(Protocol):
    def stream_chat(
        self,
        messages: Sequence[dict[str, str]],
        *,
        temperature: float,
        top_p: float,
        max_tokens: int,
    ) -> Iterator[dict[str, Any]]: ...


class LLMUnavailable(RuntimeError):
    pass
