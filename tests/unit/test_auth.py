from __future__ import annotations

from fastapi.testclient import TestClient

from tests.helpers import auth, get_captcha, login, register


def test_captcha_register_login_and_me(client: TestClient) -> None:
    captcha = get_captcha(client)
    assert captcha["image_base64"]
    assert captcha["debug_code"]

    response = client.post(
        "/api/v1/auth/register",
        json={
            "username": "政策用户",
            "password": "user123456",
            "confirm_password": "user123456",
            "captcha_id": captcha["captcha_id"],
            "captcha_code": captcha["debug_code"],
        },
    )
    assert response.status_code == 201, response.text
    token = response.json()["access_token"]
    assert response.json()["user"]["role"] == "user"

    me = client.get("/api/v1/auth/me", headers=auth(token))
    assert me.status_code == 200
    assert me.json()["username"] == "政策用户"

    login_token = login(client, "政策用户", "user123456")
    assert login_token


def test_register_password_mismatch(client: TestClient) -> None:
    captcha = get_captcha(client)
    response = client.post(
        "/api/v1/auth/register",
        json={
            "username": "mismatch",
            "password": "user123456",
            "confirm_password": "user123457",
            "captcha_id": captcha["captcha_id"],
            "captcha_code": captcha["debug_code"],
        },
    )
    assert response.status_code == 422


def test_wrong_captcha(client: TestClient) -> None:
    captcha = get_captcha(client)
    response = client.post(
        "/api/v1/auth/register",
        json={
            "username": "wrongcap",
            "password": "user123456",
            "confirm_password": "user123456",
            "captcha_id": captcha["captcha_id"],
            "captcha_code": "ZZZZ",
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "CAPTCHA_INVALID"


def test_duplicate_username(client: TestClient) -> None:
    register(client, "duplicated")
    captcha = get_captcha(client)
    response = client.post(
        "/api/v1/auth/register",
        json={
            "username": "duplicated",
            "password": "user123456",
            "confirm_password": "user123456",
            "captcha_id": captcha["captcha_id"],
            "captcha_code": captcha["debug_code"],
        },
    )
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "USERNAME_TAKEN"


def test_user_cannot_access_admin(client: TestClient) -> None:
    token = register(client, "normal_user")
    response = client.get("/api/v1/admin/knowledge-bases", headers=auth(token))
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "FORBIDDEN"


def test_login_wrong_password(client: TestClient) -> None:
    register(client, "wrongpass")
    captcha = get_captcha(client)
    response = client.post(
        "/api/v1/auth/login",
        json={
            "username": "wrongpass",
            "password": "bad-password",
            "captcha_id": captcha["captcha_id"],
            "captcha_code": captcha["debug_code"],
        },
    )
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "INVALID_CREDENTIALS"
