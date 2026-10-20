from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from enterprise_rag.config import Settings
from enterprise_rag.infra.embedder import HashingEmbedder
from enterprise_rag.infra.llm import MockLLM
from enterprise_rag.infra.milvus import InMemoryVectorStore
from enterprise_rag.main import create_app


@pytest.fixture
def settings(tmp_path) -> Settings:
    return Settings(
        app_env="test",
        database_url="sqlite+pysqlite:///:memory:",
        auto_create_tables=True,
        jwt_secret="test-secret-key-with-at-least-32-bytes",
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
        deepseek_model="deepseek-flash",
    )


@pytest.fixture
def app(settings: Settings):
    vector_store = InMemoryVectorStore()
    app = create_app(
        settings,
        vector_store=vector_store,
        embedder=HashingEmbedder(settings.embedding_dim),
        llm=MockLLM(settings),
        start_worker=False,
    )
    return app


@pytest.fixture
def client(app) -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


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


@pytest.fixture
def admin_token(client: TestClient) -> str:
    return login(client, "admin", "admin123456")


@pytest.fixture
def user_token(client: TestClient) -> str:
    return register(client, "user_demo")


@pytest.fixture
def admin_headers(admin_token: str) -> dict[str, str]:
    return auth(admin_token)


@pytest.fixture
def user_headers(user_token: str) -> dict[str, str]:
    return auth(user_token)
