from __future__ import annotations

from datetime import timedelta

from fastapi.testclient import TestClient

from enterprise_rag.models import CaptchaChallenge
from enterprise_rag.utils import utcnow
from tests.helpers import (
    create_kb,
    create_session,
    get_captcha,
    process_document,
    upload_md,
)


def test_captcha_expired(client: TestClient, app) -> None:
    captcha = get_captcha(client)
    db = app.state.db.SessionLocal()
    try:
        challenge = db.get(CaptchaChallenge, captcha["captcha_id"])
        challenge.expires_at = utcnow() - timedelta(seconds=1)
        db.commit()
    finally:
        db.close()
    response = client.post(
        "/api/v1/auth/register",
        json={
            "username": "expired_user",
            "password": "user123456",
            "confirm_password": "user123456",
            "captcha_id": captcha["captcha_id"],
            "captcha_code": captcha["debug_code"],
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "CAPTCHA_INVALID"


def test_unsupported_file_type(client: TestClient, admin_headers) -> None:
    kb = create_kb(client, admin_headers)
    response = client.post(
        f"/api/v1/admin/knowledge-bases/{kb['id']}/documents",
        headers=admin_headers,
        files={"file": ("bad.exe", b"binary", "application/octet-stream")},
    )
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "UNSUPPORTED_FILE_TYPE"


def test_wiki_download(client: TestClient, app, admin_headers) -> None:
    kb = create_kb(client, admin_headers)
    doc = upload_md(client, admin_headers, kb["id"]).json()
    process_document(app, doc["id"])
    response = client.get(
        f"/api/v1/admin/documents/{doc['id']}/wiki?download=1", headers=admin_headers
    )
    assert response.status_code == 200
    assert "text/markdown" in response.headers["content-type"]
    assert response.text.startswith("---")
    assert "source_file" in response.text


def test_no_knowledge_base_selected(client: TestClient, user_headers) -> None:
    session = create_session(client, user_headers)
    response = client.post(
        f"/api/v1/chat/sessions/{session['id']}/messages/stream",
        headers=user_headers,
        json={
            "content": "问题",
            "kb_ids": [],
            "temperature": 0.7,
            "top_p": 0.8,
            "max_tokens": 128,
            "history_rounds": 5,
        },
    )
    assert response.status_code == 422


def test_multi_knowledge_base_retrieval(
    client: TestClient, app, admin_headers, user_headers
) -> None:
    hybrid = create_kb(client, admin_headers, name="混合库")
    dense = create_kb(client, admin_headers, name="稠密库")
    client.patch(
        f"/api/v1/admin/knowledge-bases/{dense['id']}",
        headers=admin_headers,
        json={"retrieval_mode": "dense"},
    )
    doc1 = upload_md(client, admin_headers, hybrid["id"]).json()
    doc2 = upload_md(client, admin_headers, dense["id"]).json()
    process_document(app, doc1["id"])
    process_document(app, doc2["id"])

    session = create_session(client, user_headers)
    with client.stream(
        "POST",
        f"/api/v1/chat/sessions/{session['id']}/messages/stream",
        headers=user_headers,
        json={
            "content": "西部计划服务期是几年？",
            "kb_ids": [hybrid["id"], dense["id"]],
            "temperature": 0.7,
            "top_p": 0.8,
            "max_tokens": 256,
            "history_rounds": 5,
        },
    ) as response:
        body = "".join(response.iter_text())
    assert "混合库" in body
    assert "稠密库" in body
