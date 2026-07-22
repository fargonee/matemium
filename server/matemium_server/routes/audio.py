from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from ..deps import AuthUser, require_user
from ..models import AudioSpeechRequest

router = APIRouter(tags=["audio"])


@router.post("/audio/speech")
async def text_to_speech(
    body: AudioSpeechRequest,
    user: Annotated[AuthUser, Depends(require_user)],
) -> None:
    """
    Deprecated compatibility endpoint. Provider keys are stored on the user's
    computer, so Matemium servers do not proxy external audio generation.
    """
    _ = (body, user)
    raise HTTPException(
        status_code=410,
        detail="Matemium no longer proxies provider audio requests. Provider keys stay on the user's computer.",
    )
