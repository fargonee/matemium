from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response

from ..config import settings
from ..deps import AuthUser, require_user
from ..models import AudioSpeechRequest
from ..services.llm import generate_speech
from ..services.supabase import SupabaseService, get_supabase_service

router = APIRouter(tags=["audio"])


@router.post("/audio/speech")
async def text_to_speech(
    body: AudioSpeechRequest,
    user: Annotated[AuthUser, Depends(require_user)],
) -> Response:
    """
    Secure TTS.

    use_personal_llm + provider → use user's stored key.
    Otherwise use our platform pool + cost tracking.
    """
    use_personal = bool(body.use_personal_llm)
    provider = body.tts_provider

    supabase: SupabaseService = get_supabase_service()
    personal = await supabase.get_user_personal_key(user.id, provider, for_tts=True) if use_personal else None
    using_platform = not personal

    if using_platform and not settings.llm_stub:
        if not await supabase.has_sufficient_credits(user.id, 1):
            raise HTTPException(
                status_code=402,
                detail="Insufficient platform credits for audio. Configure personal TTS key or buy tokens.",
            )

    audio_bytes = await generate_speech(
        body,
        user_id=user.id,
        provider=provider,
        use_personal=use_personal,
    )

    if using_platform and not settings.llm_stub:
        try:
            await record_platform_usage(
                user_id=user.id,
                provider_name=provider or "openai",
                model=body.model or "tts-1",
                call_type="audio",
                prompt_tokens=len(body.text or ""),  # chars as rough proxy
                completion_tokens=0,
                request_id=getattr(request.state, "request_id", None),
                extra={"voice": body.voice},
            )
        except Exception:
            pass

    return Response(
        content=audio_bytes,
        media_type="audio/mpeg",
        headers={"Content-Disposition": 'inline; filename="speech.mp3"'},
    )
