from __future__ import annotations

from fastapi.testclient import TestClient

from enterprise_rag.services.ingestion import IngestionService

POLICY_MD = """# 西部计划政策说明

## 服务期

西部计划志愿者服务期一般为 1 至 3 年，服务协议一年一签。服务期满且考核合格的，颁发服务证书。

## 生活补贴

志愿者服务期间，中央财政给予一定生活补贴，地方财政可根据当地实际给予配套补贴。具体标准以当年文件为准。

## 社会保险

服务期间，志愿者按规定参加社会保险，具体险种和缴费方式按服务地有关规定执行。

## 期满优惠

服务期满考核合格的志愿者，在考研、公务员招录、就业创业等方面可按规定享受相关优惠政策。
"""


def get_captcha(client: TestClient) -> dict:
    response = client.get("/api/v1/auth/captcha")
    assert response.status_code == 200, response.text
    return response.json()


def login(client: TestClient, username: str, password: str) -> str:
    captcha = get_captcha(client)
    response = client.post(
        "/api/v1/auth/login",
        json={
            "username": username,
            "password": password,
            "captcha_id": captcha["captcha_id"],
            "captcha_code": captcha["debug_code"],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def register(client: TestClient, username: str, password: str = "user123456") -> str:
    captcha = get_captcha(client)
    response = client.post(
        "/api/v1/auth/register",
        json={
            "username": username,
            "password": password,
            "confirm_password": password,
            "captcha_id": captcha["captcha_id"],
            "captcha_code": captcha["debug_code"],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["access_token"]


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def create_kb(client: TestClient, headers: dict, name: str = "政策测试库") -> dict:
    response = client.post(
        "/api/v1/admin/knowledge-bases",
        headers=headers,
        json={
            "name": name,
            "description": "用于单元测试",
            "default_chunk_size": 200,
            "default_chunk_overlap": 20,
            "retrieval_mode": "hybrid",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def upload_md(client: TestClient, headers: dict, kb_id: str, content: str = POLICY_MD):
    return client.post(
        f"/api/v1/admin/knowledge-bases/{kb_id}/documents",
        headers=headers,
        files={"file": ("policy.md", content.encode("utf-8"), "text/markdown")},
        data={"chunk_size": "200", "chunk_overlap": "20"},
    )


def process_document(app, doc_id: str) -> None:
    db = app.state.db.SessionLocal()
    try:
        IngestionService(
            app.state.settings, app.state.vector_store, app.state.embedder
        ).process_document(db, doc_id)
    finally:
        db.close()


def create_session(client: TestClient, headers: dict, title: str = "新对话") -> dict:
    response = client.post(
        "/api/v1/chat/sessions", headers=headers, json={"title": title, "settings": {}}
    )
    assert response.status_code == 201, response.text
    return response.json()
