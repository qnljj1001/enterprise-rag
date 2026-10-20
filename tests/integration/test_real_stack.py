from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from enterprise_rag.config import Settings
from enterprise_rag.infra.embedder import HashingEmbedder
from enterprise_rag.infra.llm import MockLLM
from enterprise_rag.infra.milvus import MilvusVectorStore
from enterprise_rag.main import create_app
from tests.helpers import (
    create_kb,
    login,
    process_document,
    register,
    upload_md,
)

pytestmark = pytest.mark.integration


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        app_env="test",
        database_url=os.getenv(
            "TEST_DATABASE_URL",
            "mysql+pymysql://rag:rag@127.0.0.1:3306/enterprise_rag_test?charset=utf8mb4",
        ),
        auto_create_tables=True,
        jwt_secret="integration-secret-key-with-32-bytes!!",
        admin_username="admin",
        admin_password="admin123456",
        seed_admin=True,
        embedding_provider="hash",
        embedding_dim=1024,
        llm_provider="mock",
        enable_worker=False,
        embedding_preload=False,
        upload_dir=tmp_path / "uploads",
        log_dir=tmp_path / "logs",
        expose_captcha_code=True,
        milvus_collection="kb_chunks_it",
    )


def test_real_mysql_milvus_ingest_and_chat(tmp_path: Path) -> None:
    if os.getenv("RUN_INTEGRATION") != "1":
        pytest.skip("设置 RUN_INTEGRATION=1 后运行")
    settings = _settings(tmp_path)
    vector_store = MilvusVectorStore(settings)
    app = create_app(
        settings,
        vector_store=vector_store,
        embedder=HashingEmbedder(settings.embedding_dim),
        llm=MockLLM(settings),
        start_worker=False,
    )
    with TestClient(app) as client:
        admin = login(client, "admin", "admin123456")
        admin_headers = {"Authorization": f"Bearer {admin}"}
        kb = create_kb(client, admin_headers, name=f"集成测试库 {os.getpid()}")
        doc = upload_md(client, admin_headers, kb["id"]).json()
        process_document(app, doc["id"])

        detail = client.get(f"/api/v1/admin/documents/{doc['id']}", headers=admin_headers)
        assert detail.json()["status"] == "ready"
        assert detail.json()["chunk_count"] > 0

        user = register(client, f"it_user_{os.getpid()}")
        user_headers = {"Authorization": f"Bearer {user}"}
        session = client.post(
            "/api/v1/chat/sessions", headers=user_headers, json={"title": "集成会话"}
        ).json()
        with client.stream(
            "POST",
            f"/api/v1/chat/sessions/{session['id']}/messages/stream",
            headers=user_headers,
            json={
                "content": "西部计划服务期是几年？",
                "kb_ids": [kb["id"]],
                "temperature": 0.5,
                "top_p": 0.9,
                "max_tokens": 256,
                "history_rounds": 5,
            },
        ) as response:
            body = "".join(response.iter_text())
        assert "event: citations" in body
        assert "event: done" in body
        assert "chunk_id" in body

        client.delete(f"/api/v1/admin/knowledge-bases/{kb['id']}", headers=admin_headers)
    app.state.db.drop_all()
