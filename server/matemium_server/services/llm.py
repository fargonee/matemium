"""LLM-agnostic proxy for code generation (chat) and audio (TTS).

Design:
- LLM agnostic: works with any OpenAI-compatible provider (OpenAI, Groq, xAI, OpenRouter, Together, Fireworks, local vLLM, etc.).
- BYO support: if user_api_key (and optional provider/base) is supplied, use the *user's* key (no platform credit consumption).
- Platform mode: use server keys + deduct from user's llm_credits.
- Audio creations: separate text-to-speech path (also supports BYO or platform).
"""

from __future__ import annotations

import uuid
from functools import lru_cache
from pathlib import Path
from typing import Any

import httpx

from ..config import settings
from ..models import (
    AudioSpeechRequest,
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatMessage,
    CodeEdit,
)

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SCENE_AUTHORING_PROMPT_PATH = _REPO_ROOT / "shared" / "prompts" / "scene-authoring-system.txt"

# Default bases for common providers (extend as needed)
PROVIDER_BASES: dict[str, str] = {
    "openai": "https://api.openai.com/v1",
    "groq": "https://api.groq.com/openai/v1",
    "xai": "https://api.x.ai/v1",
    "openrouter": "https://openrouter.ai/api/v1",
    "together": "https://api.together.xyz/v1",
    "fireworks": "https://api.fireworks.ai/inference/v1",
}

DEFAULT_CHAT_MODEL = "gpt-4o-mini"
DEFAULT_TTS_MODEL = "tts-1"
DEFAULT_TTS_VOICE = "alloy"


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


async def resolve_llm_for_user(
    user_id: str,
    *,
    provider: str | None = None,
    use_personal: bool = False,
    for_tts: bool = False,
) -> dict[str, Any]:
    """
    Server-side only resolution.
    - If use_personal and user has a stored key for the provider → use BYO (no cost to us).
    - Else → pick one of our platform llm_providers.
    Never accepts raw keys from client.
    """
    from .supabase import get_supabase_service

    supabase = get_supabase_service()

    prov = (provider or "openai").lower()

    if use_personal:
        personal = await supabase.get_user_personal_key(user_id, prov, for_tts=for_tts)
        if personal and personal.get("api_key"):
            base = PROVIDER_BASES.get(personal["provider"].lower(), settings.llm_api_base)
            return {
                "mode": "personal",
                "provider": personal["provider"],
                "base_url": base,
                "api_key": personal["api_key"],
                "model": personal.get("model"),
            }

    # Platform mode - use our managed keys
    platform = await supabase.pick_best_platform_provider(prov)
    if platform and platform.get("api_key"):
        base = platform.get("api_base") or PROVIDER_BASES.get(platform["name"].lower(), settings.llm_api_base)
        return {
            "mode": "platform",
            "provider": platform["name"],
            "base_url": base,
            "api_key": platform["api_key"],
            "model": None,
        }

    # Fallback to legacy global settings
    if settings.llm_api_key:
        return {
            "mode": "platform",
            "provider": "openai",
            "base_url": settings.llm_api_base,
            "api_key": settings.llm_api_key,
            "model": settings.llm_model,
        }

    raise RuntimeError("No LLM configuration available (neither personal nor platform)")


async def complete_chat(
    request: ChatCompletionRequest,
    *,
    user_id: str | None = None,
    provider: str | None = None,
    use_personal: bool = False,
    model_override: str | None = None,
) -> ChatCompletionResponse:
    """Main entry. Resolution of secrets always happens server-side via user_id + config."""
    if settings.llm_stub:
        return _stub_response(request)

    resolved = await resolve_llm_for_user(
        user_id or "unknown",
        provider=provider,
        use_personal=use_personal,
        for_tts=False,
    )

    model = model_override or resolved.get("model") or settings.llm_model or DEFAULT_CHAT_MODEL

    if resolved["mode"] == "personal":
        # BYO - no cost logging/deduction here (done at higher level if wanted)
        return await _openai_compatible_chat(
            request, resolved["base_url"], resolved["api_key"], model
        )

    # Platform - we will log cost after the call (see route)
    return await _openai_compatible_chat(
        request, resolved["base_url"], resolved["api_key"], model
    )


async def generate_speech(
    request: AudioSpeechRequest,
    *,
    user_id: str | None = None,
    provider: str | None = None,
    use_personal: bool = False,
) -> bytes:
    """Text-to-speech. Secrets resolved server-side."""
    if settings.llm_stub:
        # Return tiny fake audio for tests
        return b"FAKE_AUDIO_MP3_STUB"

    resolved = await resolve_llm_for_user(
        user_id or "unknown",
        provider=provider,
        use_personal=use_personal,
        for_tts=True,
    )

    base_url = resolved["base_url"]
    api_key = resolved["api_key"]

    url = f"{base_url.rstrip('/')}/audio/speech"

    payload: dict[str, Any] = {
        "model": request.model or DEFAULT_TTS_MODEL,
        "input": request.text,
        "voice": request.voice or DEFAULT_TTS_VOICE,
    }
    if request.speed:
        payload["speed"] = request.speed

    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(
            url,
            headers={"Authorization": f"Bearer {api_key}"},
            json=payload,
        )
        resp.raise_for_status()
        return resp.content


# ---------------- internal helpers ----------------

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


async def _openai_compatible_chat(
    request: ChatCompletionRequest,
    base_url: str,
    api_key: str,
    model: str,
) -> ChatCompletionResponse:
    messages = [{"role": "system", "content": scene_authoring_system_prompt()}]
    if request.scenes_excerpt:
        messages.append(
            {
                "role": "system",
                "content": f"Current scenes.py:\n```python\n{request.scenes_excerpt}\n```",
            }
        )
    messages.extend({"role": m.role, "content": m.content} for m in request.messages)

    async with httpx.AsyncClient(base_url=base_url, timeout=90.0) as client:
        resp = await client.post(
            "/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": model,
                "messages": messages,
                # You can add temperature, max_tokens etc. if needed
            },
        )
        resp.raise_for_status()
        data = resp.json()

    choice = data["choices"][0]["message"]
    usage = data.get("usage", {})
    resp = ChatCompletionResponse(
        id=data.get("id", f"chatcmpl-{uuid.uuid4().hex[:12]}"),
        message=ChatMessage(role="assistant", content=choice["content"]),
        code_edit=None,
        model=data.get("model", model),
        stub=False,
    )
    # Attach for downstream cost logging (not part of public schema)
    setattr(resp, "usage", usage)
    return resp


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