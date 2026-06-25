"""LLM chat proxy — stub for offline dev, OpenAI-compatible for production."""

from __future__ import annotations

import uuid
from functools import lru_cache
from pathlib import Path

import httpx

from ..config import settings
from ..models import ChatCompletionRequest, ChatCompletionResponse, ChatMessage, CodeEdit

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SCENE_AUTHORING_PROMPT_PATH = _REPO_ROOT / "shared" / "prompts" / "scene-authoring-system.txt"


@lru_cache(maxsize=1)
def scene_authoring_system_prompt() -> str:
    """System prompt prepended to every third-party LLM chat for scenes.py authoring."""
    try:
        return _SCENE_AUTHORING_PROMPT_PATH.read_text(encoding="utf-8").strip()
    except OSError:
        return (
            "You are a Matemium Canvas assistant. Users author animations in scenes.py "
            "using CanvasBuilder and CanvasScene — not raw Manim. Respond with concise "
            "guidance and propose concrete Python edits when asked."
        )


async def complete_chat(request: ChatCompletionRequest) -> ChatCompletionResponse:
    if settings.llm_stub or not settings.llm_api_key:
        return _stub_response(request)

    return await _openai_compatible(request)


def _stub_response(request: ChatCompletionRequest) -> ChatCompletionResponse:
    last_user = next(
        (m.content for m in reversed(request.messages) if m.role == "user"),
        "your scene",
    )
    assistant_text = (
        f"I can help refine your Matemium scene. Based on your request about "
        f"\"{last_user[:80]}{'...' if len(last_user) > 80 else ''}\", "
        f"try adding a heading and a math line with CanvasBuilder."
    )
    code_edit = CodeEdit(
        description="Add intro heading and sample equation",
        full_file=_sample_scenes_py(),
    )
    return ChatCompletionResponse(
        id=f"chatcmpl-stub-{uuid.uuid4().hex[:12]}",
        message=ChatMessage(role="assistant", content=assistant_text),
        code_edit=code_edit,
        model="stub",
        stub=True,
    )


async def _openai_compatible(request: ChatCompletionRequest) -> ChatCompletionResponse:
    messages = [{"role": "system", "content": scene_authoring_system_prompt()}]
    if request.scenes_excerpt:
        messages.append(
            {
                "role": "system",
                "content": f"Current scenes.py:\n```python\n{request.scenes_excerpt}\n```",
            }
        )
    messages.extend({"role": m.role, "content": m.content} for m in request.messages)

    async with httpx.AsyncClient(base_url=settings.llm_api_base, timeout=60.0) as client:
        resp = await client.post(
            "/chat/completions",
            headers={"Authorization": f"Bearer {settings.llm_api_key}"},
            json={"model": settings.llm_model, "messages": messages},
        )
        resp.raise_for_status()
        data = resp.json()

    choice = data["choices"][0]["message"]
    return ChatCompletionResponse(
        id=data.get("id", f"chatcmpl-{uuid.uuid4().hex[:12]}"),
        message=ChatMessage(role="assistant", content=choice["content"]),
        code_edit=None,
        model=data.get("model", settings.llm_model),
        stub=False,
    )


def _sample_scenes_py() -> str:
    return '''from canvas import CanvasScene
from canvas.builder import CanvasBuilder


class MyScene(CanvasScene):
    def __init__(self, **kwargs):
        builder = CanvasBuilder(title="My Scene")
        builder.add_heading("Introduction")
        builder.add_math(r"x^2 - 5x + 6 = 0")
        super().__init__(dsl=builder.build(), **kwargs)
'''