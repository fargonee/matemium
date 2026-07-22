from __future__ import annotations

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str = Field(..., pattern="^(system|user|assistant)$")
    content: str


class ChatCompletionRequest(BaseModel):
    messages: list[ChatMessage]
    project_id: str | None = None
    conversation_id: str | None = Field(
        None,
        description="Stable UI conversation identifier used for agent persistence.",
    )
    scenes_excerpt: str | None = Field(
        None,
        description="Current scenes.py content or selection for context",
    )
    # LLM selection retained for compatibility; desktop resolves local provider keys.
    llm_provider: str | None = Field(
        "openrouter",
        description="User-owned provider to use. OpenRouter is the default.",
    )
    use_personal_llm: bool = Field(
        True,
        description="Deprecated compatibility flag. External AI runs from the user's device with local provider keys.",
    )
    model: str | None = Field(None, description="Optional model override for this call")
    use_autonomous_agent: bool = Field(
        False,
        description="Explicitly request to execute the autonomous multi-turn ReAct agent loop for this call.",
    )
    agent_runtime_version: str | None = Field(
        None,
        description="Versioned autonomous runtime selector. Omitted requests use the current compatible default.",
    )


class CodeEdit(BaseModel):
    description: str
    search: str | None = None
    replace: str | None = None
    full_file: str | None = None


class ChatCompletionResponse(BaseModel):
    id: str
    message: ChatMessage
    code_edit: CodeEdit | None = None
    model: str
    stub: bool = False
    agent_runtime_version: str | None = None
    provider: str | None = None
    billing_mode: str | None = Field(
        None,
        description="Compatibility field; current values are byo_external or local, never platform.",
    )
    request_id: str | None = None
    agent_trace: list[dict[str, object]] = Field(default_factory=list)


# ---------------- Audio / TTS ----------------

class AudioSpeechRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=4000)
    voice: str | None = "alloy"
    model: str | None = None
    speed: float | None = Field(None, ge=0.25, le=4.0)
    # Deprecated compatibility fields. Provider audio proxying is disabled server-side.
    tts_provider: str | None = None
    use_personal_llm: bool = Field(False, description="Deprecated compatibility flag.")


# Response is raw audio bytes. Route will return it with proper Content-Type (e.g. audio/mpeg).

# ---------------- Thin Publishing & Gallery (Phase 8) ----------------

class PublishRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: str | None = Field(None, max_length=2000)
    tags: list[str] = Field(default_factory=list, max_items=10)
    # Optional scene info
    scene_class: str | None = None
    duration: float | None = None

class GalleryItem(BaseModel):
    id: str
    title: str
    description: str | None = None
    tags: list[str] = []
    author_id: str | None = None
    author_name: str | None = None
    youtube_id: str | None = None
    status: str = "pending"  # pending, published, rejected
    published_at: str | None = None
    featured: bool = False
    created_at: str | None = None
    duration: float | None = None
    scene_class: str | None = None

class PublishResponse(BaseModel):
    id: str
    status: str
    message: str = "Submitted for review. Video upload to YouTube channel pending."

class GalleryListResponse(BaseModel):
    items: list[GalleryItem]
    total: int
    limit: int
    offset: int
