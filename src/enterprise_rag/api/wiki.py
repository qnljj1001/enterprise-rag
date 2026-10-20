"""只读 Wiki 接口（管理员）。"""

from __future__ import annotations

import urllib.parse

from fastapi import APIRouter, Depends, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from ..models import User
from ..schemas import WikiOut
from ..services.wiki import build_document_wiki, build_kb_wiki
from ..utils import utcnow
from .deps import get_db, require_admin

router = APIRouter(prefix="/api/v1/admin", tags=["Wiki"])


def _download(markdown: str, filename: str) -> PlainTextResponse:
    quoted = urllib.parse.quote(filename)
    return PlainTextResponse(
        markdown,
        media_type="text/markdown; charset=utf-8",
        headers={
            "Content-Disposition": f"attachment; filename=\"wiki.md\"; filename*=UTF-8''{quoted}"
        },
    )


@router.get("/documents/{doc_id}/wiki")
def document_wiki(
    doc_id: str,
    download: bool = Query(default=False),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    title, markdown = build_document_wiki(db, doc_id)
    if download:
        return _download(markdown, f"{title}.md")
    return WikiOut(title=title, markdown=markdown, generated_at=utcnow())


@router.get("/knowledge-bases/{kb_id}/wiki")
def knowledge_base_wiki(
    kb_id: str,
    download: bool = Query(default=False),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    title, markdown = build_kb_wiki(db, kb_id)
    if download:
        return _download(markdown, f"{title}.md")
    return WikiOut(title=title, markdown=markdown, generated_at=utcnow())
