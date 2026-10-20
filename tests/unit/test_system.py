from __future__ import annotations

from fastapi.testclient import TestClient


def test_health_and_meta(client: TestClient) -> None:
    health = client.get("/health")
    assert health.status_code == 200
    data = health.json()
    assert data["db"] == "ok"
    assert data["milvus"] in {"ok", "unavailable"}

    meta = client.get("/api/v1/meta")
    assert meta.status_code == 200
    body = meta.json()
    assert body["llm_model"] == "deepseek-flash"
    assert body["embedding_dim"] == 1024
    assert "hybrid" in body["retrieval_modes"]
    assert "top_p" in body["top_p_note"]


def test_root(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["health"] == "/health"
