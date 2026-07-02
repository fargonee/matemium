"""Lazy loading registry for heavy engines (Manim, canvas, etc.).

Implements deferred loading so the sidecar control plane (IPC, ping, get_status)
starts with zero heavy imports. Loading is triggered on first use of engine
features and can emit status events.

See PRODUCT-ARCHITECTURE-DECISIONS.md §6 for the design.
"""

from __future__ import annotations

import threading
from typing import Any

from . import paths

_lock = threading.RLock()

# Module-level state (process lifetime)
_state: dict[str, Any] = {
    "engine_loaded": False,
    "embeddings_loaded": False,
    "intelligence_loaded": False,
    "phase": "CORE_READY",
}

# Cache of loaded modules / symbols if needed later
_loaded: dict[str, Any] = {}


def get_phase() -> str:
    """Current loading phase: CORE_READY | ENGINE_LOADING | ENGINE_READY | EMBEDDING_LOADING | EMBEDDING_READY | INTELLIGENCE_LOADING | INTELLIGENCE_READY | ..."""
    return _state["phase"]


def _set_phase(phase: str, events: Any = None) -> None:
    _state["phase"] = phase
    if events is not None and hasattr(events, "emit"):
        try:
            events.emit("loading_phase", phase=phase)
        except Exception:
            # Never let event emission break the load
            pass


def _load_engine(events: Any = None) -> None:
    """Perform the heavy imports exactly once. Safe to call from multiple threads."""
    if _state["engine_loaded"]:
        return
    with _lock:
        if _state["engine_loaded"]:
            return
        _set_phase("ENGINE_LOADING", events)
        if events and hasattr(events, "emit"):
            try:
                events.emit("loading_phase", phase="ENGINE_LOADING", message="Loading Manim / canvas engine...")
            except Exception:
                pass

        # PAD Phase 2: Inject TinyTeX into PATH *before* importing Manim (which uses LaTeX).
        # This is safe and idempotent. The base dir can come from Rust later (asset manager).
        # For now it uses env + standard locations (see paths.get_tinytex_bin_dir).
        paths.inject_local_latex_env()

        # === HEAVY IMPORTS START HERE ===
        # These were previously at top level in handlers.py / workspace_project.py etc.
        import manim  # type: ignore  # noqa: F401
        from canvas import CanvasScene, ReelCutter, SheetDSL  # noqa: F401
        from canvas.dsl import CanvasElement, CameraKeyframe  # noqa: F401

        # Also pull render/workspace bits that depend on them when needed
        # (we import specific heavy symbols inside the actual handler functions)
        _loaded["manim"] = manim
        _loaded["CanvasScene"] = CanvasScene
        _loaded["SheetDSL"] = SheetDSL
        _loaded["ReelCutter"] = ReelCutter
        _loaded["CanvasElement"] = CanvasElement
        _loaded["CameraKeyframe"] = CameraKeyframe

        _state["engine_loaded"] = True
        _set_phase("ENGINE_READY", events)


def ensure_engine_loaded(events: Any = None) -> None:
    """Public entry point. Call before using any canvas/manim functionality."""
    _load_engine(events)


def is_engine_loaded() -> bool:
    return bool(_state["engine_loaded"])


def _load_embeddings(events: Any = None) -> None:
    """Lazy load the Jina ONNX embeddings model."""
    if _state["embeddings_loaded"]:
        return
    with _lock:
        if _state["embeddings_loaded"]:
            return
        _set_phase("EMBEDDING_LOADING", events)
        if events and hasattr(events, "emit"):
            try:
                events.emit("loading_phase", phase="EMBEDDING_LOADING", message="Loading jina-embeddings-v2-base-code (ONNX)...")
            except Exception:
                pass

        # Import will trigger model download if not cached (handled inside retriever)
        from .intelligence.retriever import VectorRetriever  # noqa: F401
        # The actual model load happens on first embed / index
        _state["embeddings_loaded"] = True
        _set_phase("EMBEDDING_READY", events)


def ensure_embeddings_loaded(events: Any = None) -> None:
    _load_embeddings(events)


def _load_intelligence(events: Any = None) -> None:
    """Load vector store + full retriever (requires embeddings)."""
    if _state["intelligence_loaded"]:
        return
    with _lock:
        if _state["intelligence_loaded"]:
            return
        ensure_embeddings_loaded(events)
        _set_phase("INTELLIGENCE_LOADING", events)
        if events and hasattr(events, "emit"):
            try:
                events.emit("loading_phase", phase="INTELLIGENCE_LOADING", message="Initializing LanceDB + RAG retriever...")
            except Exception:
                pass

        # This will init the retriever (lazy inside)
        from .intelligence import get_retriever  # noqa: F401
        _state["intelligence_loaded"] = True
        _set_phase("INTELLIGENCE_READY", events)


def ensure_intelligence_loaded(events: Any = None) -> None:
    """Call this before using RAG / vector retrieval."""
    _load_intelligence(events)


def is_intelligence_loaded() -> bool:
    return bool(_state["intelligence_loaded"])


def get_status() -> dict[str, Any]:
    """Lightweight status for IPC get_status (never triggers heavy load)."""
    return {
        "phase": get_phase(),
        "engine_loaded": is_engine_loaded(),
        "embeddings_loaded": _state["embeddings_loaded"],
        "intelligence_loaded": _state["intelligence_loaded"],
        "core_ready": True,
        "embedding_ready": _state["embeddings_loaded"],
        "intelligence_ready": is_intelligence_loaded(),
        "fully_ready": is_engine_loaded() and is_intelligence_loaded(),
    }


def get_loaded_symbol(name: str) -> Any:
    """Retrieve a cached heavy symbol after ensure_engine_loaded() has run."""
    ensure_engine_loaded()
    if name not in _loaded:
        # Fallback direct import (should be rare)
        if name == "CanvasScene":
            from canvas import CanvasScene as _cs
            _loaded[name] = _cs
        # add more as needed
    return _loaded.get(name)
