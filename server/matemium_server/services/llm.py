"""Legacy LLM helpers for server-side compatibility.

Design:
- Current desktop clients call OpenRouter directly from the user's computer.
- Matemium servers do not store provider keys or proxy external AI requests.
- This module remains for tests and old compatibility boundaries only.
"""

from __future__ import annotations

import uuid
import time
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

DEFAULT_CHAT_MODEL = "openai/gpt-4o-mini"
DEFAULT_TTS_MODEL = "tts-1"
DEFAULT_TTS_VOICE = "alloy"


@lru_cache(maxsize=1)
def scene_authoring_system_prompt() -> str:
    """System prompt prepended to every third-party LLM chat for scenes.py authoring."""
    try:
        return _SCENE_AUTHORING_PROMPT_PATH.read_text(encoding="utf-8").strip()
    except OSError:
        return (
            "You are Ferganus, a Matemium assistant. Users author animations in scenes.py "
            "using CanvasBuilder and CanvasScene — not raw Manim. Respond with concise "
            "guidance and propose concrete Python edits when asked."
        )


async def resolve_llm_for_user(
    user_id: str,
    *,
    provider: str | None = None,
    use_personal: bool = True,
    for_tts: bool = False,
) -> dict[str, Any]:
    """
    Server-side only resolution.
    - If the user has a stored key for the provider, use that BYO key.
    - OpenRouter is the default provider.
    - There is no Matemium platform-key fallback.
    Never accepts raw keys from client.
    """
    from .supabase import get_supabase_service

    supabase = get_supabase_service()

    prov = (provider or "openrouter").lower()

    personal = await supabase.get_user_personal_key(user_id, prov, for_tts=for_tts)
    if personal and personal.get("api_key"):
        resolved_provider = str(personal.get("provider") or prov).lower()
        base = PROVIDER_BASES.get(resolved_provider, settings.llm_api_base)
        return {
            "mode": "byo_external",
            "provider": personal.get("provider") or prov,
            "base_url": base,
            "api_key": personal["api_key"],
            "model": personal.get("model"),
        }

    raise RuntimeError(
        f"No user-owned API key configured for {prov}. Connect OpenRouter or add a provider key."
    )


async def complete_chat(
    request: ChatCompletionRequest,
    *,
    user_id: str | None = None,
    provider: str | None = None,
    use_personal: bool = True,
    model_override: str | None = None,
) -> ChatCompletionResponse:
    """Legacy server entry. Desktop clients call external providers directly."""
    if settings.llm_stub:
        return _stub_response(request)

    resolved = await resolve_llm_for_user(
        user_id or "unknown",
        provider=provider,
        use_personal=use_personal,
        for_tts=False,
    )

    model = model_override or resolved.get("model") or settings.llm_model or DEFAULT_CHAT_MODEL

    return await _openai_compatible_chat(
        request, resolved["base_url"], resolved["api_key"], model
    )


async def complete_structured_agent(
    request: "StructuredModelRequest",
    *,
    user_id: str,
    provider: str | None = None,
    use_personal: bool = True,
) -> "StructuredModelResponse":
    """Execute one provider-native, structured agent model call.

    This is the Phase 2 gateway entry point. It deliberately does not execute
    tools or authorize task completion; later runtime phases own those policies.
    """
    from matemium.agent.model_gateway import CallAccounting, StructuredModelGateway

    resolved = await resolve_llm_for_user(
        user_id,
        provider=provider,
        use_personal=use_personal,
        for_tts=False,
    )

    async def transport(payload: dict[str, Any]) -> dict[str, Any]:
        async with httpx.AsyncClient(base_url=resolved["base_url"], timeout=90.0) as client:
            response = await client.post(
                "/chat/completions",
                headers={"Authorization": f"Bearer {resolved['api_key']}"},
                json=payload,
            )
            response.raise_for_status()
            return response.json()

    started = time.monotonic()
    response = await StructuredModelGateway(transport).complete(request)
    latency_ms = max(0, round((time.monotonic() - started) * 1000))
    request_id = response.provider_response_id or f"agent-call-{uuid.uuid4().hex}"
    provider_name = str(resolved.get("provider") or provider or "unknown")
    response_model = response.model or request.model
    response.call_accounting = CallAccounting(
        provider=provider_name,
        model=response_model,
        request_id=request_id,
        billing_mode="byo_external",
        latency_ms=latency_ms,
        cost_usd=0.0,
        charged_credits=0,
    )
    return response


async def generate_speech(
    request: AudioSpeechRequest,
    *,
    user_id: str | None = None,
    provider: str | None = None,
    use_personal: bool = True,
) -> bytes:
    """Legacy server TTS helper. Desktop/provider-direct TTS should not use this path."""
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

def extract_code_edit(content: str) -> CodeEdit | None:
    """
    Extract a CodeEdit from the assistant's content.
    Supports:
    - Aider-style search/replace block.
    - Full-file python code block if it contains class / CanvasScene definitions.
    """
    # 1. Search for Aider Search/Replace format
    search_marker = "<<<<<<< SEARCH"
    divider_marker = "======="
    replace_marker = ">>>>>>> REPLACE"

    search_idx = content.find(search_marker)
    if search_idx >= 0:
        divider_idx = content.find(divider_marker, search_idx)
        replace_idx = content.find(replace_marker, divider_idx)
        if divider_idx > search_idx and replace_idx > divider_idx:
            search_text = content[search_idx + len(search_marker) : divider_idx]
            replace_text = content[divider_idx + len(divider_marker) : replace_idx]
            
            # Clean up leading/trailing newlines
            if search_text.startswith("\n"):
                search_text = search_text[1:]
            if search_text.endswith("\n"):
                search_text = search_text[:-1]
            if replace_text.startswith("\n"):
                replace_text = replace_text[1:]
            if replace_text.endswith("\n"):
                replace_text = replace_text[:-1]

            return CodeEdit(
                description="Apply proposed search/replace edit",
                search=search_text,
                replace=replace_text,
            )

    # 2. Look for Python Markdown code blocks that look like full scenes.py files
    import re
    code_block_re = re.compile(r"```(?:python)?\s*\n(.*?)\n\s*```", re.DOTALL)
    matches = code_block_re.findall(content)
    for match in matches:
        # Safety check: ensure it looks like a full scenes.py file (has CanvasScene / class definitions)
        if ("CanvasScene" in match or "CanvasBuilder" in match) and "class " in match:
            return CodeEdit(
                description="Apply proposed full file replacement",
                full_file=match.strip(),
            )
            
    return None


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
    code_edit = CodeEdit(description="Add intro heading and sample equation", full_file=_sample_scenes_py())
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
        if "--- REFERENCE FILE:" in request.scenes_excerpt:
            parts = request.scenes_excerpt.split("// --- workspace context below ---")
            if len(parts) == 2:
                references_part = parts[0].strip()
                scenes_part = parts[1].strip()
                messages.append(
                    {
                        "role": "system",
                        "content": f"Reference documents provided by the user:\n{references_part}",
                    }
                )
                if scenes_part:
                    messages.append(
                        {
                            "role": "system",
                            "content": f"Current scenes.py:\n```python\n{scenes_part}\n```",
                        }
                    )
            else:
                messages.append(
                    {
                        "role": "system",
                        "content": f"Workspace context and reference files:\n{request.scenes_excerpt}",
                    }
                )
        else:
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
    from matemium.agent.edit_normalization import has_edit_proposal, normalize_model_edit

    normalized = None if request.use_autonomous_agent else normalize_model_edit(
        choice["content"], request.scenes_excerpt
    )
    if normalized:
        code_edit = CodeEdit(
            description=normalized.description,
            search=normalized.search,
            replace=normalized.replace,
            full_file=normalized.full_file,
        )
        assistant_content = "Prepared a validated, bounded edit from the model proposal. Review the diff below and choose Apply to editor; no file has been changed yet."
    else:
        code_edit = None
        assistant_content = (
            "The model proposed a code change, but it was not safely applicable to the current file: its precondition was missing or ambiguous, or the change exceeded the bounded-edit policy. Nothing was changed. Ask for a smaller edit or use autonomous mode with verification."
            if has_edit_proposal(choice["content"])
            else choice["content"]
        )
    resp = ChatCompletionResponse(
        id=data.get("id", f"chatcmpl-{uuid.uuid4().hex[:12]}"),
        message=ChatMessage(role="assistant", content=assistant_content),
        code_edit=code_edit,
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
