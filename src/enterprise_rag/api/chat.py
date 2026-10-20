"""对话接口：会话 CRUD、历史消息、SSE 流式问答。"""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import case
from sqlalchemy.orm import Session

from ..models import ChatMessage, ChatSession, KnowledgeBase, User
from ..schemas import (
    ChatRequestIn,
    MessageOut,
    SessionCreateIn,
    SessionOut,
    SessionUpdateIn,
)
from ..services.chat import ChatService
from ..utils import utcnow
from .deps import get_current_user, get_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/chat", tags=["对话"])


def _session_for(db: Session, session_id: str, user_id: str) -> ChatSession:
    session = db.get(ChatSession, session_id)
    if session is None or session.user_id != user_id:
        raise HTTPException(
            status_code=404, detail={"code": "NOT_FOUND", "message": "会话不存在。"}
        )
    return session


@router.get("/sessions", response_model=list[SessionOut])
def list_sessions(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> list[SessionOut]:
    rows = (
        db.query(ChatSession)
        .filter(ChatSession.user_id == user.id)
        .order_by(ChatSession.updated_at.desc())
        .all()
    )
    return [SessionOut.model_validate(item) for item in rows]


@router.post("/sessions", response_model=SessionOut, status_code=201)
def create_session(
    payload: SessionCreateIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SessionOut:
    session = ChatSession(
        user_id=user.id,
        title=payload.title.strip() or "新对话",
        settings=payload.settings,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return SessionOut.model_validate(session)


@router.patch("/sessions/{session_id}", response_model=SessionOut)
def update_session(
    session_id: str,
    payload: SessionUpdateIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SessionOut:
    session = _session_for(db, session_id, user.id)
    if payload.title is not None:
        session.title = payload.title.strip()
        session.updated_at = utcnow()
        db.commit()
        db.refresh(session)
    return SessionOut.model_validate(session)


@router.delete("/sessions/{session_id}", status_code=204)
def delete_session(
    session_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    session = _session_for(db, session_id, user.id)
    db.delete(session)
    db.commit()


@router.get("/sessions/{session_id}/messages", response_model=list[MessageOut])
def list_messages(
    session_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[MessageOut]:
    _session_for(db, session_id, user.id)
    rows = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(
            ChatMessage.created_at,
            case((ChatMessage.role == "user", 0), else_=1),
            ChatMessage.id,
        )
        .all()
    )
    return [MessageOut.model_validate(item) for item in rows]


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/sessions/{session_id}/messages/stream")
def stream_message(
    session_id: str,
    payload: ChatRequestIn,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    session = _session_for(db, session_id, user.id)
    kb_count = db.query(KnowledgeBase).filter(KnowledgeBase.id.in_(payload.kb_ids)).count()
    if kb_count == 0:
        raise HTTPException(
            status_code=400,
            detail={"code": "NO_KNOWLEDGE_BASE", "message": "请选择至少一个有效知识库。"},
        )
    settings = request.app.state.settings
    app = request.app
    request_id = getattr(request.state, "request_id", "-")

    def generate():
        service = ChatService(
            settings,
            app.state.db.SessionLocal,
            app.state.vector_store,
            app.state.embedder,
            app.state.llm,
        )
        try:
            for event in service.stream(session.id, user.id, payload, request_id):
                yield _sse(event["event"], event["data"])
        except Exception:
            logger.exception("SSE 生成失败：session=%s", session_id)
            yield _sse(
                "error",
                {
                    "code": "INTERNAL",
                    "message": "问答失败，请稍后重试。",
                    "request_id": request_id,
                },
            )

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
