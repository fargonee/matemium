"""Persistent Mobject Registry for the infinite canvas.

Elements are registered once with their canonical canvas (x,y,z) coordinate.
The registry survives camera panning and enables:
- Re-animating elements that have scrolled out of view
- Pausing expensive idle updaters when far away
- Spatial queries
"""

from __future__ import annotations

import logging
from typing import Callable, Dict, List, Optional, Tuple

from manim import Mobject

logger = logging.getLogger("matemium.canvas.registry")


class RegistryEntry:
    """Light slotted container (no dataclass to avoid __slots__ + default conflicts)."""
    __slots__ = ("mobject", "canvas_y", "original_position", "active_updaters")

    def __init__(
        self,
        mobject: Mobject,
        canvas_y: float,
        original_position: Tuple[float, float, float],
    ):
        self.mobject = mobject
        self.canvas_y = canvas_y
        self.original_position = original_position
        self.active_updaters: List[Callable] = []


class MobjectRegistry:
    """Holds references to every element ever placed on the canvas.

    This is the key to "persistent state" and re-animation without
    re-creating Mobjects from scratch.
    """

    def __init__(self, viewport_margin: float = 2.0):
        self._store: Dict[str, RegistryEntry] = {}
        self.viewport_margin = viewport_margin

    def register(
        self,
        uid: str,
        mobject: Mobject,
        y: float,
        pos: Tuple[float, float, float],
    ) -> None:
        """Register a newly created mobject at its canonical canvas location."""
        entry = RegistryEntry(
            mobject=mobject,
            canvas_y=y,
            original_position=pos,
        )
        self._store[uid] = entry
        logger.debug("Registered %s at canvas_y=%.2f", uid, y)

    def get(self, uid: str) -> Optional[Mobject]:
        entry = self._store.get(uid)
        return entry.mobject if entry else None

    def get_entry(self, uid: str) -> Optional[RegistryEntry]:
        return self._store.get(uid)

    def move_to_canvas(
        self, uid: str, new_y: float, new_pos: Tuple[float, float, float]
    ) -> None:
        """Permanently re-anchor an element (used by TransformElement)."""
        entry = self._store.get(uid)
        if entry:
            entry.canvas_y = new_y
            entry.original_position = new_pos
            logger.debug("Re-anchored %s -> y=%.2f", uid, new_y)

    def get_visible(
        self, camera_center_y: float, camera_height: float
    ) -> List[Mobject]:
        """Return mobjects whose canvas_y is inside the current viewport ± margin."""
        half = camera_height / 2
        low = camera_center_y - half - self.viewport_margin
        high = camera_center_y + half + self.viewport_margin
        return [
            e.mobject
            for e in self._store.values()
            if low <= e.canvas_y <= high
        ]

    def pause_far_updaters(self, camera_center_y: float, buffer: float = 4.0) -> None:
        """Disable updaters on elements that are far from the viewport (CPU saving)."""
        for entry in self._store.values():
            if abs(entry.canvas_y - camera_center_y) > buffer:
                for upd in entry.active_updaters[:]:
                    try:
                        entry.mobject.remove_updater(upd)
                    except Exception:
                        pass
                entry.active_updaters.clear()
            # Near elements keep (or will have) their updaters

    def add_updater(self, uid: str, updater: Callable, active: bool = True) -> None:
        """Attach and track an updater for later management."""
        entry = self._store.get(uid)
        if entry:
            entry.mobject.add_updater(updater)
            if active:
                entry.active_updaters.append(updater)

    def clear_updaters(self, uid: str) -> None:
        entry = self._store.get(uid)
        if entry:
            for upd in entry.active_updaters[:]:
                try:
                    entry.mobject.remove_updater(upd)
                except Exception:
                    pass
            entry.active_updaters.clear()

    def __len__(self) -> int:
        return len(self._store)

    def __contains__(self, uid: str) -> bool:
        return uid in self._store
