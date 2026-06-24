"""Phase 4 — Critic & self-correction loop with Guardrail 4 enforcement."""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from matemium.paths import discover_root

from .debug import build_debug_payload, write_debug_log
from .guard import apply_guard_to_project
from .models import CriticResult, Phase, ProjectSession
from .sidecar_outcome import (
    PYTHON_MANIM_ERROR_MARKERS,
    SidecarIpcResult,
    compile_outcome_from_sidecar,
    contains_python_or_manim_error,
    format_compile_error,
    ipc_failure_result,
    merge_ipc_results,
)
from .stubs import CompileFn, PatchFn, default_visual_qc

MAX_CRITIC_RETRIES = 3
VISUAL_QC_FAILURE = "visual_qc_failed: layout/clipping/contrast issue detected"

SIDECAR_REL_PATH = Path("dist") / "matemium-sidecar"
DEFAULT_COMPILE_TIMEOUT = 300.0


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


def _decode_subprocess_stream(data: str | bytes | None) -> str:
    if not data:
        return ""
    if isinstance(data, bytes):
        return data.decode("utf-8", errors="replace")
    return data


def run_sidecar_ipc(
    requests: list[tuple[str, str, dict]],
    *,
    timeout: float = DEFAULT_COMPILE_TIMEOUT,
) -> SidecarIpcResult:
    """Spawn the PyInstaller sidecar and exchange NDJSON requests on stdin."""
    try:
        binary = sidecar_binary_path()
    except FileNotFoundError as exc:
        return ipc_failure_result(str(exc))

    stdin_payload = "\n".join(
        _ipc_request(req_id, command, params) for req_id, command, params in requests
    )
    stdin_payload = f"{stdin_payload}\n" if stdin_payload else ""

    try:
        proc = subprocess.run(
            [str(binary)],
            input=stdin_payload,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=_sidecar_env(),
            cwd=str(discover_root()),
        )
    except subprocess.TimeoutExpired as exc:
        stderr = _decode_subprocess_stream(exc.stderr)
        if stderr.strip():
            stderr = f"sidecar subprocess timed out after {timeout}s\n{stderr}"
        else:
            stderr = f"sidecar subprocess timed out after {timeout}s"
        return ipc_failure_result(stderr)
    except OSError as exc:
        return ipc_failure_result(f"sidecar spawn failed: {exc}")

    responses, _events = _parse_sidecar_stdout(proc.stdout)
    return SidecarIpcResult(
        responses=tuple(responses),
        stderr=proc.stderr or "",
        returncode=proc.returncode,
    )


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
    list_ipc = run_sidecar_ipc(
        [("list", "list_scenes", {"workspace": str(workspace)})],
        timeout=timeout,
    )
    scene_name = _resolve_scene_from_listing(list_ipc.responses, scene)

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

    compile_ipc = run_sidecar_ipc(compile_requests, timeout=timeout)
    merged = merge_ipc_results(list_ipc, compile_ipc)
    return compile_outcome_from_sidecar(merged)


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
        apply_guard_to_project(session)
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