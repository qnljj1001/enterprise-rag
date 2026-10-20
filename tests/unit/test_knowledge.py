from __future__ import annotations

from fastapi.testclient import TestClient

from tests.helpers import create_kb, process_document, upload_md


def test_admin_creates_kb_and_user_lists_it(
    client: TestClient, admin_headers, user_headers
) -> None:
    kb = create_kb(client, admin_headers)
    assert kb["name"] == "政策测试库"

    response = client.get("/api/v1/knowledge-bases", headers=user_headers)
    assert response.status_code == 200
    assert any(item["id"] == kb["id"] for item in response.json())

    denied = client.post(
        "/api/v1/admin/knowledge-bases",
        headers=user_headers,
        json={"name": "不应创建"},
    )
    assert denied.status_code == 403


def test_upload_process_chunks_wiki_and_edit(client: TestClient, app, admin_headers) -> None:
    kb = create_kb(client, admin_headers)
    upload = upload_md(client, admin_headers, kb["id"])
    assert upload.status_code == 202, upload.text
    doc = upload.json()
    assert doc["status"] == "pending"

    process_document(app, doc["id"])

    detail = client.get(f"/api/v1/admin/documents/{doc['id']}", headers=admin_headers)
    assert detail.status_code == 200
    assert detail.json()["status"] == "ready"
    assert detail.json()["chunk_count"] > 0

    chunks = client.get(f"/api/v1/admin/documents/{doc['id']}/chunks", headers=admin_headers)
    assert chunks.status_code == 200
    items = chunks.json()["items"]
    assert items
    assert "服务期" in items[0]["content"] or "西部计划" in items[0]["content"]
    assert app.state.vector_store.rows

    wiki = client.get(f"/api/v1/admin/documents/{doc['id']}/wiki", headers=admin_headers)
    assert wiki.status_code == 200
    assert "source_file" in wiki.json()["markdown"]
    assert "片段 1" in wiki.json()["markdown"]

    kb_wiki = client.get(f"/api/v1/admin/knowledge-bases/{kb['id']}/wiki", headers=admin_headers)
    assert kb_wiki.status_code == 200
    assert "文档索引" in kb_wiki.json()["markdown"]

    chunk = items[0]
    updated = client.patch(
        f"/api/v1/admin/chunks/{chunk['id']}",
        headers=admin_headers,
        json={"content": "这是编辑后的测试内容，服务期为 2 年。"},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["content"].startswith("这是编辑后的测试内容")
    assert app.state.vector_store.rows[chunk["id"]]["content"].startswith("这是编辑后的测试内容")

    deleted = client.delete(f"/api/v1/admin/chunks/{chunk['id']}", headers=admin_headers)
    assert deleted.status_code == 204
    assert chunk["id"] not in app.state.vector_store.rows


def test_duplicate_upload_rejected(client: TestClient, admin_headers) -> None:
    kb = create_kb(client, admin_headers)
    first = upload_md(client, admin_headers, kb["id"])
    assert first.status_code == 202
    second = upload_md(client, admin_headers, kb["id"])
    assert second.status_code == 409
    assert second.json()["detail"]["code"] == "DOCUMENT_DUPLICATE"


def test_user_cannot_upload_or_preview(client: TestClient, admin_headers, user_headers) -> None:
    kb = create_kb(client, admin_headers)
    upload = upload_md(client, user_headers, kb["id"])
    assert upload.status_code == 403
    response = client.get(
        f"/api/v1/admin/knowledge-bases/{kb['id']}/documents", headers=user_headers
    )
    assert response.status_code == 403


def test_delete_document_removes_vectors(client: TestClient, app, admin_headers) -> None:
    kb = create_kb(client, admin_headers)
    doc = upload_md(client, admin_headers, kb["id"]).json()
    process_document(app, doc["id"])
    assert app.state.vector_store.rows
    response = client.delete(f"/api/v1/admin/documents/{doc['id']}", headers=admin_headers)
    assert response.status_code == 204
    assert not app.state.vector_store.rows
