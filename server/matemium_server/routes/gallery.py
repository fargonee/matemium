"""Thin publishing and public gallery endpoints (Phase 8).

No video storage. Only metadata + YouTube IDs. Gallery works pre-ready.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from ..deps import AuthUser, require_user, get_supabase_service
from ..models import (
    GalleryItem,
    GalleryListResponse,
    PublishRequest,
    PublishResponse,
)
from ..services.supabase import SupabaseService

router = APIRouter(tags=["gallery"])


@router.post("/v1/publish", response_model=PublishResponse)
async def publish_animation(
    payload: PublishRequest,
    user: AuthUser = Depends(require_user),
    supabase: SupabaseService = Depends(get_supabase_service),
) -> PublishResponse:
    """Submit a rendered animation for the community gallery (thin metadata only).

    The actual video should be uploaded to the official Matemium YouTube channel
    (manual or automated). Once youtube_id is set, it appears in gallery.
    """
    if not supabase._db_configured():  # type: ignore[attr-defined]
        # Fallback for dev without DB
        return PublishResponse(id="dev-" + str(int(datetime.now().timestamp())), status="pending")

    now = datetime.utcnow().isoformat()
    data = {
        "title": payload.title,
        "description": payload.description,
        "tags": payload.tags,
        "author_id": user.id,
        "author_name": user.email or "anonymous",  # or fetch profile
        "status": "pending",
        "created_at": now,
        "duration": payload.duration,
        "scene_class": payload.scene_class,
        "featured": False,
    }

    try:
        created = await supabase.create_animation(data)
        anim_id = created.get("id") or "unknown"
        return PublishResponse(id=str(anim_id), status="pending")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to publish: {e}")


@router.get("/v1/gallery", response_model=GalleryListResponse)
async def list_gallery(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status: str | None = Query("published"),
    featured: bool | None = Query(None),
    search: str | None = Query(None),
    supabase: SupabaseService = Depends(get_supabase_service),
) -> GalleryListResponse:
    """Public gallery listing. Works completely before any local heavy assets are ready.

    Powered by metadata + YouTube embeds. No videos stored on Matemium servers.
    """
    if not supabase._db_configured():  # type: ignore[attr-defined]
        # Dev fallback with mocks (from Phase 5)
        mock_items = [
            GalleryItem(
                id="demo-quadratic",
                title="Quadratic Factoring",
                description="Visual proof of factoring x² + bx + c with completing the square animation.",
                tags=["algebra", "factoring"],
                author_name="Matemium Demo",
                youtube_id="M7lc1UVf-VE",
                status="published",
            ),
            GalleryItem(
                id="demo-waves",
                title="Electromagnetic Waves",
                description="Interactive 3D visualization of EM wave propagation and polarization.",
                tags=["physics", "3d"],
                author_name="Community",
                youtube_id="jNQXAC9IVRw",
                status="published",
            ),
        ]
        return GalleryListResponse(items=mock_items, total=len(mock_items), limit=limit, offset=offset)

    rows = await supabase.list_animations(
        limit=limit, offset=offset, status=status, featured=featured, search=search
    )
    items = [GalleryItem(**r) for r in rows]
    total = len(items)  # For simplicity; real impl would count separately
    return GalleryListResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/v1/gallery/{item_id}", response_model=GalleryItem)
async def get_gallery_item(
    item_id: str,
    supabase: SupabaseService = Depends(get_supabase_service),
) -> GalleryItem:
    if not supabase._db_configured():  # type: ignore[attr-defined]
        # Fallback
        for item in [
            GalleryItem(id="demo-quadratic", title="Quadratic Factoring", youtube_id="M7lc1UVf-VE", status="published"),
        ]:
            if item.id == item_id:
                return item
        raise HTTPException(404, "Not found")

    row = await supabase.get_animation(item_id)
    if not row:
        raise HTTPException(status_code=404, detail="Animation not found")
    return GalleryItem(**row)


# Optional: admin or webhook to set youtube_id
@router.patch("/v1/gallery/{item_id}")
async def update_gallery_item(
    item_id: str,
    data: dict[str, Any],
    user: AuthUser = Depends(require_user),
    supabase: SupabaseService = Depends(get_supabase_service),
) -> dict[str, str]:
    # TODO: check admin role
    allowed = {"youtube_id": str, "status": str, "featured": bool}
    patch: dict[str, Any] = {}
    for k, v in data.items():
        if k in allowed:
            patch[k] = v
    if not patch:
        raise HTTPException(400, "No valid fields to update")
    await supabase.update_animation(item_id, patch)
    return {"status": "updated", "id": item_id}