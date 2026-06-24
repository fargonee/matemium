"""Phase 4 — Critic & self-correction loop with Guardrail 4 enforcement."""

from __future__ import annotations

import json
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from matemium.paths import discover_root

from .debug import build_debug_payload, write_debug_log
from .models import CriticResult, Phase, ProjectSession
from .stubs import CompileFn, PatchFn, default_visual_qc

MAX_CRITIC_RETRIES = 3
VISUAL_QC_FAILURE = "visual_qc_failed: layout/clipping/contrast issue detected"

SIDECAR_REL_PATH = Path("dist") / "matemium-sidecar"
DEFAULT_COMPILE_TIMEOUT = 300.0

PYTHON_MANIM_ERROR_MARKERS: tuple[str, ...] = (
    "SyntaxError",
    "IndentationError",
    "ImportError",
    "ModuleNotFoundError",
    "AttributeError",
    "has no attribute",
    "NameError",
    "TypeError",
    "Traceback",
    "Manim",
    "CHECK_FAILED",
    "RENDER_FAILED",
    "Exception",
)


class CoordinatorHaltError(RuntimeError):
    """Raised when the lifecycle must stop after terminal critic failure."""

    def __init__(self, message: str, debug_path: str | None = None):
        super().__init__(message)
        self.debug_path = debug_path


@dataclass(frozen=True)
class CriticHooks:
    compile_fn: CompileFn
    patch_fn: PatchFn
    visual_qc_fn: Callable[[], bool] = default_visual_qc


@dataclass(frozen=True)
class SidecarIpcResult:
    """Captured sidecar subprocess IPC outcome."""

    responses: tuple[dict, ...]
    stderr: str
    returncode: int


def sidecar_binary_path() -> Path:
    """Resolve the PyInstaller matemium-sidecar binary."""
    binary = discover_root() / SIDECAR_REL_PATH
    if not binary.is_file():
        raise FileNotFoundError(
            f"PyInstaller sidecar not found at {binary} — run ./desktop/scripts/build-sidecar.sh"
        )
    return binary


def sidecar_binary_available() -> bool:
    """Return True when the frozen sidecar binary is present."""
    try:
        sidecar_binary_path()
        return True
    except FileNotFoundError:
        return False


def _sidecar_env() -> dict[str, str]:
    env = os.environ.copy()
    env["MATEMIUM_ROOT"] = str(discover_root())
    return env


def _ipc_request(req_id: str, command: str, params: dict) -> str:
    return json.dumps(
        {"type": "request", "id": req_id, "command": command, "params": params},
        separators=(",", ":"),
    )


def _parse_sidecar_stdout(stdout: str) -> tuple[list[dict], list[dict]]:
    responses: list[dict] = []
    events: list[dict] = []
    for line in stdout.splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if payload.get("type") == "response":
            responses.append(payload)
        elif payload.get("type") == "event":
            events.append(payload)
    return responses, events


def run_sidecar_ipc(
    requests: list[tuple[str, str, dict]],
    *,
    timeout: float = DEFAULT_COMPILE_TIMEOUT,
) -> SidecarIpcResult:
    """Spawn the PyInstaller sidecar and exchange NDJSON requests on stdin."""
    binary = sidecar_binary_path()
    stdin_payload = "\n".join(_ipc_request(req_id, command, params) for req_id, command, params in requests)
    stdin_payload = f"{stdin_payload}\n" if stdin_payload else ""

    proc = subprocess.run(
        [str(binary)],
        input=stdin_payload,
        capture_output=True,
        text=True,
        timeout=timeout,
        env=_sidecar_env(),
        cwd=str(discover_root()),
    )
    responses, _events = _parse_sidecar_stdout(proc.stdout)
    return SidecarIpcResult(
        responses=tuple(responses),
        stderr=proc.stderr or "",
        returncode=proc.returncode,
    )


def contains_python_or_manim_error(text: str) -> bool:
    """Detect Python or Manim failure signatures in stderr or error payloads."""
    if not text.strip():
        return False
    for marker in PYTHON_MANIM_ERROR_MARKERS:
        if marker in text:
            return True
    return bool(re.search(r"\bError\b", text))


def format_compile_error(responses: tuple[dict, ...] | list[dict], stderr: str) -> str:
    """Flatten sidecar responses and stderr into one error string for patch_fn."""
    lines: list[str] = []
    if stderr.strip():
        lines.append(stderr.strip())
    for resp in responses:
        if not resp.get("ok"):
            err = resp.get("error") or {}
            message = err.get("message") if isinstance(err, dict) else str(err)
            if message:
                lines.append(str(message))
        result = resp.get("result")
        if isinstance(result, dict) and result.get("ok") is False:
            for diag in result.get("errors") or []:
                if isinstance(diag, dict):
                    lines.append(str(diag.get("message", diag)))
                else:
                    lines.append(str(diag))
    return "\n".join(lines) if lines else ""


def compile_outcome_from_sidecar(result: SidecarIpcResult) -> tuple[bool, str]:
    """Classify sidecar IPC as compile success or failure with error text."""
    error_text = format_compile_error(result.responses, result.stderr)
    if result.returncode != 0 and not error_text.strip():
        error_text = f"sidecar exited with code {result.returncode}"

    if not result.responses:
        return False, error_text or "sidecar produced no responses"

    for resp in result.responses:
        if not resp.get("ok"):
            return False, error_text
        payload = resp.get("result")
        if isinstance(payload, dict) and payload.get("ok") is False:
            return False, error_text

    if contains_python_or_manim_error(result.stderr):
        return False, error_text
    if contains_python_or_manim_error(error_text):
        return False, error_text

    return True, ""


def _resolve_scene_from_listing(
    responses: tuple[dict, ...],
    preferred: str | None,
) -> str | None:
    for resp in responses:
        result = resp.get("result")
        if isinstance(result, dict) and "scenes" in result:
            scenes = list(result.get("scenes") or [])
            if not scenes:
                return None
            if preferred and preferred in scenes:
                return preferred
            for candidate in ("AgentScene", "PortraitDemo", "MyScene", "MyVideo"):
                if candidate in scenes:
                    return candidate
            return scenes[0]
    return preferred


def compile_project_via_sidecar(
    workspace: Path | str,
    *,
    scene: str | None = None,
    include_render: bool = False,
    timeout: float = DEFAULT_COMPILE_TIMEOUT,
) -> tuple[bool, str]:
    """Compile a workspace scenes.py via the PyInstaller sidecar subprocess."""
    workspace = Path(workspace).resolve()
    requests: list[tuple[str, str, dict]] = [
        ("list", "list_scenes", {"workspace": str(workspace)}),
    ]
    ipc = run_sidecar_ipc(requests, timeout=timeout)
    scene_name = _resolve_scene_from_listing(ipc.responses, scene)

    compile_requests: list[tuple[str, str, dict]] = [
        (
            "check",
            "check_project",
            {"workspace": str(workspace), **({"scene": scene_name} if scene_name else {})},
        ),
    ]
    if include_render and scene_name:
        compile_requests.append(
            (
                "render",
                "render_project",
                {
                    "workspace": str(workspace),
                    "scene": scene_name,
                    "quality": "preview",
                    "output_dir": str(workspace / "renders"),
                },
            )
        )

    ipc = run_sidecar_ipc(compile_requests, timeout=timeout)
    return compile_outcome_from_sidecar(ipc)


def make_sidecar_compile_fn(
    project_dir: Path | str,
    *,
    scene: str | None = None,
    include_render: bool = False,
    timeout: float = DEFAULT_COMPILE_TIMEOUT,
) -> CompileFn:
    """Build a compile_fn closure bound to a project workspace."""

    def compile_fn() -> tuple[bool, str]:
        return compile_project_via_sidecar(
            project_dir,
            scene=scene,
            include_render=include_render,
            timeout=timeout,
        )

    return compile_fn


def run_critic_loop(session: ProjectSession, hooks: CriticHooks) -> CriticResult:
    """Compile + visual QC with capped self-correction (compile or visual failures)."""
    last_stderr = ""

    for attempt in range(1, MAX_CRITIC_RETRIES + 1):
        success, stderr = hooks.compile_fn()
        last_stderr = stderr
        if not success:
            if attempt < MAX_CRITIC_RETRIES:
                hooks.patch_fn(stderr)
                continue
            break

        visual_ok = hooks.visual_qc_fn()
        if visual_ok:
            return CriticResult(
                passed=True,
                attempts=attempt,
                stderr=stderr,
                visual_qc_passed=True,
            )

        last_stderr = VISUAL_QC_FAILURE
        if attempt < MAX_CRITIC_RETRIES:
            hooks.patch_fn(last_stderr)
            continue
        break

    script_excerpt = ""
    if session.director_output:
        script_excerpt = session.director_output.script[:500]

    payload = build_debug_payload(
        session,
        error=last_stderr or "compilation failed",
        error_trace=last_stderr,
        retry_count=MAX_CRITIC_RETRIES,
        script_excerpt=script_excerpt,
    )
    debug_path = write_debug_log(session, payload)
    session.halted = True
    session.halt_reason = last_stderr or "compilation failed"
    raise CoordinatorHaltError(
        f"Critic loop exhausted {MAX_CRITIC_RETRIES} attempts; debug log written.",
        debug_path=str(debug_path),
    )