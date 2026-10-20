"""端到端冒烟：登录、建库、上传、解析、注册、流式问答。

用法：uv run python scripts/smoke_test.py [--base http://127.0.0.1:8001]
需要后端以 EXPOSE_CAPTCHA_CODE=true 启动（仅开发/测试环境）。
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "data" / "samples" / "policy_faq.md"


def captcha(client: httpx.Client, base: str) -> dict:
    response = client.get(f"{base}/api/v1/auth/captcha")
    response.raise_for_status()
    data = response.json()
    if not data.get("debug_code"):
        raise RuntimeError("后端未返回 debug_code，请用 EXPOSE_CAPTCHA_CODE=true 启动")
    return data


def login(client: httpx.Client, base: str, username: str, password: str) -> str:
    code = captcha(client, base)
    response = client.post(
        f"{base}/api/v1/auth/login",
        json={
            "username": username,
            "password": password,
            "captcha_id": code["captcha_id"],
            "captcha_code": code["debug_code"],
        },
    )
    response.raise_for_status()
    return response.json()["access_token"]


def register(client: httpx.Client, base: str, username: str, password: str) -> str:
    code = captcha(client, base)
    response = client.post(
        f"{base}/api/v1/auth/register",
        json={
            "username": username,
            "password": password,
            "confirm_password": password,
            "captcha_id": code["captcha_id"],
            "captcha_code": code["debug_code"],
        },
    )
    response.raise_for_status()
    return response.json()["access_token"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:8001")
    parser.add_argument("--file", default=str(SAMPLE))
    args = parser.parse_args()
    base = args.base.rstrip("/")
    sample = Path(args.file).resolve()
    content_type = mimetypes.guess_type(sample.name)[0] or "application/octet-stream"
    suffix = str(int(time.time()))
    with httpx.Client(timeout=120) as client:
        admin = login(client, base, "admin", "admin123456")
        admin_headers = {"Authorization": f"Bearer {admin}"}
        kb_resp = client.post(
            f"{base}/api/v1/admin/knowledge-bases",
            headers=admin_headers,
            json={
                "name": f"冒烟政策库 {suffix}",
                "description": "smoke test",
                "default_chunk_size": 300,
                "default_chunk_overlap": 30,
                "retrieval_mode": "hybrid",
            },
        )
        kb_resp.raise_for_status()
        kb = kb_resp.json()
        print("kb:", kb["id"])

        with sample.open("rb") as handle:
            upload = client.post(
                f"{base}/api/v1/admin/knowledge-bases/{kb['id']}/documents",
                headers=admin_headers,
                files={"file": (sample.name, handle, content_type)},
                data={"chunk_size": "300", "chunk_overlap": "30"},
            )
        upload.raise_for_status()
        document = upload.json()
        print("doc:", document["id"], document["status"])

        for _ in range(180):
            detail = client.get(
                f"{base}/api/v1/admin/documents/{document['id']}", headers=admin_headers
            )
            detail.raise_for_status()
            document = detail.json()
            print("status:", document["status"], document["progress"])
            if document["status"] in {"ready", "failed"}:
                break
            time.sleep(1)
        if document["status"] != "ready":
            raise RuntimeError(f"解析失败：{document.get('error_message')}")

        chunks = client.get(
            f"{base}/api/v1/admin/documents/{document['id']}/chunks", headers=admin_headers
        )
        chunks.raise_for_status()
        print("chunks:", chunks.json()["total"])

        user = register(client, base, f"smoke_user_{suffix}", "user123456")
        user_headers = {"Authorization": f"Bearer {user}"}
        session_resp = client.post(
            f"{base}/api/v1/chat/sessions",
            headers=user_headers,
            json={"title": "冒烟会话", "settings": {}},
        )
        session_resp.raise_for_status()
        session = session_resp.json()
        print("session:", session["id"])

        events: dict[str, int] = {}
        answer = ""
        citations = 0
        with client.stream(
            "POST",
            f"{base}/api/v1/chat/sessions/{session['id']}/messages/stream",
            headers=user_headers,
            json={
                "content": "西部计划服务期一般是几年？",
                "kb_ids": [kb["id"]],
                "temperature": 0.5,
                "top_p": 0.9,
                "max_tokens": 512,
                "history_rounds": 5,
            },
        ) as response:
            response.raise_for_status()
            current = ""
            for line in response.iter_lines():
                if line.startswith("event:"):
                    current = line.split(":", 1)[1].strip()
                    events[current] = events.get(current, 0) + 1
                elif line.startswith("data:"):
                    payload = json.loads(line.split(":", 1)[1].strip())
                    if current == "citations":
                        citations = len(payload.get("items", []))
                    elif current == "delta":
                        answer += payload.get("text", "")
        print("events:", events)
        print("citations:", citations)
        print("answer:", answer[:200])
        if "done" not in events or "delta" not in events:
            raise RuntimeError("SSE 事件不完整")
        if citations == 0:
            raise RuntimeError("没有检索到引用")
        if not answer:
            raise RuntimeError("回答为空")
        print("SMOKE OK")


if __name__ == "__main__":
    main()
