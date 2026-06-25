"""Reusable animation primitives for the canvas."""

from __future__ import annotations

from manim import Animation, AnimationGroup, Create, FadeIn, Flash, GrowFromCenter, Write
from manim import Mobject


def get_entry_animation(
    mob: Mobject,
    anim_spec: "EntryAnimation",  # forward ref ok because we import inside
    default: str = "Write",
) -> Animation:
    """Factory that turns an EntryAnimation spec into a real Manim Animation."""
    atype = (anim_spec.type or default).lower()
    rt = anim_spec.run_time
    kw = anim_spec.kwargs or {}

    if atype in ("write", "writetex"):
        return Write(mob, run_time=rt, **kw)
    elif atype in ("fadein", "fade"):
        return FadeIn(mob, run_time=rt, **kw)
    elif atype in ("grow", "growfromcenter"):
        return GrowFromCenter(mob, run_time=rt, **kw)
    elif atype in ("create", "draw"):
        return Create(mob, run_time=rt, **kw)
    else:
        # sensible default
        return FadeIn(mob, run_time=rt, **kw)


def FLASH_AND_SCALE(
    mob: Mobject,
    scale_factor: float = 1.25,
    run_time: float = 1.0,
    flash_radius: float | None = None,
) -> Animation:
    """Signature 're-emphasis' animation used for callbacks / transforms."""
    if flash_radius is None:
        flash_radius = mob.get_width() / 2 + 0.2

    flash = Flash(
        mob,
        line_length=0.35,
        flash_radius=flash_radius,
        run_time=run_time * 0.35,
    )
    scale_up = mob.animate.scale(scale_factor).set_run_time(run_time * 0.4)
    scale_down = mob.animate.scale(1.0 / scale_factor).set_run_time(run_time * 0.4)

    return AnimationGroup(
        flash,
        scale_up,
        scale_down,
        lag_ratio=0.35,
        run_time=run_time,
    )
