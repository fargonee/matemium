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