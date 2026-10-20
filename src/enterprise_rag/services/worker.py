"""后台入库 worker：单线程队列，避免阻塞请求。"""

from __future__ import annotations

import logging
import queue
import threading
from collections.abc import Callable

from sqlalchemy.orm import Session

from ..config import Settings
from ..models import Document
from ..ports import Embedder, VectorStore
from .ingestion import IngestionService

logger = logging.getLogger(__name__)

PROCESSING_STATUSES = ("parsing", "chunking", "embedding", "indexing")


class IngestWorker:
    def __init__(
        self,
        settings: Settings,
        db_factory: Callable[[], Session],
        vector_store: VectorStore,
        embedder: Embedder,
    ) -> None:
        self.settings = settings
        self.db_factory = db_factory
        self.service = IngestionService(settings, vector_store, embedder)
        self.queue: queue.Queue[str | None] = queue.Queue()
        self._thread: threading.Thread | None = None
        self._stopping = False

    def start(self) -> None:
        if self._thread is not None:
            return
        self._thread = threading.Thread(target=self._run, name="ingest-worker", daemon=True)
        self._thread.start()
        logger.info("入库 worker 已启动")

    def submit(self, document_id: str) -> None:
        self.queue.put(document_id)

    def stop(self) -> None:
        self._stopping = True
        self.queue.put(None)
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None
        logger.info("入库 worker 已停止")

    def reset_stale(self) -> int:
        db = self.db_factory()
        try:
            rows = db.query(Document).filter(Document.status.in_(PROCESSING_STATUSES)).all()
            for document in rows:
                document.status = "failed"
                document.progress = 0
                document.error_message = "服务重启导致入库中断，请重新解析。"
            db.commit()
            if rows:
                logger.warning("已重置 %s 个中断的入库任务", len(rows))
            return len(rows)
        finally:
            db.close()

    def _run(self) -> None:
        while not self._stopping:
            document_id = self.queue.get()
            if document_id is None:
                break
            db = self.db_factory()
            try:
                self.service.process_document(db, document_id)
            except Exception:
                logger.exception("worker 处理文档失败：%s", document_id)
            finally:
                db.close()
                self.queue.task_done()
