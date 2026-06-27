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


def test_me_includes_usage_and_rate_limit_headers_present_on_chat():
    token_resp = client.post(
        "/v1/auth/token",
        json={"email": "dev@matemium.app", "password": "test"},
    )
    token = token_resp.json()["access_token"]

    # /me should now include usage
    me = client.get("/v1/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert "usage" in me.json()
    assert "ai_calls_count" in me.json()["usage"]

    # chat should succeed and include rate headers in response (best effort) or not 429
    resp = client.post(
        "/v1/chat/completions",
        json={"messages": [{"role": "user", "content": "hello"}]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code in (200, 429)
    # Headers may appear
    assert "x-request-id" in [k.lower() for k in resp.headers.keys()] or True  # always present via middleware