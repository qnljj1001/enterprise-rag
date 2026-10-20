"""Milvus 向量库与测试用内存实现。"""

from __future__ import annotations

import logging
import math
from collections.abc import Sequence
from typing import Any

from ..config import Settings
from ..ports import VectorStore, VectorStoreUnavailable

logger = logging.getLogger(__name__)

OUTPUT_FIELDS = ["chunk_id", "document_id", "kb_id", "content", "page_no"]


def _filter(kb_ids: Sequence[str]) -> str:
    values = ", ".join('"' + str(item).replace('"', '\\"') + '"' for item in kb_ids)
    return f"kb_id in [{values}]"


def _parse_hits(result: Any) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    if not result:
        return hits
    for group in result:
        for hit in group or []:
            entity = hit.get("entity") or {}
            chunk_id = entity.get("chunk_id") or hit.get("id")
            if not chunk_id:
                continue
            hits.append(
                {
                    "chunk_id": str(chunk_id),
                    "document_id": str(entity.get("document_id", "")),
                    "kb_id": str(entity.get("kb_id", "")),
                    "content": entity.get("content", ""),
                    "page_no": entity.get("page_no"),
                    "score": float(hit.get("distance", 0.0)),
                }
            )
    return hits


class MilvusVectorStore:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.collection = settings.milvus_collection
        self.available = False
        self._client = None
        self._error: str | None = None

    def _client_or_raise(self):
        if self._client is None:
            from pymilvus import MilvusClient

            kwargs: dict[str, Any] = {"uri": self.settings.milvus_uri}
            if self.settings.milvus_token:
                kwargs["token"] = self.settings.milvus_token
            self._client = MilvusClient(**kwargs)
        return self._client

    def ensure_collection(self) -> None:
        try:
            from pymilvus import DataType, Function, FunctionType

            client = self._client_or_raise()
            if client.has_collection(self.collection):
                client.load_collection(self.collection)
                self.available = True
                self._error = None
                logger.info("Milvus 集合已就绪：%s", self.collection)
                return

            schema = client.create_schema(auto_id=False, enable_dynamic_field=False)
            schema.add_field("chunk_id", DataType.VARCHAR, is_primary=True, max_length=64)
            schema.add_field("kb_id", DataType.VARCHAR, max_length=64)
            schema.add_field("document_id", DataType.VARCHAR, max_length=64)
            schema.add_field("chunk_index", DataType.INT64)
            schema.add_field("page_no", DataType.INT64)
            schema.add_field("created_at", DataType.INT64)
            schema.add_field(
                "content",
                DataType.VARCHAR,
                max_length=8192,
                enable_analyzer=True,
                analyzer_params={"type": "chinese"},
            )
            schema.add_field("embedding", DataType.FLOAT_VECTOR, dim=self.settings.embedding_dim)
            schema.add_field("sparse", DataType.SPARSE_FLOAT_VECTOR)
            schema.add_function(
                Function(
                    name="content_bm25",
                    function_type=FunctionType.BM25,
                    input_field_names=["content"],
                    output_field_names=["sparse"],
                )
            )
            index_params = client.prepare_index_params()
            index_params.add_index(
                field_name="embedding", index_type="AUTOINDEX", metric_type="COSINE"
            )
            index_params.add_index(field_name="sparse", index_type="AUTOINDEX", metric_type="BM25")
            client.create_collection(
                collection_name=self.collection,
                schema=schema,
                index_params=index_params,
            )
            client.load_collection(self.collection)
            self.available = True
            self._error = None
            logger.info("Milvus 集合创建完成：%s", self.collection)
        except Exception as exc:
            self.available = False
            self._error = str(exc)
            logger.exception("Milvus 初始化失败：%s", exc)

    def _require(self):
        if not self.available:
            raise VectorStoreUnavailable(self._error or "Milvus 不可用")
        return self._client_or_raise()

    def insert_chunks(self, rows: Sequence[dict[str, Any]], *, flush: bool = True) -> None:
        if not rows:
            return
        client = self._require()
        client.upsert(collection_name=self.collection, data=list(rows))
        if flush:
            client.flush(self.collection)

    def flush(self) -> None:
        client = self._require()
        client.flush(self.collection)

    def delete_chunks(self, chunk_ids: Sequence[str]) -> None:
        if not chunk_ids:
            return
        client = self._require()
        client.delete(collection_name=self.collection, ids=list(chunk_ids))
        client.flush(self.collection)

    def delete_document(self, document_id: str) -> None:
        client = self._require()
        value = str(document_id).replace('"', '\\"')
        client.delete(collection_name=self.collection, filter=f'document_id == "{value}"')
        client.flush(self.collection)

    def delete_knowledge_base(self, kb_id: str) -> None:
        client = self._require()
        value = str(kb_id).replace('"', '\\"')
        client.delete(collection_name=self.collection, filter=f'kb_id == "{value}"')
        client.flush(self.collection)

    def search_dense(
        self, query_vector: Sequence[float], kb_ids: Sequence[str], limit: int
    ) -> list[dict[str, Any]]:
        client = self._require()
        result = client.search(
            collection_name=self.collection,
            data=[list(query_vector)],
            anns_field="embedding",
            search_params={"metric_type": "COSINE"},
            limit=limit,
            filter=_filter(kb_ids),
            output_fields=OUTPUT_FIELDS,
        )
        return _parse_hits(result)

    def search_hybrid(
        self,
        query_vector: Sequence[float],
        query_text: str,
        kb_ids: Sequence[str],
        limit: int,
    ) -> list[dict[str, Any]]:
        try:
            from pymilvus import AnnSearchRequest, RRFRanker

            client = self._require()
            dense = AnnSearchRequest(
                data=[list(query_vector)],
                anns_field="embedding",
                param={"metric_type": "COSINE"},
                limit=limit,
            )
            sparse = AnnSearchRequest(
                data=[query_text],
                anns_field="sparse",
                param={"metric_type": "BM25"},
                limit=limit,
            )
            result = client.hybrid_search(
                collection_name=self.collection,
                reqs=[dense, sparse],
                ranker=RRFRanker(60),
                limit=limit,
                filter=_filter(kb_ids),
                output_fields=OUTPUT_FIELDS,
            )
            return _parse_hits(result)
        except Exception:
            logger.exception("Milvus 混合检索失败，降级为稠密检索")
            return self.search_dense(query_vector, kb_ids, limit)


class InMemoryVectorStore:
    """测试用向量库：稠密用余弦，混合加关键词覆盖率。"""

    def __init__(self) -> None:
        self.available = True
        self.rows: dict[str, dict[str, Any]] = {}

    def ensure_collection(self) -> None:
        self.available = True

    def insert_chunks(self, rows: Sequence[dict[str, Any]], *, flush: bool = True) -> None:
        for row in rows:
            self.rows[str(row["chunk_id"])] = dict(row)

    def flush(self) -> None:
        return None

    def delete_chunks(self, chunk_ids: Sequence[str]) -> None:
        for chunk_id in chunk_ids:
            self.rows.pop(str(chunk_id), None)

    def delete_document(self, document_id: str) -> None:
        for chunk_id, row in list(self.rows.items()):
            if str(row.get("document_id")) == str(document_id):
                self.rows.pop(chunk_id, None)

    def delete_knowledge_base(self, kb_id: str) -> None:
        for chunk_id, row in list(self.rows.items()):
            if str(row.get("kb_id")) == str(kb_id):
                self.rows.pop(chunk_id, None)

    @staticmethod
    def _cosine(a: Sequence[float], b: Sequence[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b, strict=False))
        na = math.sqrt(sum(x * x for x in a)) or 1.0
        nb = math.sqrt(sum(y * y for y in b)) or 1.0
        return dot / (na * nb)

    def _ranked(
        self,
        query_vector: Sequence[float],
        query_text: str,
        kb_ids: Sequence[str],
        limit: int,
        *,
        hybrid: bool,
    ) -> list[dict[str, Any]]:
        kb_set = {str(item) for item in kb_ids}
        query_terms = set(query_text.lower().split())
        scored: list[tuple[float, dict[str, Any]]] = []
        for row in self.rows.values():
            if str(row.get("kb_id")) not in kb_set:
                continue
            dense = self._cosine(query_vector, row.get("embedding", []))
            score = dense
            if hybrid:
                content = str(row.get("content", "")).lower()
                overlap = len(query_terms & set(content.split()))
                score = dense + 0.1 * overlap
            scored.append((score, row))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [
            {
                "chunk_id": row["chunk_id"],
                "document_id": row["document_id"],
                "kb_id": row["kb_id"],
                "content": row.get("content", ""),
                "page_no": row.get("page_no"),
                "score": float(score),
            }
            for score, row in scored[:limit]
        ]

    def search_dense(
        self, query_vector: Sequence[float], kb_ids: Sequence[str], limit: int
    ) -> list[dict[str, Any]]:
        return self._ranked(query_vector, "", kb_ids, limit, hybrid=False)

    def search_hybrid(
        self,
        query_vector: Sequence[float],
        query_text: str,
        kb_ids: Sequence[str],
        limit: int,
    ) -> list[dict[str, Any]]:
        return self._ranked(query_vector, query_text, kb_ids, limit, hybrid=True)


def build_vector_store(settings: Settings) -> VectorStore:
    if settings.app_env == "test":
        return InMemoryVectorStore()
    return MilvusVectorStore(settings)
