"""文档与文档块管理接口（管理员）。"""

from __future__ import annotations

import hashlib
import logging
import threading
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from sqlalchemy.orm import Session

from ..config import Settings
from ..ingest.parsers import SUPPORTED_EXTENSIONS
from ..models import Document, DocumentChunk, KnowledgeBase, User
from ..schemas import (
    ChunkListOut,
    ChunkOut,
    ChunkUpdateIn,
    DocumentListOut,
    DocumentOut,
    ReparseIn,
)
from ..utils import new_id, safe_filename, utcnow
from .deps import get_db, get_embedder, get_settings, get_vector_store, require_admin

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/admin", tags=["文档管理"])


def _safe_flush(vector_store) -> None:
    try:
        vector_store.flush()
    except Exception:
        logger.warning("Milvus flush 失败，等待自动 flush", exc_info=True)


def _get_kb(db: Session, kb_id: str) -> KnowledgeBase:
    kb = db.get(KnowledgeBase, kb_id)
    if kb is None:
        raise HTTPException(
            status_code=404, detail={"code": "NOT_FOUND", "message": "知识库不存在。"}
        )
    return kb


def _get_document(db: Session, doc_id: str) -> Document:
    document = db.get(Document, doc_id)
    if document is None:
        raise HTTPException(
            status_code=404, detail={"code": "NOT_FOUND", "message": "文档不存在。"}
        )
    return document


@router.get("/knowledge-bases/{kb_id}/documents", response_model=DocumentListOut)
def list_documents(
    kb_id: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> DocumentListOut:
    _get_kb(db, kb_id)
    query = db.query(Document).filter(Document.kb_id == kb_id)
    if status:
        query = query.filter(Document.status == status)
    total = query.count()
    rows = (
        query.order_by(Document.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return DocumentListOut(
        items=[DocumentOut.model_validate(item) for item in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/knowledge-bases/{kb_id}/documents",
    response_model=DocumentOut,
    status_code=202,
)
def upload_document(
    kb_id: str,
    request: Request,
    file: UploadFile = File(...),
    chunk_size: int | None = Form(default=None),
    chunk_overlap: int | None = Form(default=None),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _: User = Depends(require_admin),
) -> DocumentOut:
    kb = _get_kb(db, kb_id)
    original = safe_filename(file.filename or "document")
    suffix = Path(original).suffix.lower()
    file_type = SUPPORTED_EXTENSIONS.get(suffix)
    if file_type is None:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "UNSUPPORTED_FILE_TYPE",
                "message": (
                    "不支持该文件类型。支持 PDF、PPTX、Markdown、图片（PNG/JPG/WEBP）和 DOCX。"
                ),
            },
        )

    size = chunk_size if chunk_size is not None else kb.default_chunk_size
    overlap = chunk_overlap if chunk_overlap is not None else kb.default_chunk_overlap
    if not (100 <= size <= 4000):
        raise HTTPException(
            status_code=422,
            detail={"code": "VALIDATION_FAILED", "message": "切块大小需在 100–4000 之间。"},
        )
    if not (0 <= overlap < size):
        raise HTTPException(
            status_code=422,
            detail={"code": "VALIDATION_FAILED", "message": "重叠大小必须小于切块大小。"},
        )

    directory = Path(settings.upload_dir).resolve() / kb.id
    directory.mkdir(parents=True, exist_ok=True)
    stored_name = f"{new_id()}{suffix}"
    stored_path = directory / stored_name
    max_bytes = settings.max_upload_mb * 1024 * 1024
    digest = hashlib.sha256()
    total = 0
    try:
        with stored_path.open("wb") as output:
            while True:
                block = file.file.read(1024 * 1024)
                if not block:
                    break
                total += len(block)
                if total > max_bytes:
                    raise HTTPException(
                        status_code=413,
                        detail={
                            "code": "FILE_TOO_LARGE",
                            "message": f"文件超过 {settings.max_upload_mb} MB 限制。",
                        },
                    )
                digest.update(block)
                output.write(block)
    except HTTPException:
        stored_path.unlink(missing_ok=True)
        raise
    except Exception as exc:
        stored_path.unlink(missing_ok=True)
        logger.exception("保存上传文件失败")
        raise HTTPException(
            status_code=500, detail={"code": "INTERNAL", "message": "保存文件失败。"}
        ) from exc
    finally:
        file.file.close()

    if total == 0:
        stored_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=400, detail={"code": "VALIDATION_FAILED", "message": "文件为空。"}
        )
    sha = digest.hexdigest()
    duplicate = db.query(Document).filter(Document.kb_id == kb.id, Document.sha256 == sha).first()
    if duplicate is not None:
        stored_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=409,
            detail={
                "code": "DOCUMENT_DUPLICATE",
                "message": f"该文件已存在于知识库中：{duplicate.filename}",
            },
        )

    document = Document(
        kb_id=kb.id,
        filename=original,
        stored_path=str(stored_path),
        file_type=file_type,
        size_bytes=total,
        sha256=sha,
        chunk_size=size,
        chunk_overlap=overlap,
        status="pending",
        progress=0,
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    worker = getattr(request.app.state, "worker", None)
    if worker is not None:
        worker.submit(document.id)
    logger.info("上传文档：%s doc=%s kb=%s", original, document.id, kb.id)
    return DocumentOut.model_validate(document)


@router.get("/documents/{doc_id}", response_model=DocumentOut)
def get_document(
    doc_id: str, db: Session = Depends(get_db), _: User = Depends(require_admin)
) -> DocumentOut:
    return DocumentOut.model_validate(_get_document(db, doc_id))


@router.delete("/documents/{doc_id}", status_code=204)
def delete_document(
    doc_id: str,
    db: Session = Depends(get_db),
    vector_store=Depends(get_vector_store),
    _: User = Depends(require_admin),
) -> None:
    document = _get_document(db, doc_id)
    try:
        vector_store.delete_document(document.id)
    except Exception:
        logger.warning("删除文档向量失败：%s", document.id, exc_info=True)
    try:
        Path(document.stored_path).unlink(missing_ok=True)
    except Exception:
        logger.warning("删除文件失败：%s", document.stored_path, exc_info=True)
    db.delete(document)
    db.commit()
    logger.info("删除文档：%s", doc_id)


@router.post("/documents/{doc_id}/reparse", response_model=DocumentOut, status_code=202)
def reparse_document(
    doc_id: str,
    payload: ReparseIn,
    request: Request,
    db: Session = Depends(get_db),
    vector_store=Depends(get_vector_store),
    _: User = Depends(require_admin),
) -> DocumentOut:
    document = _get_document(db, doc_id)
    data = payload.model_dump(exclude_unset=True)
    if data.get("chunk_size") is not None:
        document.chunk_size = int(data["chunk_size"])
    if data.get("chunk_overlap") is not None:
        document.chunk_overlap = int(data["chunk_overlap"])
    if document.chunk_overlap >= document.chunk_size:
        raise HTTPException(
            status_code=422,
            detail={"code": "VALIDATION_FAILED", "message": "重叠大小必须小于切块大小。"},
        )
    old_ids = [
        row[0]
        for row in db.query(DocumentChunk.id).filter(DocumentChunk.document_id == document.id).all()
    ]
    if old_ids:
        try:
            vector_store.delete_chunks(old_ids)
        except Exception:
            logger.warning("重新解析前清理向量失败", exc_info=True)
        db.query(DocumentChunk).filter(DocumentChunk.document_id == document.id).delete()
    document.status = "pending"
    document.progress = 0
    document.chunk_count = 0
    document.error_message = None
    document.updated_at = utcnow()
    db.commit()
    db.refresh(document)
    worker = getattr(request.app.state, "worker", None)
    if worker is not None:
        worker.submit(document.id)
    logger.info("重新解析文档：%s", doc_id)
    return DocumentOut.model_validate(document)


@router.get("/documents/{doc_id}/chunks", response_model=ChunkListOut)
def list_chunks(
    doc_id: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    q: str | None = Query(default=None, max_length=200),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> ChunkListOut:
    _get_document(db, doc_id)
    query = db.query(DocumentChunk).filter(DocumentChunk.document_id == doc_id)
    if q:
        query = query.filter(DocumentChunk.content.contains(q))
    total = query.count()
    rows = (
        query.order_by(DocumentChunk.chunk_index)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return ChunkListOut(
        items=[ChunkOut.model_validate(item) for item in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.patch("/chunks/{chunk_id}", response_model=ChunkOut)
def update_chunk(
    chunk_id: str,
    payload: ChunkUpdateIn,
    db: Session = Depends(get_db),
    vector_store=Depends(get_vector_store),
    embedder=Depends(get_embedder),
    _: User = Depends(require_admin),
) -> ChunkOut:
    chunk = db.get(DocumentChunk, chunk_id)
    if chunk is None:
        raise HTTPException(
            status_code=404, detail={"code": "NOT_FOUND", "message": "文档块不存在。"}
        )
    content = payload.content.strip()
    if not content:
        raise HTTPException(
            status_code=422, detail={"code": "VALIDATION_FAILED", "message": "内容不能为空。"}
        )
    try:
        vector = embedder.embed([content])[0]
        vector_store.insert_chunks(
            [
                {
                    "chunk_id": chunk.id,
                    "kb_id": chunk.kb_id,
                    "document_id": chunk.document_id,
                    "chunk_index": chunk.chunk_index,
                    "page_no": chunk.page_no or 0,
                    "created_at": int(utcnow().timestamp()),
                    "content": content,
                    "embedding": vector,
                }
            ],
            flush=False,
        )
        threading.Thread(target=_safe_flush, args=(vector_store,), daemon=True).start()
    except Exception as exc:
        logger.exception("更新文档块向量失败：%s", chunk_id)
        raise HTTPException(
            status_code=503,
            detail={"code": "VECTOR_STORE_UNAVAILABLE", "message": "向量库更新失败，请稍后重试。"},
        ) from exc
    chunk.content = content
    chunk.updated_at = utcnow()
    db.commit()
    db.refresh(chunk)
    return ChunkOut.model_validate(chunk)


@router.delete("/chunks/{chunk_id}", status_code=204)
def delete_chunk(
    chunk_id: str,
    db: Session = Depends(get_db),
    vector_store=Depends(get_vector_store),
    _: User = Depends(require_admin),
) -> None:
    chunk = db.get(DocumentChunk, chunk_id)
    if chunk is None:
        raise HTTPException(
            status_code=404, detail={"code": "NOT_FOUND", "message": "文档块不存在。"}
        )
    try:
        vector_store.delete_chunks([chunk.id])
    except Exception:
        logger.warning("删除文档块向量失败：%s", chunk_id, exc_info=True)
    db.delete(chunk)
    db.commit()
    logger.info("删除文档块：%s", chunk_id)
