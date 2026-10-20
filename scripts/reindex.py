"""从 MySQL 文档块重建某个知识库的 Milvus 索引。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from enterprise_rag.config import get_settings  # noqa: E402
from enterprise_rag.db import Database  # noqa: E402
from enterprise_rag.infra.embedder import build_embedder  # noqa: E402
from enterprise_rag.infra.milvus import build_vector_store  # noqa: E402
from enterprise_rag.models import DocumentChunk  # noqa: E402
from enterprise_rag.utils import utcnow  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--kb-id", required=True)
    args = parser.parse_args()
    settings = get_settings()
    db = Database(settings.database_url)
    embedder = build_embedder(settings)
    vector_store = build_vector_store(settings)
    vector_store.ensure_collection()
    session = db.SessionLocal()
    try:
        chunks = (
            session.query(DocumentChunk)
            .filter(DocumentChunk.kb_id == args.kb_id)
            .order_by(DocumentChunk.document_id, DocumentChunk.chunk_index)
            .all()
        )
        vector_store.delete_knowledge_base(args.kb_id)
        rows = []
        for chunk in chunks:
            vector = embedder.embed([chunk.content])[0]
            rows.append(
                {
                    "chunk_id": chunk.id,
                    "kb_id": chunk.kb_id,
                    "document_id": chunk.document_id,
                    "chunk_index": chunk.chunk_index,
                    "page_no": chunk.page_no or 0,
                    "created_at": int(utcnow().timestamp()),
                    "content": chunk.content,
                    "embedding": vector,
                }
            )
        if rows:
            vector_store.insert_chunks(rows)
        print(f"知识库 {args.kb_id} 重建完成：{len(rows)} 块")
    finally:
        session.close()
        db.dispose()


if __name__ == "__main__":
    main()
