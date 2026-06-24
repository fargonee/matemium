"""Commercial gatekeeping — tier evaluation and watermark injection before render."""

from __future__ import annotations

import re
from pathlib import Path

from canvas.dsl import CanvasElement, SheetDSL

from .models import AccountTier, ProjectSession

WATERMARK_TEXT = "matemium"
WATERMARK_MARKER = "# <<<Matemium:COMMERCIAL_WATERMARK>>>"
WATERMARK_BUILDER_LINE = f'        builder.add_text("{WATERMARK_TEXT}")'
SUPER_INIT_ANCHOR = "        super().__init__(dsl=builder.build(), **kwargs)"

_WATERMARK_BLOCK = f"        {WATERMARK_MARKER}\n{WATERMARK_BUILDER_LINE}\n"
_WATERMARK_BLOCK_RE = re.compile(
    rf"^[ \t]*{re.escape(WATERMARK_MARKER)}\n{re.escape(WATERMARK_BUILDER_LINE)}\n",
    re.MULTILINE,
)


def should_apply_watermark(
    account_tier: AccountTier,
    *,
    watermark_removal_paid: bool = False,
    extra_project_tokens_spent: bool = False,
) -> bool:
    """Return True when a commercial watermark must be injected before compile."""
    if account_tier is AccountTier.PREMIUM:
        return False
    if watermark_removal_paid or extra_project_tokens_spent:
        return False
    return True


def should_apply_watermark_for_session(session: ProjectSession) -> bool:
    """Evaluate guard decision from live ProjectSession commercial state."""
    return should_apply_watermark(
        session.account_tier,
        watermark_removal_paid=session.watermark_removal_paid,
        extra_project_tokens_spent=session.extra_project_tokens_spent,
    )


def scenes_source_has_watermark(source: str) -> bool:
    """Detect whether scenes.py already contains the commercial watermark block."""
    return WATERMARK_MARKER in source or WATERMARK_BUILDER_LINE in source


def inject_watermark_to_scenes_source(source: str) -> str:
    """Insert the matemium overlay into the CanvasBuilder main-scene configuration."""
    if scenes_source_has_watermark(source):
        return source
    if SUPER_INIT_ANCHOR not in source:
        return source
    return source.replace(
        SUPER_INIT_ANCHOR,
        f"{_WATERMARK_BLOCK}{SUPER_INIT_ANCHOR}",
        1,
    )


def strip_watermark_from_scenes_source(source: str) -> str:
    """Remove a previously injected commercial watermark block."""
    return _WATERMARK_BLOCK_RE.sub("", source)


def inject_watermark_if_needed(source: str, *, apply_watermark: bool) -> str:
    """Apply or remove watermark injection according to the guard decision."""
    if apply_watermark:
        return inject_watermark_to_scenes_source(source)
    return strip_watermark_from_scenes_source(source)


def apply_guard_to_scenes_file(scenes_path: Path, session: ProjectSession) -> bool:
    """Rewrite on-disk scenes.py so compile reflects the current commercial entitlement."""
    if not scenes_path.is_file():
        return False
    source = scenes_path.read_text(encoding="utf-8")
    updated = inject_watermark_if_needed(
        source,
        apply_watermark=should_apply_watermark_for_session(session),
    )
    if updated != source:
        scenes_path.write_text(updated, encoding="utf-8")
    return should_apply_watermark_for_session(session)


def apply_guard_to_project(session: ProjectSession) -> bool:
    """Enforce guard on the session workspace scenes.py prior to sidecar compile."""
    return apply_guard_to_scenes_file(session.project_dir / "scenes.py", session)


def dsl_has_watermark(dsl: SheetDSL) -> bool:
    """Return True when compiled DSL timeline contains the matemium overlay text."""
    for item in dsl.timeline:
        if not isinstance(item, CanvasElement):
            continue
        if item.type != "Text":
            continue
        content = item.content
        if content == WATERMARK_TEXT:
            return True
        if isinstance(content, str) and WATERMARK_TEXT in content:
            return True
    return False