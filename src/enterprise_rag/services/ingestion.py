"""文档入库：解析 -> 切块 -> bge-m3 编码 -> Milvus。"""

from __future__ import annotations

import logging
from pathlib import Path

from sqlalchemy import delete
from sqlalchemy.orm import Session

from ..config import Settings
from ..ingest.chunker import chunk_blocks
from ..ingest.parsers import parse_file
from ..models import Document, DocumentChunk
from ..ports import Embedder, VectorStore
from ..utils import new_id, truncate, utcnow

logger = logging.getLogger(__name__)


class IngestionService:
    def __init__(
        self,
        settings: Settings,
        vector_store: VectorStore,
        embedder: Embedder,
    ) -> None:
        self.settings = settings
        self.vector_store = vector_store
        self.embedder = embedder

    def process_document(self, db: Session, document_id: str) -> Document:
        document = db.get(Document, document_id)
        if document is None:
            raise ValueError(f"文档不存在：{document_id}")
        document.status = "parsing"
        document.progress = 5
        document.error_message = None
        db.commit()

        try:
            blocks = parse_file(Path(document.stored_path), document.file_type)
            document.status = "chunking"
            document.progress = 20
            db.commit()

            chunks = chunk_blocks(blocks, document.chunk_size, document.chunk_overlap)
            if not chunks:
                raise ValueError("切块结果为空，请检查文档内容。")

            # 清理旧块与旧向量，支持重新解析
            old_ids = [
                row[0]
                for row in db.query(DocumentChunk.id)
                .filter(DocumentChunk.document_id == document.id)
                .all()
            ]
            if old_ids:
                try:
                    self.vector_store.delete_chunks(old_ids)
                except Exception:
                    logger.warning("清理旧向量失败，继续重建", exc_info=True)
                db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document.id))
                db.commit()

            document.status = "embedding"
            document.progress = 35
            document.chunk_count = len(chunks)
            db.commit()

            rows: list[DocumentChunk] = []
            for index, chunk in enumerate(chunks):
                rows.append(
                    DocumentChunk(
                        id=new_id("chk_"),
                        kb_id=document.kb_id,
                        document_id=document.id,
                        chunk_index=index,
                        content=chunk.content,
                        char_start=chunk.char_start,
                        char_end=chunk.char_end,
                        page_no=chunk.page_no,
                        chunk_metadata=chunk.metadata,
                    )
                )
            db.add_all(rows)
            db.commit()

            batch_size = max(1, self.settings.embedding_batch_size)
            total = len(rows)
            for offset in range(0, total, batch_size):
                batch = rows[offset : offset + batch_size]
                vectors = self.embedder.embed([item.content for item in batch])
                vector_rows = []
                for item, vector in zip(batch, vectors, strict=False):
                    vector_rows.append(
                        {
                            "chunk_id": item.id,
                            "kb_id": item.kb_id,
                            "document_id": item.document_id,
                            "chunk_index": item.chunk_index,
                            "page_no": item.page_no or 0,
                            "created_at": int(utcnow().timestamp()),
                            "content": item.content,
                            "embedding": vector,
                        }
                    )
                self.vector_store.insert_chunks(vector_rows)
                document.progress = 35 + int(50 * min(1.0, (offset + len(batch)) / total))
                db.commit()

            document.status = "indexing"
            document.progress = 90
            db.commit()
            document.status = "ready"
            document.progress = 100
            document.chunk_count = total
            db.commit()
            logger.info("文档入库完成：doc=%s chunks=%s kb=%s", document.id, total, document.kb_id)
            return document
        except Exception as exc:
            logger.exception("文档入库失败：doc=%s", document_id)
            db.rollback()
            current = db.get(Document, document_id)
            if current is not None:
                current.status = "failed"
                current.progress = 0
                current.error_message = truncate(str(exc), 900)
                current.chunk_count = 0
                db.commit()
                try:
                    self.vector_store.delete_document(document_id)
                except Exception:
                    logger.warning("清理失败文档向量失败", exc_info=True)
            raise
