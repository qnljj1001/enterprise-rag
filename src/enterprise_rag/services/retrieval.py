"""检索：按知识库检索模式分组，RRF 合并。"""

from __future__ import annotations

import logging
from collections.abc import Sequence

from sqlalchemy.orm import Session

from ..config import Settings
from ..models import Document, DocumentChunk, KnowledgeBase
from ..ports import Embedder, VectorStore

logger = logging.getLogger(__name__)

RRF_K = 60


class RetrievalService:
    def __init__(self, settings: Settings, vector_store: VectorStore, embedder: Embedder) -> None:
        self.settings = settings
        self.vector_store = vector_store
        self.embedder = embedder

    def search(
        self, db: Session, kb_ids: Sequence[str], query: str, top_k: int | None = None
    ) -> list[dict]:
        if not kb_ids or not query.strip():
            return []
        kbs = db.query(KnowledgeBase).filter(KnowledgeBase.id.in_(list(kb_ids))).all()
        if not kbs:
            return []
        grouped: dict[str, list[str]] = {"dense": [], "hybrid": []}
        for kb in kbs:
            grouped.setdefault(kb.retrieval_mode, []).append(kb.id)

        limit = top_k or self.settings.top_k
        query_vector = self.embedder.embed([query])[0]
        ranked_lists: list[list[dict]] = []
        for mode, ids in grouped.items():
            if not ids:
                continue
            if mode == "hybrid":
                ranked_lists.append(
                    self.vector_store.search_hybrid(query_vector, query, ids, limit * 2)
                )
            else:
                ranked_lists.append(self.vector_store.search_dense(query_vector, ids, limit * 2))

        scores: dict[str, float] = {}
        items: dict[str, dict] = {}
        for results in ranked_lists:
            for rank, item in enumerate(results, start=1):
                chunk_id = item["chunk_id"]
                scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (RRF_K + rank)
                items.setdefault(chunk_id, item)
        ordered = sorted(scores.items(), key=lambda pair: pair[1], reverse=True)[:limit]
        if not ordered:
            return []

        chunk_ids = [chunk_id for chunk_id, _ in ordered]
        rows = (
            db.query(DocumentChunk, Document, KnowledgeBase)
            .join(Document, Document.id == DocumentChunk.document_id)
            .join(KnowledgeBase, KnowledgeBase.id == DocumentChunk.kb_id)
            .filter(DocumentChunk.id.in_(chunk_ids))
            .all()
        )
        by_id = {
            chunk.id: {
                "chunk_id": chunk.id,
                "document_id": chunk.document_id,
                "filename": document.filename,
                "kb_name": kb.name,
                "page_no": chunk.page_no,
                "content": chunk.content,
                "score": score,
            }
            for chunk, document, kb in rows
            for score in [scores.get(chunk.id, 0.0)]
        }
        return [by_id[chunk_id] for chunk_id, _ in ordered if chunk_id in by_id]
