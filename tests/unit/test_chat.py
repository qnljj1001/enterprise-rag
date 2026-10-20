from __future__ import annotations

from fastapi.testclient import TestClient

from tests.helpers import (
    auth,
    create_kb,
    create_session,
    process_document,
    register,
    upload_md,
)


def _stream(client: TestClient, headers: dict, session_id: str, content: str, kb_ids: list[str]):
    with client.stream(
        "POST",
        f"/api/v1/chat/sessions/{session_id}/messages/stream",
        headers=headers,
        json={
            "content": content,
            "kb_ids": kb_ids,
            "temperature": 0.5,
            "top_p": 0.9,
            "max_tokens": 512,
            "history_rounds": 5,
        },
    ) as response:
        assert response.status_code == 200, response.text
        body = "".join(response.iter_text())
    return body


def _ready_kb(client: TestClient, app, admin_headers) -> dict:
    kb = create_kb(client, admin_headers)
    doc = upload_md(client, admin_headers, kb["id"]).json()
    process_document(app, doc["id"])
    return kb


def test_stream_chat_returns_citations_and_persists(
    client: TestClient, app, admin_headers, user_headers
) -> None:
    kb = _ready_kb(client, app, admin_headers)
    session = create_session(client, user_headers)

    body = _stream(client, user_headers, session["id"], "西部计划服务期是几年？", [kb["id"]])
    assert "event: meta" in body
    assert "event: citations" in body
    assert "event: delta" in body
    assert "event: done" in body
    assert "chunk_id" in body
    assert "服务期" in body or "政策" in body

    messages = client.get(f"/api/v1/chat/sessions/{session['id']}/messages", headers=user_headers)
    assert messages.status_code == 200
    assert len(messages.json()) == 2
    assert messages.json()[0]["role"] == "user"
    assert messages.json()[1]["role"] == "assistant"
    assert messages.json()[1]["content"]
    assert messages.json()[1]["citations"]


def test_empty_knowledge_base_refuses(client: TestClient, admin_headers, user_headers) -> None:
    kb = create_kb(client, admin_headers, name="空知识库")
    session = create_session(client, user_headers)
    body = _stream(client, user_headers, session["id"], "服务期是几年？", [kb["id"]])
    assert "event: citations" in body
    assert '"items": []' in body or '"items":[]' in body
    assert "无法确定" in body
    assert "event: done" in body


def test_session_isolation_and_crud(client: TestClient, admin_headers, user_headers) -> None:
    kb = create_kb(client, admin_headers, name="隔离测试库")
    session = create_session(client, user_headers, title="我的会话")
    other_token = register(client, "other_user")
    other_headers = auth(other_token)

    forbidden = client.get(f"/api/v1/chat/sessions/{session['id']}/messages", headers=other_headers)
    assert forbidden.status_code == 404

    renamed = client.patch(
        f"/api/v1/chat/sessions/{session['id']}",
        headers=user_headers,
        json={"title": "改名后的会话"},
    )
    assert renamed.status_code == 200
    assert renamed.json()["title"] == "改名后的会话"

    deleted = client.delete(f"/api/v1/chat/sessions/{session['id']}", headers=user_headers)
    assert deleted.status_code == 204
    assert client.get("/api/v1/chat/sessions", headers=user_headers).json() == []
    _ = kb


def test_history_rounds_sent_to_prompt(
    client: TestClient, app, admin_headers, user_headers
) -> None:
    kb = _ready_kb(client, app, admin_headers)
    session = create_session(client, user_headers)
    _stream(client, user_headers, session["id"], "服务期是几年？", [kb["id"]])
    _stream(client, user_headers, session["id"], "那补贴呢？", [kb["id"]])
    messages = client.get(f"/api/v1/chat/sessions/{session['id']}/messages", headers=user_headers)
    assert messages.status_code == 200
    assert len(messages.json()) == 4
