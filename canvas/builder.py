"""High-level builder for Matemium.

Fluent API for authoring content. Layout is delegated to ``LayoutEngine``;
measurement and rendering share ``measure.py``.
"""

from __future__ import annotations

import contextlib
from typing import Any, Dict, List, Optional, Tuple, Union, Iterator

from manim import WHITE

from .dsl import (
    CameraFocus,
    CameraInspect,
    CanvasElement,
    CanvasSettings,
    CameraMove,
    CameraKeyframe,  # Phase 3
    EntryAnimation,
    PlotTrace,
    SheetDSL,
    SolidLift,
    SolidRotate,
    StateBehavior,
    TapeObject,
    WorldObject,  # Phase 5
)
from .coords import WorldTransform, Vector3, resolve_world_position  # Phase 4
from .measure import _OBJECT_KINDS  # for add_object
from .diagrams import grid_cell_center, parse_grid_content
from .layout import LayoutEngine, Style
from .plots import format_quadratic_tex
from .rich_text import RunInput, RichInput, normalize_rich_input



class TapeBuilder:
    """Authoring sub-builder for a specific tape."""
    def __init__(self, builder: "CanvasBuilder", tape_id: str):
        self._builder = builder
        self.tape_id = tape_id

    def _with_tape(self, func, *args, **kwargs):
        tape = self._builder._tapes.get(self.tape_id)
        if tape:
            with self._builder.in_object_space(tape.id):
                func(*args, **kwargs)
        return self

    def add_text(self, *args, **kwargs): return self._with_tape(self._builder.add_text, *args, **kwargs)
    def add_heading(self, *args, **kwargs): return self._with_tape(self._builder.add_heading, *args, **kwargs)
    def add_body(self, *args, **kwargs): return self._with_tape(self._builder.add_body, *args, **kwargs)
    def add_math(self, *args, **kwargs): return self._with_tape(self._builder.add_math, *args, **kwargs)
    def add_flex_row(self, *args, **kwargs): return self._with_tape(self._builder.add_flex_row, *args, **kwargs)
    def add_flex_column(self, *args, **kwargs): return self._with_tape(self._builder.add_flex_column, *args, **kwargs)
    def add_observation(self, *args, **kwargs): return self._with_tape(self._builder.add_observation, *args, **kwargs)
    def add_concept(self, *args, **kwargs): return self._with_tape(self._builder.add_concept, *args, **kwargs)
    def add_grid_board(self, *args, **kwargs): return self._with_tape(self._builder.add_grid_board, *args, **kwargs)
    def add_grid_mark(self, *args, **kwargs): return self._with_tape(self._builder.add_grid_mark, *args, **kwargs)
    def add_grid_moves(self, *args, **kwargs): return self._with_tape(self._builder.add_grid_moves, *args, **kwargs)
    def add_quadratic_plot(self, *args, **kwargs): return self._with_tape(self._builder.add_quadratic_plot, *args, **kwargs)
    def add_quadratic_compare(self, *args, **kwargs): return self._with_tape(self._builder.add_quadratic_compare, *args, **kwargs)
    def add_plot_trace(self, *args, **kwargs): return self._with_tape(self._builder.add_plot_trace, *args, **kwargs)
    def add_3d(self, *args, **kwargs): return self._with_tape(self._builder.add_3d, *args, **kwargs)
    def add_solid(self, *args, **kwargs): return self._with_tape(self._builder.add_solid, *args, **kwargs)
    def add_solid_lift(self, *args, **kwargs): return self._with_tape(self._builder.add_solid_lift, *args, **kwargs)
    def add_solid_rotate(self, *args, **kwargs): return self._with_tape(self._builder.add_solid_rotate, *args, **kwargs)
    def add_solid_rotation(self, *args, **kwargs): return self._with_tape(self._builder.add_solid_rotation, *args, **kwargs)
    def add_camera_inspect(self, *args, **kwargs): return self._with_tape(self._builder.add_camera_inspect, *args, **kwargs)
    def add_camera_focus(self, *args, **kwargs): return self._with_tape(self._builder.add_camera_focus, *args, **kwargs)
    def add_relative(self, *args, **kwargs): return self._with_tape(self._builder.add_relative, *args, **kwargs)
    def add_raw(self, *args, **kwargs): return self._with_tape(self._builder.add_raw, *args, **kwargs)
    def add_camera_move(self, *args, **kwargs): return self._with_tape(self._builder.add_camera_move, *args, **kwargs)

    def text_spec(self, *args, **kwargs): return self._builder.text_spec(*args, **kwargs)
    def math_spec(self, *args, **kwargs): return self._builder.math_spec(*args, **kwargs)
    def grid_board_spec(self, *args, **kwargs): return self._builder.grid_board_spec(*args, **kwargs)
    def grid_mark_spec(self, *args, **kwargs): return self._builder.grid_mark_spec(*args, **kwargs)
    def grid_moves_spec(self, *args, **kwargs): return self._builder.grid_moves_spec(*args, **kwargs)
    def add_space(self, height: float = 1.0):
        layout = self._builder._layouts.get(self.tape_id)
        if layout:
            layout._current_y -= height
        return self


class CanvasBuilder:
    """Fluent builder for the canvas tape/sheet."""

    def __init__(self, title: str = "Matemium", **settings_kwargs: Any):
        canvas_settings = settings_kwargs.pop("canvas_settings", None)
        if canvas_settings is not None:
            self.settings = canvas_settings
        else:
            self.settings = CanvasSettings.for_reels(title=title, **settings_kwargs)
        self.dsl = SheetDSL(canvas_settings=self.settings)
        self._tapes: Dict[str, TapeObject] = {}
        self._current_tape: Optional[TapeObject] = None
        self._layouts: Dict[str, LayoutEngine] = {}
        self._layout = None
        self._current_layout = None
        self._counter = 0
        self._boards: Dict[str, CanvasElement] = {}
        self._last_flex_ids: List[str] = []
        self._placed_transforms: Dict[str, WorldTransform] = {}  # for relative resolution Phase 4
        self._placed_objects: Dict[str, Any] = {}  # for anchor lookup

    def _get_id(self, prefix: str = "el") -> str:
        self._counter += 1
        return f"{prefix}_{self._counter}"

    def _add(self, el: CanvasElement) -> "CanvasBuilder":
        # Phase 2/3: elements live in the current tape context (root_tape by default).
        # Supports multiple tapes via in_object_space("tape_id") or add_tape + scoping.
        # Also populates timeline for backward compat.
        current_tape = getattr(self, "_current_tape", None)
        if not current_tape:
            raise RuntimeError("Cannot add 2D element without an active TapeObject context. Use builder.add_tape().")
        if current_tape:
            current_tape.local_elements.append(el)
        self.dsl.add_element(el)
        self._placed_objects[el.id] = el
        self._placed_objects[el.id] = el
        return self

    def _track_board(self, el: CanvasElement) -> None:
        if el.type == "GridBoard":
            self._boards[el.id] = el

    def _board_cell_size(self, board: CanvasElement) -> float:
        c = parse_grid_content(board.content)
        cols = int(c.get("cols", 3))
        if board.layout and cols > 0:
            return board.layout.width / cols
        return float(c.get("cell_size", 1.0))

    def _apply_after_3d(self, style: Dict[str, Any], kwargs: Dict[str, Any]) -> Dict[str, Any]:
        style = dict(style)
        if kwargs.pop("after_3d", False):
            mt = style.get("margin-top", style.get("margin", 0) or 0)
            style["margin-top"] = float(mt) + 1.8
        return style

    # ---------------- High-level content methods ----------------

    def _text_content(self, text: RichInput) -> Union[str, Dict[str, Any], List[RunInput]]:
        runs = normalize_rich_input(text)
        if runs is not None:
            return {"runs": [{"text": r.text, **self._run_style_dict(r)} for r in runs]}
        return str(text)

    @staticmethod
    def _run_style_dict(run) -> Dict[str, Any]:
        d: Dict[str, Any] = {}
        color = str(run.color)
        if color.upper() not in ("WHITE", "#FFF", "#FFFFFF"):
            d["color"] = color
        if run.highlight is not None:
            d["highlight"] = run.highlight
        if run.underline:
            d["underline"] = True
        if run.bold:
            d["bold"] = True
        if run.italic:
            d["italic"] = True
        if run.font_size != 36:
            d["font_size"] = run.font_size
        if run.opacity != 1.0:
            d["opacity"] = run.opacity
        return d

    def run(self, text: str, **style: Any) -> Dict[str, Any]:
        """One inline styled fragment — letter, word, or phrase."""
        return {"text": text, **style}

    def add_text(
        self,
        text: RichInput,
        *,
        id: Optional[str] = None,
        style: Optional[Dict[str, Any]] = None,
        wrap: Optional[bool] = None,
        **kwargs: Any,
    ) -> "CanvasBuilder":
        """Add text — plain string or a list of styled runs (letter/word/phrase granularity)."""
        style = self._apply_after_3d(style or {}, kwargs)
        if wrap is not None:
            style["wrap"] = wrap
        el = CanvasElement(
            id=id or self._get_id("text"),
            type="Text",
            content=self._text_content(text),
            entry_animation=EntryAnimation(type="FadeIn", run_time=1.0),
            **kwargs,
        )
        return self._add(self._layout.place_block(el, style))

    def add_heading(self, text: RichInput, **kwargs: Any) -> "CanvasBuilder":
        """Short title text — scales to fit, does not wrap by default."""
        style = dict(kwargs.pop("style", {}) or {})
        style.setdefault("wrap", False)
        style.setdefault("margin-bottom", 1.1)
        return self.add_text(text, style=style, **kwargs)

    def add_body(self, text: RichInput, **kwargs: Any) -> "CanvasBuilder":
        """Body / explanatory text — wraps by default."""
        style = dict(kwargs.pop("style", {}) or {})
        style.setdefault("wrap", True)
        return self.add_text(text, style=style, **kwargs)

    def add_math(
        self,
        latex: str,
        *,
        id: Optional[str] = None,
        label: Optional[str] = None,
        run_time: float = 1.5,
        style: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> "CanvasBuilder":
        content = latex
        if label:
            content = f"{label} \\\\ {latex}"
        style = self._apply_after_3d(style or {}, kwargs)
        el = CanvasElement(
            id=id or self._get_id("math"),
            type="MathTex",
            content=content,
            entry_animation=EntryAnimation(type="Write", run_time=run_time),
            **kwargs,
        )
        return self._add(self._layout.place_block(el, style))

    def add_3d(
        self,
        equation: Optional[str] = None,
        *,
        id: Optional[str] = None,
        pitch: Optional[float] = None,
        run_time: float = 0.8,
        style: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> "CanvasBuilder":
        content: Optional[Dict[str, Any]] = {"equation": equation} if equation else None
        el = CanvasElement(
            id=id or self._get_id("3d"),
            type="ThreeDGraph",
            content=content,
            entry_animation=EntryAnimation(type="FadeIn", run_time=run_time),
            state_behavior=StateBehavior(type="rotate_slowly", params={"speed": 0.3}),
            pitch=pitch,
            static_phi=25.0,
            static_theta=-50.0,
            static_scale=0.9,
            **kwargs,
        )
        return self._add(self._layout.place_block(el, style))

    def add_solid(
        self,
        shape: str = "cube",
        *,
        size: float = 2.0,
        id: Optional[str] = None,
        color: str = "#5eb3ff",
        opacity: float = 0.82,
        lift: float = 0.0,
        parts: Optional[List[Dict[str, Any]]] = None,
        labels: Optional[List[Dict[str, Any]]] = None,
        run_time: float = 1.0,
        style: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> "CanvasBuilder":
        """Add a volumetric 3D solid — center on the tape at z = 0, straddling the plane."""
        content: Dict[str, Any] = {
            "shape": shape,
            "size": size,
            "color": color,
            "opacity": opacity,
            "lift": lift,
        }
        if parts is not None:
            content = {"parts": parts, "size": size, "lift": lift}
        if labels is not None:
            content["labels"] = labels
        eid = id or self._get_id("solid")
        el = CanvasElement(
            id=eid,
            type="Solid3D",
            content=content,
            entry_animation=EntryAnimation(type="FadeIn", run_time=run_time),
            static_phi=55.0,
            static_theta=-45.0,
            **kwargs,
        )
        placed = self._layout.place_block(el, style)
        self._add(placed)
        return self

    def solid_label(
        self,
        text: str,
        at: tuple[float, float, float],
        *,
        color: str = "#ffdd66",
        font_size: int = 22,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """One billboard label spec for ``add_solid(..., labels=[...])``."""
        spec: Dict[str, Any] = {"text": text, "at": list(at), "color": color, "font_size": font_size}
        spec.update(kwargs)
        return spec

    def solid_spec(
        self,
        shape: str = "cube",
        *,
        id: Optional[str],
        size: float = 2.0,
        color: str = "#5eb3ff",
        opacity: float = 0.82,
        lift: float = 0.0,
        parts: Optional[List[Dict[str, Any]]] = None,
        style: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Flex-row spec for a volumetric solid."""
        content: Dict[str, Any] = {
            "shape": shape,
            "size": size,
            "color": color,
            "opacity": opacity,
            "lift": lift,
        }
        if parts is not None:
            content = {"parts": parts, "size": size, "lift": lift}
        return self.element_spec(
            CanvasElement(
                id=id,
                type="Solid3D",
                content=content,
                entry_animation=EntryAnimation(type="FadeIn", run_time=1.0),
                **kwargs,
            ),
            style=style,
        )

    def add_solid_lift(
        self,
        element_id: str,
        *,
        lift: float = 1.5,
        run_time: float = 1.2,
    ) -> "CanvasBuilder":
        """Raise a solid off the tape so the camera can orbit around it."""
        self.dsl.add_solid_lift(
            SolidLift(
                id=self._get_id("lift"),
                element_id=element_id,
                lift=lift,
                run_time=run_time,
            )
        )
        return self

    def rotate_shot(
        self,
        *,
        axis: str = "y",
        angle: float = 90.0,
        space: str = "local",
        hold: float = 0.0,
        run_time: float = 1.2,
        rate_func: str = "smooth",
    ) -> Dict[str, Any]:
        """One keyframe for ``add_solid_rotation(..., path=[...])``."""
        return {
            "axis": axis,
            "angle": angle,
            "space": space,
            "hold": hold,
            "run_time": run_time,
            "rate_func": rate_func,
        }

    def add_solid_rotate(
        self,
        element_id: str,
        *,
        path: Optional[List[Dict[str, Any]]] = None,
        preset: Optional[str] = None,
        preset_kwargs: Optional[Dict[str, Any]] = None,
        axis: str = "y",
        angle: float = 90.0,
        space: str = "local",
        run_time: float = 1.2,
        hold: float = 0.0,
        rate_func: str = "smooth",
    ) -> "CanvasBuilder":
        """Rotate a solid — one shot, preset, or pass ``path=`` for multi-step."""
        self.dsl.add_solid_rotate(
            SolidRotate(
                id=self._get_id("rotate"),
                element_id=element_id,
                path=path,
                preset=preset,
                preset_kwargs=dict(preset_kwargs or {}),
                axis=axis,
                angle=angle,
                space=space,  # type: ignore[arg-type]
                run_time=run_time,
                hold=hold,
                rate_func=rate_func,
            )
        )
        return self

    def add_solid_rotation(
        self,
        element_id: str,
        *,
        path: Optional[List[Dict[str, Any]]] = None,
        preset: Optional[str] = None,
        preset_kwargs: Optional[Dict[str, Any]] = None,
        axis: str = "y",
        angle: float = 90.0,
        space: str = "local",
        run_time: float = 1.2,
        hold: float = 0.0,
        rate_func: str = "smooth",
    ) -> "CanvasBuilder":
        """Multi-step rotation path with holds, or preset tour."""
        self.dsl.add_solid_rotate(
            SolidRotate(
                id=self._get_id("rotate"),
                element_id=element_id,
                path=path,
                preset=preset,
                preset_kwargs=dict(preset_kwargs or {}),
                axis=axis,
                angle=angle,
                space=space,  # type: ignore[arg-type]
                run_time=run_time,
                hold=hold,
                rate_func=rate_func,
            )
        )
        return self

    def inspect_shot(
        self,
        *,
        phi: float = 65.0,
        theta: float = -50.0,
        zoom: float = 1.0,
        hold: float = 0.0,
        run_time: float = 1.5,
        target_offset: Optional[tuple[float, float, float]] = None,
        rate_func: str = "smooth",
    ) -> Dict[str, Any]:
        """One keyframe for ``add_camera_inspect(..., path=[...])``."""
        shot: Dict[str, Any] = {
            "phi": phi,
            "theta": theta,
            "zoom": zoom,
            "hold": hold,
            "run_time": run_time,
            "rate_func": rate_func,
        }
        if target_offset is not None:
            shot["target_offset"] = list(target_offset)
        return shot

    def add_camera_inspect(
        self,
        element_id: str,
        *,
        path: Optional[List[Dict[str, Any]]] = None,
        preset: Optional[str] = None,
        preset_kwargs: Optional[Dict[str, Any]] = None,
        curve: str = "smooth",
        phi: float = 65.0,
        theta: float = -50.0,
        run_time: float = 1.6,
        hold_time: float = 0.0,
        orbit: bool = False,
        orbit_degrees: float = 360.0,
        orbit_run_time: float = 4.0,
        return_to_sheet: bool = True,
        return_run_time: float = 1.0,
        rate_func: str = "smooth",
    ) -> "CanvasBuilder":
        """Inspect a 3D target along a keyframe path, preset, or legacy orbit."""
        self.dsl.add_camera_inspect(
            CameraInspect(
                id=self._get_id("inspect"),
                element_id=element_id,
                path=path,
                preset=preset,
                preset_kwargs=dict(preset_kwargs or {}),
                curve=curve,  # type: ignore[arg-type]
                phi=phi,
                theta=theta,
                run_time=run_time,
                hold_time=hold_time,
                orbit=orbit,
                orbit_degrees=orbit_degrees,
                orbit_run_time=orbit_run_time,
                return_to_sheet=return_to_sheet,
                return_run_time=return_run_time,
                rate_func=rate_func,
            )
        )
        return self

    def add_observation(self, text: str, **kwargs: Any) -> "CanvasBuilder":
        return self.add_body(text, **kwargs)

    def add_concept(
        self,
        title: str,
        explanation: str,
        formula: Optional[str] = None,
        **kwargs: Any,
    ) -> "CanvasBuilder":
        lines = [title, explanation]
        if formula:
            lines.append(formula)
        return self.add_body("\n".join(lines), **kwargs)

    # ---------------- Flex spec helpers ----------------

    def text_spec(
        self,
        text: RichInput,
        style: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        content = self._text_content(text) if not isinstance(text, str) else text
        return {"type": "text", "content": content, "style": style or {}, **kwargs}

    def math_spec(self, latex: str, style: Optional[Dict[str, Any]] = None, **kwargs: Any) -> Dict[str, Any]:
        return {"type": "math", "content": latex, "style": style or {}, **kwargs}

    def element_spec(
        self,
        element: CanvasElement,
        style: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Generic flex item — pass any ``CanvasElement`` (project helpers use this)."""
        return {"type": "element", "element": element, "style": style or {}, **kwargs}

    def observation_spec(self, text: str, style: Optional[Dict[str, Any]] = None, **kwargs: Any) -> Dict[str, Any]:
        return {"type": "observation", "content": text, "style": style or {}, **kwargs}

    def grid_board_spec(
        self,
        *,
        rows: int = 3,
        cols: int = 3,
        cell_size: float = 1.0,
        id: Optional[str] = None,
        style: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Spec for ``add_flex_row`` / ``add_flex_column`` — embed a grid board."""
        return {
            "type": "grid_board",
            "rows": rows,
            "cols": cols,
            "cell_size": cell_size,
            "id": id,
            "style": style or {},
            **kwargs,
        }

    # ---------------- Diagrams (grids, board games) ----------------

    def add_grid_board(
        self,
        *,
        rows: int = 3,
        cols: int = 3,
        cell_size: float = 1.0,
        id: Optional[str] = None,
        style: Optional[Dict[str, Any]] = None,
        run_time: float = 1.2,
        **kwargs: Any,
    ) -> str:
        """Add a grid board in vertical flow. Returns board id for ``add_grid_mark``."""
        eid = id or self._get_id("board")
        el = CanvasElement(
            id=eid,
            type="GridBoard",
            content={
                "rows": rows,
                "cols": cols,
                "cell_size": cell_size,
            },
            entry_animation=EntryAnimation(type="Create", run_time=run_time),
            **kwargs,
        )
        placed = self._layout.place_block(el, style)
        self._track_board(placed)
        self._add(placed)
        return eid

    def add_grid_mark(
        self,
        board_id: str,
        row: int,
        col: int,
        symbol: str,
        *,
        run_time: float = 0.55,
        **kwargs: Any,
    ) -> "CanvasBuilder":
        """Place X/O on a board cell (overlay — does not advance vertical flow)."""
        board = self._boards.get(board_id)
        if board is None:
            raise KeyError(f"Unknown board id: {board_id!r}")
        c = parse_grid_content(board.content)
        rows, cols = int(c.get("rows", 3)), int(c.get("cols", 3))
        cell = self._board_cell_size(board)
        pos = grid_cell_center(board.canvas_position, row, col, rows, cols, cell)
        mark_size = cell * 0.72
        el = CanvasElement(
            id=self._get_id("mark"),
            type="GridMark",
            content={"symbol": symbol, "cell_size": cell},
            entry_animation=EntryAnimation(type="GrowFromCenter", run_time=run_time),
            auto_focus=False,
            **kwargs,
        )
        return self._add(
            self._layout.place_overlay(el, pos[0], pos[1], mark_size, mark_size)
        )

    def add_grid_moves(
        self,
        board_id: str,
        moves: List[tuple],
        *,
        run_time: float = 0.55,
    ) -> "CanvasBuilder":
        """Play a sequence of moves: [(symbol, row, col), ...]."""
        for move in moves:
            symbol, row, col = move[0], int(move[1]), int(move[2])
            self.add_grid_mark(board_id, row, col, symbol, run_time=run_time)
        return self

    # ---------------- Flex containers ----------------

    def add_flex_row(
        self,
        items: List[Dict[str, Any]],
        *,
        gap: float = 0.5,
        justify_content: str = "start",
        align_items: str = "center",
        style: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> "CanvasBuilder":
        """Place each item as its own timeline element (separate ids, individual focus).

        Items in one row share a ``flex_group`` so they reveal together; use
        ``builder.last_flex_ids`` for the ids just added.
        """
        measured = self._prepare_flex_items(items)
        placed = self._layout.layout_flex_row(
            measured,
            gap=gap,
            justify_content=justify_content,
            align_items=align_items,
            container_style=Style.from_dict(style),
        )
        self._register_flex_placed(placed)
        return self

    def add_flex_column(
        self,
        items: List[Dict[str, Any]],
        *,
        gap: float = 0.8,
        justify_content: str = "start",
        align_items: str = "center",
        style: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> "CanvasBuilder":
        measured = self._prepare_flex_items(items)
        placed = self._layout.layout_flex_column(
            measured,
            gap=gap,
            justify_content=justify_content,
            align_items=align_items,
            container_style=Style.from_dict(style),
        )
        self._register_flex_placed(placed)
        return self

    def _register_flex_placed(self, placed: List[CanvasElement]) -> None:
        group_id = self._get_id("flex") if len(placed) > 1 else None
        self._last_flex_ids = []
        for el in placed:
            if group_id is not None:
                el.flex_group = group_id
                el.auto_focus = False
            self._track_board(el)
            self._add(el)
            self._last_flex_ids.append(el.id)

    @property
    def last_flex_ids(self) -> List[str]:
        """Ids from the most recent ``add_flex_row`` / ``add_flex_column``."""
        return list(self._last_flex_ids)

    def _prepare_flex_items(self, items: List[Dict[str, Any]]):
        prepared = []
        for spec in items:
            itype = spec.get("type", "text")
            icontent = spec.get("content")
            if icontent is None:
                icontent = spec.get("text") or spec.get("latex") or ""
            istyle = dict(spec.get("style") or {})
            if itype in ("observation", "body"):
                istyle.setdefault("wrap", True)
            iel = self._create_element_for_flex(itype, icontent, spec)
            prepared.append(self._layout.measure(iel, Style.from_dict(istyle)))
        return prepared

    def _create_element_for_flex(
        self,
        itype: str,
        icontent: Any,
        spec: Dict[str, Any],
    ) -> CanvasElement:
        eid = spec.get("id") or self._get_id(itype[:4])
        if itype in ("text", "observation", "body"):
            if isinstance(icontent, list):
                runs = normalize_rich_input(icontent)
                content = (
                    {"runs": [{"text": r.text, **self._run_style_dict(r)} for r in runs]}
                    if runs
                    else ""
                )
            elif isinstance(icontent, dict) and "runs" in icontent:
                content = icontent
            else:
                content = str(icontent)
            return CanvasElement(
                id=eid,
                type="Text",
                content=content,
                entry_animation=EntryAnimation(type="FadeIn", run_time=1.0),
            )
        if itype == "math":
            return CanvasElement(
                id=eid,
                type="MathTex",
                content=icontent,
                entry_animation=EntryAnimation(type="Write", run_time=spec.get("run_time", 1.5)),
            )
        if itype in ("3d", "three_d", "threed"):
            return CanvasElement(
                id=eid,
                type="ThreeDGraph",
                content={"equation": icontent} if isinstance(icontent, str) else icontent,
                entry_animation=EntryAnimation(type="FadeIn", run_time=spec.get("run_time", 1.2)),
                state_behavior=StateBehavior(type="rotate_slowly", params={"speed": 0.3}),
                pitch=spec.get("pitch"),
                static_scale=0.9,
            )
        if itype in ("grid_board", "grid", "board"):
            return CanvasElement(
                id=eid,
                type="GridBoard",
                content={
                    "rows": int(spec.get("rows", 3)),
                    "cols": int(spec.get("cols", 3)),
                    "cell_size": float(spec.get("cell_size", 1.0)),
                },
                entry_animation=EntryAnimation(type="Create", run_time=spec.get("run_time", 1.2)),
            )
        if itype == "element":
            el = spec.get("element")
            if isinstance(el, CanvasElement):
                if spec.get("id"):
                    el.id = str(spec["id"])
                return el
        return CanvasElement(
            id=eid,
            type="Text",
            content=str(icontent),
            entry_animation=EntryAnimation(type="FadeIn", run_time=1.0),
        )

    # ---------------- 2D quadratic plots ----------------

    def quad_plot_spec(
        self,
        a: float,
        b: float,
        c: float,
        *,
        formula: Optional[str] = None,
        x_range: tuple[float, float] = (-2.5, 3.5),
        x_start: float = 0.0,
        color: str = "#5eb3ff",
        **kwargs: Any,
    ) -> Dict[str, Any]:
        return {
            "a": a,
            "b": b,
            "c": c,
            "formula": formula or format_quadratic_tex(a, b, c),
            "x_range": x_range,
            "x_start": x_start,
            "color": color,
            **kwargs,
        }

    def add_quadratic_plot(
        self,
        a: float,
        b: float,
        c: float,
        *,
        id: Optional[str] = None,
        style: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> str:
        """Single 2D quadratic graph with formula and trace dot.

        NOTE: This is legacy convenience. For a more abstract engine, prefer
        defining such helpers in your project's helpers.py (or using
        composition of lower-level primitives + styling). See USAGE.md.
        """
        eid = id or self._get_id("qplot")
        el = CanvasElement(
            id=eid,
            type="QuadraticPlot",
            content=self.quad_plot_spec(a, b, c, **kwargs),
            entry_animation=EntryAnimation(type="Create", run_time=1.2),
        )
        self._add(self._layout.place_block(el, style))
        return eid

    def add_quadratic_compare(
        self,
        left: Dict[str, Any],
        right: Dict[str, Any],
        *,
        id: Optional[str] = None,
        gap: float = 0.55,
        style: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> str:
        """Two quadratic graphs side by side — one timeline entry, one focus."""
        eid = id or self._get_id("qpair")
        el = CanvasElement(
            id=eid,
            type="QuadraticPlotPair",
            content={"left": left, "right": right, "gap": gap, **kwargs},
            entry_animation=EntryAnimation(type="Create", run_time=1.4),
        )
        self._add(self._layout.place_block(el, style))
        return eid

    def add_plot_trace(
        self,
        element_id: str,
        *,
        plot_index: int = 0,
        x_from: float = -2.0,
        x_to: float = 2.0,
        run_time: float = 3.0,
        show_readout: bool = True,
    ) -> "CanvasBuilder":
        """Animate the dot along a plot to show y changing with x."""
        self.dsl.add_plot_trace(
            PlotTrace(
                id=self._get_id("trace"),
                element_id=element_id,
                plot_index=plot_index,
                x_from=x_from,
                x_to=x_to,
                run_time=run_time,
                show_readout=show_readout,
            )
        )
        return self

    def add_camera_focus(
        self,
        element_id: str,
        *,
        mode: str = "isolate",
        zoom: float = 2.0,
        dim_opacity: float = 0.1,
        run_time: float = 1.1,
        highlight: bool = True,
        hold_time: float = 1.2,
        reset_zoom: bool = True,
        reset_run_time: float = 0.9,
    ) -> "CanvasBuilder":
        """Focus on an element.

        ``mode="isolate"`` (default): dim the tape, pan + zoom camera to the target, restore.
        ``mode="overlay"``: fixed-screen magnifier; scroll position unchanged.
        """
        self.dsl.add_camera_focus(
            CameraFocus(
                id=self._get_id("focus"),
                element_id=element_id,
                mode=mode,  # type: ignore[arg-type]
                zoom=zoom,
                dim_opacity=dim_opacity,
                run_time=run_time,
                highlight=highlight,
                hold_time=hold_time,
                reset_zoom=reset_zoom,
                reset_run_time=reset_run_time,
            )
        )
        return self

    # ---------------- Camera ----------------

    def add_camera_move(self, dy: float = 0.0, run_time: float = 2.0, **kwargs: Any) -> "CanvasBuilder":
        """Legacy explicit scroll. New content auto-focuses on reveal — manual moves are rarely needed."""
        target_y = self._layout.flow.last_bottom + (self.settings.frame_height / 2) - dy
        self.dsl.add_camera_move(
            CameraMove(
                id=self._get_id("cam"),
                target_position=(0.0, target_y, 0.0),
                run_time=run_time,
                **kwargs,
            )
        )
        self._layout.flow.y = target_y
        return self

    def add_camera_keyframe(
        self,
        *,
        target: Any,
        time: float = 0.0,
        duration: float = 2.0,
        rate_func: str = "smooth",
        params: Optional[Dict[str, Any]] = None,
    ) -> "CanvasBuilder":
        """Phase 3: add CameraKeyframe for generalized 3D observation (world point, object, tape scroll)."""
        kf = CameraKeyframe(
            id=self._get_id("kf"),
            time=time,
            target=target,
            duration=duration,
            rate_func=rate_func,
            params=params or {},
        )
        self.dsl.timeline.append(kf)
        return self

    def scroll_tape(
        self,
        local_y: float,
        *,
        tape_id: str = "root_tape",
        run_time: float = 2.0,
        rate_func: str = "smooth",
        framing_mode: str = "sheet",
        dim_others: bool = True,
        dim_opacity: float = 0.15,
    ) -> "CanvasBuilder":
        """High-level sugar to enter tape-scroll-mode on a TapeObject.

        This activates the tape's internal 2D mechanisms (local scroll, lazy reveal
        driven by local_y, focus, flex, etc.) while the outer camera respects the
        tape's world_transform.

        When dim_others=True (default), other 3D objects and other tapes' content
        are dimmed (to dim_opacity) so attention stays on the active tape.

        Use dim_others=False to keep everything at full opacity.
        """
        from .dsl import TapeScroll
        target = TapeScroll(
            tape_id=tape_id,
            local_y=local_y,
            framing_mode=framing_mode,
            dim_others=dim_others,
            dim_opacity=dim_opacity,
        )
        return self.add_camera_keyframe(
            target=target,
            duration=run_time,
            rate_func=rate_func,
        )

    def observe_object(
        self,
        object_id: str,
        *,
        anchor: str = "center",
        run_time: float = 2.0,
        rate_func: str = "smooth",
        framing: str = "cinematic",
        **params: Any,
    ) -> "CanvasBuilder":
        """High-level sugar for normal cinematic 3D observation of any object.

        Works for free 3D objects AND for TapeObjects (treated as 3D planes,
        no internal tape logic activated).
        Use scroll_tape() to activate classic tape scroll + reveal on a tape.
        Use framing="face_on" to align the camera perfectly with the object's local plane.
        """
        from .dsl import ObjectAnchor
        target = ObjectAnchor(object_id=object_id, anchor=anchor, framing=framing)
        return self.add_camera_keyframe(
            target=target,
            duration=run_time,
            rate_func=rate_func,
            params=params or None,
        )

    def add_tape(
        self,
        id: Optional[str] = None,
        *,
        frame_width: Optional[float] = None,
        frame_height: Optional[float] = None,
        **kwargs: Any,
    ) -> "TapeBuilder":
        if "position" in kwargs or "rotation" in kwargs or "scale" in kwargs:
            raise ValueError(
                "Tapes are now purely 2D layout canvases and do not exist in 3D space. "
                "Arguments 'position', 'rotation', and 'scale' are no longer supported in add_tape(). "
                "To place objects in the 3D world, use add_object() instead."
            )
        """Create a new TapeObject (2D canvas context).

        Returns a TapeBuilder instance to author content inside its local 2D space.
        """
        tape_id = id or self._get_id("tape")
        tape_settings = CanvasSettings(
            frame_width=frame_width or self.settings.frame_width,
            frame_height=frame_height or self.settings.frame_height,
        )
        new_tape = TapeObject(
            id=tape_id,
            local_elements=[],
            local_canvas_settings=tape_settings,
        )
        self._tapes[tape_id] = new_tape

        tape_layout = LayoutEngine(
            frame_width=tape_settings.frame_width,
            frame_height=tape_settings.frame_height,
            scope=new_tape,
        )
        self._layouts[tape_id] = tape_layout

        # Store as first-class tape canvas
        self.dsl.tapes.append(new_tape)

        # Track for placement and scoping
        self._placed_objects[tape_id] = new_tape

        return TapeBuilder(self, tape_id)

    def add_world_object(self, wo: WorldObject) -> str:
        """Phase 5/6: place a top-level WorldObject in the 3D world."""
        if wo.element and getattr(wo.element, 'type', None) in ('Tape', 'tape'):
            raise ValueError("Tapes can no longer be added as WorldObjects. Use add_tape() instead.")
        self.dsl.root_objects.append(wo)
        return wo.id
        return wo.id

    def add_object(
        self,
        type: str,
        *,
        relative_to: Optional[str] = None,
        anchor: str = "center",
        content: Optional[Any] = None,
        style: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> str:
        """Phase 9 high-level API: add a (possibly registered) object in world or relative to another.

        If type is registered, uses its builder.
        Otherwise, creates a CanvasElement or WorldObject with the given transform.
        """
        position = kwargs.get("position", (0.0, 0.0, 0.0))
        rotation = kwargs.get("rotation", (0.0, 0.0, 0.0))
        scale = kwargs.get("scale", 1.0)
        wt = WorldTransform(
            position=Vector3(*position),
            rotation=Vector3(*rotation),
            scale=scale,
        )
        if relative_to:
            base = self._placed_transforms.get(relative_to, WorldTransform())
            other = self._placed_objects.get(relative_to)
            if other and hasattr(other, 'get_anchor'):
                anchor_pos = other.get_anchor(anchor)
                wt.position = Vector3(
                    wt.position.x + base.position.x + anchor_pos.x,
                    wt.position.y + base.position.y + anchor_pos.y,
                    wt.position.z + base.position.z + anchor_pos.z,
                )
            else:
                wt.position = resolve_world_position(wt.position.as_tuple(), relative_to=base)

        if type.lower() == "tape":
            raise ValueError("Cannot create a Tape via add_object(). Tapes are 2D canvases, not 3D objects. Use add_tape() instead.")
            
        if type in _OBJECT_KINDS and _OBJECT_KINDS[type].get("build"):
            # use registered build to create element
            fake_elem = CanvasElement(id=self._get_id(type.lower()), type=type, content=content or {}, world_transform=wt)
            # the build will be used later in render
            elem = fake_elem
        else:
            elem = CanvasElement(
                id=self._get_id(type.lower()),
                type=type,
                content=content,
            )
        # place as world object
        wo = WorldObject(id=elem.id, element=elem, transform=wt)
        self.dsl.root_objects.append(wo)
        return wo.id
        self._placed_transforms[elem.id] = wt
        self._placed_objects[elem.id] = wo
        return elem.id

    @contextlib.contextmanager
    def in_object_space(self, obj_id: str) -> Iterator[None]:
        """Phase 3/9: temporarily scope layout/positioning to a specific TapeObject's local space.

        This allows authoring content inside a secondary tape created with add_tape().

        Usage:
            tape_id = builder.add_tape("side_panel", position=(5, 0, 0), rotation=(0, 45, 0))
            with builder.in_object_space(tape_id):
                builder.add_text("content local to this tape")
                # normal add_* will target this tape's 2D local space
        """
        prev_tape = getattr(self, '_current_tape', None)
        prev_layout = getattr(self, '_current_layout', self._layout)
        prev_active_layout = self._layout
        obj = self._placed_objects.get(obj_id) or self._tapes.get(obj_id)
        if obj and hasattr(obj, 'local_elements'):
            self._current_tape = obj
            self._current_layout = self._layouts.get(obj_id, self._layout)
            self._layout = self._current_layout  # swap for flow-based add_* methods
        try:
            yield
        finally:
            self._current_tape = prev_tape
            self._current_layout = prev_layout
            self._layout = prev_active_layout

    def auto_camera(
        self,
        *,
        viewport_fraction: float = 0.65,
        run_time: float = 2.0,
        min_dy: float = 2.0,
    ) -> "CanvasBuilder":
        """Insert a camera move when accumulated content exceeds one viewport."""
        dy = self._layout.suggest_camera_dy(
            viewport_fraction=viewport_fraction,
            min_dy=min_dy,
        )
        if dy is not None:
            self.add_camera_move(dy=dy, run_time=run_time)
        return self

    # Phase 4: relative/absolute positioning for 3D world + tape objects
    def place_relative_to(
        self,
        other_id: str,
        local_offset: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        *,
        anchor: str = "center",
        style: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> CanvasElement:
        """Phase 4: compute a CanvasElement with world pos relative to other_id's anchor + offset.
        Uses placed transforms and object anchors (enhanced in TapeObject etc).
        """
        base = self._placed_transforms.get(other_id, WorldTransform())
        other = self._placed_objects.get(other_id)
        anchor_pos = Vector3(0, 0, 0)
        if other and hasattr(other, 'get_anchor'):
            anchor_pos = other.get_anchor(anchor)
        rel = resolve_world_position(
            tuple(a + b for a, b in zip(local_offset, anchor_pos.as_tuple())),
            relative_to=base,
        )
        el = CanvasElement(
            id=self._get_id("rel"),
            type="rel",
        )
        if getattr(self, '_current_tape', None):
            self._add(el)
        return el

    def add_relative(
        self,
        other_id: str,
        element: CanvasElement,
        local_offset: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        anchor: str = "center",
        style: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> str:
        """Add element positioned relative to other placed id's anchor."""
        base = self._placed_transforms.get(other_id, WorldTransform())
        other = self._placed_objects.get(other_id)
        anchor_pos = Vector3(0, 0, 0)
        if other and hasattr(other, 'get_anchor'):
            anchor_pos = other.get_anchor(anchor)
        rel = resolve_world_position(
            tuple(a + b for a, b in zip(local_offset, anchor_pos.as_tuple())),
            relative_to=base,
        )
        element.world_transform = WorldTransform(position=rel)
        if style:
            # apply layout style if needed
            pass
        self._add(element)
        self._placed_transforms[element.id] = element.world_transform
        return element.id

    # ---------------- Escape hatches ----------------

    def add_raw(self, el: Union[CanvasElement, "WorldObject"]) -> "CanvasBuilder":
        """Phase 5: support low-level 3D objects (WorldObject) or elements."""
        if isinstance(el, WorldObject):
            self.dsl.root_objects.append(el)
            return self
        if el.canvas_position[1] == 0.0 and el.layout is None:
            self._layout.flow.last_bottom -= 1.5
            el.canvas_position = (
                el.canvas_position[0],
                self._layout.flow.last_bottom,
                el.canvas_position[2],
            )
        return self._add(el)

    def add_explicit_camera(self, target_y: float, run_time: float = 2.0, **kwargs: Any) -> "CanvasBuilder":
        self.dsl.add_camera_move(
            CameraMove(
                id=self._get_id("cam"),
                target_position=(0.0, target_y, 0.0),
                run_time=run_time,
                **kwargs,
            )
        )
        self._layout.flow.y = target_y
        return self

    def build(self) -> SheetDSL:
        return self.dsl

    def to_scene(self, **kwargs):
        from .scene import CanvasScene
        return CanvasScene(dsl=self.build(), **kwargs)