"""High-level builder for Matemium.

Fluent API for authoring content. Layout is delegated to ``LayoutEngine``;
measurement and rendering share ``measure.py``.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

from manim import WHITE

from .dsl import (
    CameraFocus,
    CameraInspect,
    CanvasElement,
    CanvasSettings,
    CameraMove,
    EntryAnimation,
    PlotTrace,
    SheetDSL,
    SolidLift,
    SolidRotate,
    StateBehavior,
)
from .diagrams import grid_cell_center, parse_grid_content
from .layout import LayoutEngine, Style
from .plots import format_quadratic_tex
from .rich_text import RunInput, RichInput, normalize_rich_input


class CanvasBuilder:
    """Fluent builder for the canvas tape/sheet."""

    def __init__(self, title: str = "Matemium", **settings_kwargs: Any):
        canvas_settings = settings_kwargs.pop("canvas_settings", None)
        if canvas_settings is not None:
            self.settings = canvas_settings
        else:
            self.settings = CanvasSettings.for_reels(title=title, **settings_kwargs)
        self.dsl = SheetDSL(canvas_settings=self.settings)
        self._layout = LayoutEngine(
            frame_width=self.settings.frame_width,
            frame_height=self.settings.frame_height,
        )
        self._counter = 0
        self._boards: Dict[str, CanvasElement] = {}
        self._last_flex_ids: List[str] = []

    def _get_id(self, prefix: str = "el") -> str:
        self._counter += 1
        return f"{prefix}_{self._counter}"

    def _add(self, el: CanvasElement) -> "CanvasBuilder":
        self.dsl.add_element(el)
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
        """Single 2D quadratic graph with formula and trace dot."""
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

    # ---------------- Escape hatches ----------------

    def add_raw(self, el: CanvasElement) -> "CanvasBuilder":
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