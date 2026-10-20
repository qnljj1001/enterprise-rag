"""知识库接口：用户只读列表 + 管理员 CRUD。"""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..config import Settings
from ..models import Document, DocumentChunk, KnowledgeBase, User
from ..schemas import KBCreate, KBOut, KBUpdate
from ..utils import utcnow
from .deps import get_current_user, get_db, get_settings, get_vector_store, require_admin

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/knowledge-bases", tags=["知识库"])
admin_router = APIRouter(prefix="/api/v1/admin/knowledge-bases", tags=["知识库管理"])


def _kb_out(db: Session, kb: KnowledgeBase) -> KBOut:
    document_count = db.query(func.count(Document.id)).filter(Document.kb_id == kb.id).scalar() or 0
    chunk_count = (
        db.query(func.count(DocumentChunk.id)).filter(DocumentChunk.kb_id == kb.id).scalar() or 0
    )
    return KBOut(
        id=kb.id,
        name=kb.name,
        description=kb.description,
        default_chunk_size=kb.default_chunk_size,
        default_chunk_overlap=kb.default_chunk_overlap,
        retrieval_mode=kb.retrieval_mode,
        embedding_model=kb.embedding_model,
        embedding_dim=kb.embedding_dim,
        document_count=int(document_count),
        chunk_count=int(chunk_count),
        created_at=kb.created_at,
        updated_at=kb.updated_at,
    )


def _get_kb(db: Session, kb_id: str) -> KnowledgeBase:
    kb = db.get(KnowledgeBase, kb_id)
    if kb is None:
        raise HTTPException(
            status_code=404, detail={"code": "NOT_FOUND", "message": "知识库不存在。"}
        )
    return kb


@router.get("", response_model=list[KBOut])
def list_available(
    db: Session = Depends(get_db), _: User = Depends(get_current_user)
) -> list[KBOut]:
    rows = db.query(KnowledgeBase).order_by(KnowledgeBase.created_at.desc()).all()
    return [_kb_out(db, kb) for kb in rows]


@router.get("/{kb_id}", response_model=KBOut)
def get_available(
    kb_id: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)
) -> KBOut:
    return _kb_out(db, _get_kb(db, kb_id))


@admin_router.get("", response_model=list[KBOut])
def admin_list(db: Session = Depends(get_db), _: User = Depends(require_admin)) -> list[KBOut]:
    rows = db.query(KnowledgeBase).order_by(KnowledgeBase.created_at.desc()).all()
    return [_kb_out(db, kb) for kb in rows]


@admin_router.post("", response_model=KBOut, status_code=201)
def create_kb(
    payload: KBCreate,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    admin: User = Depends(require_admin),
) -> KBOut:
    kb = KnowledgeBase(
        name=payload.name.strip(),
        description=payload.description.strip(),
        default_chunk_size=payload.default_chunk_size,
        default_chunk_overlap=payload.default_chunk_overlap,
        retrieval_mode=payload.retrieval_mode,
        embedding_model=settings.embedding_model,
        embedding_dim=settings.embedding_dim,
        created_by=admin.id,
    )
    db.add(kb)
    db.commit()
    db.refresh(kb)
    logger.info("创建知识库：%s (%s)", kb.name, kb.id)
    return _kb_out(db, kb)


@admin_router.get("/{kb_id}", response_model=KBOut)
def admin_get(kb_id: str, db: Session = Depends(get_db), _: User = Depends(require_admin)) -> KBOut:
    return _kb_out(db, _get_kb(db, kb_id))


@admin_router.patch("/{kb_id}", response_model=KBOut)
def update_kb(
    kb_id: str,
    payload: KBUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> KBOut:
    kb = _get_kb(db, kb_id)
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        if value is not None:
            setattr(kb, key, value.strip() if isinstance(value, str) else value)
    kb.updated_at = utcnow()
    db.commit()
    db.refresh(kb)
    return _kb_out(db, kb)


@admin_router.delete("/{kb_id}", status_code=204)
def delete_kb(
    kb_id: str,
    db: Session = Depends(get_db),
    vector_store=Depends(get_vector_store),
    _: User = Depends(require_admin),
) -> None:
    kb = _get_kb(db, kb_id)
    documents = db.query(Document).filter(Document.kb_id == kb.id).all()
    try:
        vector_store.delete_knowledge_base(kb.id)
    except Exception:
        logger.warning("删除知识库向量失败：%s", kb.id, exc_info=True)
    for document in documents:
        try:
            Path(document.stored_path).unlink(missing_ok=True)
        except Exception:
            logger.warning("删除文件失败：%s", document.stored_path, exc_info=True)
    db.delete(kb)
    db.commit()
    logger.info("删除知识库：%s", kb_id)
