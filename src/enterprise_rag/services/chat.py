"""流式问答业务：检索 -> Prompt -> DeepSeek -> 持久化。"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from typing import Any

from sqlalchemy.orm import Session

from ..config import Settings
from ..models import ChatMessage, ChatSession, KnowledgeBase
from ..ports import LLM, Embedder, LLMUnavailable, VectorStore, VectorStoreUnavailable
from ..schemas import ChatRequestIn
from ..utils import truncate, utcnow
from .prompt import build_messages
from .retrieval import RetrievalService

logger = logging.getLogger(__name__)

REFUSAL_TEXT = (
    "根据现有知识库无法确定这个问题的答案。\n\n"
    "可能的原因：所选知识库中没有相关内容，或问题表述与资料差异较大。"
    "请尝试补充关键词、换一个知识库，或先请管理员上传相关资料。"
)


class ChatService:
    def __init__(
        self,
        settings: Settings,
        db_factory,
        vector_store: VectorStore,
        embedder: Embedder,
        llm: LLM,
    ) -> None:
        self.settings = settings
        self.db_factory = db_factory
        self.vector_store = vector_store
        self.embedder = embedder
        self.llm = llm
        self.retrieval = RetrievalService(settings, vector_store, embedder)

    def _history(self, db: Session, session_id: str, rounds: int) -> list[dict[str, str]]:
        if rounds <= 0:
            return []
        rows = (
            db.query(ChatMessage)
            .filter(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc())
            .limit(rounds * 2)
            .all()
        )
        rows.reverse()
        return [
            {"role": message.role, "content": message.content}
            for message in rows
            if message.role == "user" or (message.role == "assistant" and message.status == "ok")
        ]

    def stream(
        self,
        session_id: str,
        user_id: str,
        payload: ChatRequestIn,
        request_id: str = "-",
    ) -> Iterator[dict[str, Any]]:
        db = self.db_factory()
        assistant: ChatMessage | None = None
        answer = ""
        completed = False
        try:
            session = db.get(ChatSession, session_id)
            if session is None or session.user_id != user_id:
                yield _error("NOT_FOUND", "会话不存在或无权访问。", request_id)
                return
            kbs = db.query(KnowledgeBase).filter(KnowledgeBase.id.in_(payload.kb_ids)).all()
            if not kbs:
                yield _error("NO_KNOWLEDGE_BASE", "请选择至少一个有效知识库。", request_id)
                return

            history = self._history(db, session_id, payload.history_rounds)
            user_message = ChatMessage(
                session_id=session_id,
                role="user",
                content=payload.content,
                status="ok",
                model=self.settings.deepseek_model,
                params={},
            )
            db.add(user_message)
            if not session.title or session.title == "新对话":
                session.title = truncate(payload.content.replace("\n", " ").strip(), 20)
            session.settings = {
                "kb_ids": payload.kb_ids,
                "temperature": payload.temperature,
                "top_p": payload.top_p,
                "max_tokens": payload.max_tokens,
                "history_rounds": payload.history_rounds,
            }
            session.updated_at = utcnow()
            db.commit()
            db.refresh(user_message)

            assistant = ChatMessage(
                session_id=session_id,
                role="assistant",
                content="",
                citations=[],
                status="streaming",
                model=self.settings.deepseek_model,
                params={
                    "temperature": payload.temperature,
                    "top_p": payload.top_p,
                    "max_tokens": payload.max_tokens,
                    "history_rounds": payload.history_rounds,
                },
            )
            db.add(assistant)
            db.commit()
            db.refresh(assistant)

            yield {
                "event": "meta",
                "data": {
                    "session_id": session_id,
                    "message_id": assistant.id,
                    "request_id": request_id,
                    "model": self.settings.deepseek_model,
                },
            }
            yield {"event": "ping", "data": {"ts": utcnow().isoformat()}}

            try:
                citations = self.retrieval.search(db, payload.kb_ids, payload.content)
            except VectorStoreUnavailable as exc:
                raise exc
            assistant.citations = citations
            db.commit()
            yield {"event": "citations", "data": {"items": citations}}

            if not citations:
                answer = REFUSAL_TEXT
                assistant.content = answer
                assistant.status = "ok"
                db.commit()
                completed = True
                yield {"event": "delta", "data": {"text": answer}}
                yield {
                    "event": "done",
                    "data": {"message_id": assistant.id, "finish_reason": "stop", "usage": None},
                }
                return

            messages = build_messages(
                payload.content,
                citations,
                history,
                max_history_chars=self.settings.history_max_chars,
            )
            usage: dict[str, Any] | None = None
            finish_reason = "stop"
            for event in self.llm.stream_chat(
                messages,
                temperature=payload.temperature,
                top_p=payload.top_p,
                max_tokens=payload.max_tokens,
            ):
                if event.get("type") == "delta":
                    text = str(event.get("text", ""))
                    if text:
                        answer += text
                        yield {"event": "delta", "data": {"text": text}}
                elif event.get("type") == "done":
                    usage = event.get("usage")
                    finish_reason = str(event.get("finish_reason") or "stop")

            assistant.content = answer
            assistant.status = "ok"
            params = dict(assistant.params or {})
            params["usage"] = usage
            assistant.params = params
            db.commit()
            completed = True
            yield {
                "event": "done",
                "data": {
                    "message_id": assistant.id,
                    "finish_reason": finish_reason,
                    "usage": usage,
                },
            }
        except GeneratorExit:
            if assistant is not None and not completed:
                assistant.content = answer
                assistant.status = "aborted"
                db.commit()
            raise
        except LLMUnavailable as exc:
            logger.warning("LLM 不可用：%s", exc)
            _mark_error(db, assistant, answer, str(exc))
            yield _error("LLM_UNAVAILABLE", str(exc), request_id)
        except VectorStoreUnavailable as exc:
            logger.warning("向量库不可用：%s", exc)
            _mark_error(db, assistant, answer, str(exc))
            yield _error("VECTOR_STORE_UNAVAILABLE", "向量库不可用，请稍后重试。", request_id)
        except Exception as exc:  # noqa: BLE001
            logger.exception("问答失败：session=%s", session_id)
            _mark_error(db, assistant, answer, str(exc))
            yield _error("INTERNAL", "问答失败，请稍后重试。", request_id)
        finally:
            db.close()


def _mark_error(db: Session, assistant: ChatMessage | None, answer: str, message: str) -> None:
    if assistant is None:
        return
    try:
        assistant.content = answer
        assistant.status = "error"
        assistant.error_message = truncate(message, 900)
        db.commit()
    except Exception:
        logger.warning("保存问答错误状态失败", exc_info=True)


def _error(code: str, message: str, request_id: str) -> dict[str, Any]:
    return {
        "event": "error",
        "data": {"code": code, "message": message, "request_id": request_id},
    }
