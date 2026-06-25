from fastapi.testclient import TestClient

from matemium_server.app import app

client = TestClient(app)


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["service"] == "matemium-server"


def test_auth_token_stub():
    resp = client.post(
        "/v1/auth/token",
        json={"email": "dev@matemium.app", "password": "test"},
    )
    assert resp.status_code == 200
    assert resp.json()["access_token"].startswith("dev.")


def test_chat_completions_stub():
    token_resp = client.post(
        "/v1/auth/token",
        json={"email": "dev@matemium.app", "password": "test"},
    )
    token = token_resp.json()["access_token"]

    resp = client.post(
        "/v1/chat/completions",
        json={"messages": [{"role": "user", "content": "Add a quadratic formula"}]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["message"]["role"] == "assistant"
    assert data["stub"] is True
    assert data.get("code_edit") is not None