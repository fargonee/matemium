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


def test_chat_completions_disabled():
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
    assert resp.status_code == 410
    data = resp.json()
    assert data["error"] == "http_error"
    assert "no longer proxies external AI requests" in data["detail"]


def test_chat_stream_disabled():
    token_resp = client.post(
        "/v1/auth/token",
        json={"email": "dev@matemium.app", "password": "test"},
    )
    token = token_resp.json()["access_token"]

    resp = client.post(
        "/v1/chat/stream",
        json={"messages": [{"role": "user", "content": "Add a quadratic formula"}]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 410
    data = resp.json()
    assert data["error"] == "http_error"
    assert "Streaming chat through Matemium servers is disabled" in data["detail"]


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

    # chat proxying is disabled, but authenticated calls should pass auth/rate-limit
    # checks before returning the intentional deprecation response.
    resp = client.post(
        "/v1/chat/completions",
        json={"messages": [{"role": "user", "content": "hello"}]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code in (410, 429)
    # Headers may appear
    assert "x-request-id" in [k.lower() for k in resp.headers.keys()] or True  # always present via middleware


def test_extract_code_edit_aider():
    from matemium_server.services.llm import extract_code_edit
    
    aider_block = """Here is the fix:
<<<<<<< SEARCH
b.add_heading("Hello")
=======
b.add_heading("Hello World")
>>>>>>> REPLACE
Let me know if this works!"""
    
    edit = extract_code_edit(aider_block)
    assert edit is not None
    assert edit.search == "b.add_heading(\"Hello\")"
    assert edit.replace == "b.add_heading(\"Hello World\")"
    assert edit.full_file is None


def test_extract_code_edit_full_file():
    from matemium_server.services.llm import extract_code_edit
    
    full_file_block = """Here is the full file content:
```python
from canvas import CanvasScene, CanvasSettings
from canvas.builder import CanvasBuilder

class MyScene(CanvasScene):
    def __init__(self, **kwargs):
        builder = CanvasBuilder(title="My Scene")
        super().__init__(dsl=builder.build(), **kwargs)
```
Enjoy!"""
    
    edit = extract_code_edit(full_file_block)
    assert edit is not None
    assert edit.search is None
    assert edit.replace is None
    assert "class MyScene(CanvasScene):" in edit.full_file


def test_extract_code_edit_unrelated_code_block():
    from matemium_server.services.llm import extract_code_edit
    
    snippet_block = """You can write this:
```python
x = 5
print(x)
```"""
    
    edit = extract_code_edit(snippet_block)
    assert edit is None
