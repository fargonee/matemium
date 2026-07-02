from __future__ import annotations

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str = Field(..., pattern="^(system|user|assistant)$")
    content: str


class ChatCompletionRequest(BaseModel):
    messages: list[ChatMessage]
    project_id: str | None = None
    scenes_excerpt: str | None = Field(
        None,
        description="Current scenes.py content or selection for context",
    )
    # LLM selection (server resolves secrets from stored user or platform config)
    llm_provider: str | None = Field(
        None,
        description="Which provider to use. If user has configured a personal key for this provider, it will be used (BYO). Otherwise platform pool.",
    )
    use_personal_llm: bool = Field(
        False,
        description="Explicitly request to use the user's stored personal LLM keys for the selected provider.",
    )
    model: str | None = Field(None, description="Optional model override for this call")


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


# ---------------- Audio / TTS ----------------

class AudioSpeechRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=4000)
    voice: str | None = "alloy"
    model: str | None = None
    speed: float | None = Field(None, ge=0.25, le=4.0)
    # Selection (server resolves from stored config)
    tts_provider: str | None = None
    use_personal_llm: bool = Field(False, description="Use user's stored TTS key for this provider if configured.")


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