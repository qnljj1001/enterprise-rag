"""只读 Wiki：由文档块确定性拼装 Markdown。"""

from __future__ import annotations

import json

from sqlalchemy.orm import Session

from ..models import Document, DocumentChunk, KnowledgeBase
from ..utils import utcnow


def _q(value: object) -> str:
    return json.dumps(str(value), ensure_ascii=False)


def _frontmatter(items: dict[str, object]) -> str:
    lines = ["---"]
    for key, value in items.items():
        lines.append(f"{key}: {_q(value)}")
    lines.append("---")
    return "\n".join(lines)


def build_document_wiki(db: Session, document_id: str) -> tuple[str, str]:
    document = db.get(Document, document_id)
    if document is None:
        raise ValueError("文档不存在")
    kb = db.get(KnowledgeBase, document.kb_id)
    chunks = (
        db.query(DocumentChunk)
        .filter(DocumentChunk.document_id == document.id)
        .order_by(DocumentChunk.chunk_index)
        .all()
    )
    title = f"{document.filename} · Wiki"
    lines = [
        _frontmatter(
            {
                "kb_id": document.kb_id,
                "doc_id": document.id,
                "title": document.filename,
                "source_file": document.filename,
                "chunk_count": len(chunks),
                "generated_at": utcnow().isoformat(),
            }
        ),
        "",
        f"# {document.filename}",
        "",
        f"> 知识库：{kb.name if kb else document.kb_id}｜文件类型：{document.file_type}｜"
        f"片段数：{len(chunks)}｜状态：{document.status}",
        "",
    ]
    for chunk in chunks:
        page = f" · 第 {chunk.page_no} 页" if chunk.page_no else ""
        lines.extend(
            [
                f"## 片段 {chunk.chunk_index + 1}{page}",
                "",
                chunk.content.strip(),
                "",
            ]
        )
    return title, "\n".join(lines).strip() + "\n"


def build_kb_wiki(db: Session, kb_id: str) -> tuple[str, str]:
    kb = db.get(KnowledgeBase, kb_id)
    if kb is None:
        raise ValueError("知识库不存在")
    documents = (
        db.query(Document).filter(Document.kb_id == kb.id).order_by(Document.created_at).all()
    )
    title = f"{kb.name} · Wiki"
    lines = [
        _frontmatter(
            {
                "kb_id": kb.id,
                "title": kb.name,
                "retrieval_mode": kb.retrieval_mode,
                "chunk_size": kb.default_chunk_size,
                "chunk_overlap": kb.default_chunk_overlap,
                "generated_at": utcnow().isoformat(),
            }
        ),
        "",
        f"# {kb.name}",
        "",
        kb.description or "（暂无描述）",
        "",
        f"> 检索模式：{kb.retrieval_mode}｜文档数：{len(documents)}",
        "",
        "## 文档索引",
        "",
    ]
    for document in documents:
        lines.append(f"- {document.filename}（{document.chunk_count} 块，{document.status}）")
    if not documents:
        lines.append("- （暂无文档）")
    return title, "\n".join(lines).strip() + "\n"
