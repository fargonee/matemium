"""Pure sidecar IPC outcome classification — no subprocess imports."""

from __future__ import annotations

import re
from dataclasses import dataclass

PYTHON_MANIM_ERROR_MARKERS: tuple[str, ...] = (
    "SyntaxError",
    "was never closed",
    "invalid syntax",
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


@dataclass(frozen=True)
class SidecarIpcResult:
    """Captured sidecar subprocess IPC outcome."""

    responses: tuple[dict, ...]
    stderr: str
    returncode: int


def ipc_failure_result(stderr: str, *, returncode: int = -1) -> SidecarIpcResult:
    """Build a failed IPC result without spawning a subprocess."""
    return SidecarIpcResult(responses=(), stderr=stderr, returncode=returncode)


def merge_ipc_results(*results: SidecarIpcResult) -> SidecarIpcResult:
    """Combine responses and stderr from sequential sidecar IPC rounds."""
    responses: list[dict] = []
    stderr_parts: list[str] = []
    returncode = 0
    for result in results:
        responses.extend(result.responses)
        if result.stderr.strip():
            stderr_parts.append(result.stderr.strip())
        if result.returncode != 0:
            returncode = result.returncode
    return SidecarIpcResult(
        responses=tuple(responses),
        stderr="\n".join(stderr_parts),
        returncode=returncode,
    )


def contains_python_or_manim_error(text: str) -> bool:
    """Detect Python or Manim failure signatures in stderr or error payloads."""
    if not text.strip():
        return False
    for marker in PYTHON_MANIM_ERROR_MARKERS:
        if marker in text:
            return True
    return bool(re.search(r"\bError\b", text))


def collect_error_fragments(responses: tuple[dict, ...] | list[dict], stderr: str) -> list[str]:
    """Gather every error fragment from stderr and IPC payloads."""
    lines: list[str] = []
    if stderr.strip():
        lines.append(stderr.strip())
    for resp in responses:
        if not resp.get("ok"):
            err = resp.get("error") or {}
            if isinstance(err, dict):
                traceback = err.get("traceback")
                message = err.get("message")
                if traceback:
                    lines.append(str(traceback))
                if message:
                    lines.append(str(message))
            elif err:
                lines.append(str(err))
        result = resp.get("result")
        if isinstance(result, dict) and result.get("ok") is False:
            for diag in result.get("errors") or []:
                if isinstance(diag, dict):
                    lines.append(str(diag.get("message", diag)))
                else:
                    lines.append(str(diag))
    return list(dict.fromkeys(line for line in lines if line.strip()))


def richest_error_text(fragments: list[str]) -> str:
    """Pick the most informative compile error for patch_fn feeding."""
    if not fragments:
        return ""
    for fragment in fragments:
        if "SyntaxError" in fragment and "^" in fragment:
            return fragment
    for fragment in fragments:
        if "SyntaxError" in fragment:
            return fragment
    for fragment in fragments:
        if "Traceback" in fragment:
            return fragment
    return max(fragments, key=len)


def format_compile_error(responses: tuple[dict, ...] | list[dict], stderr: str) -> str:
    """Flatten sidecar responses and stderr into one error string for patch_fn."""
    fragments = collect_error_fragments(responses, stderr)
    richest = richest_error_text(fragments)
    if richest:
        return richest
    return "\n".join(fragments) if fragments else ""


def ensure_error_text(error_text: str, result: SidecarIpcResult) -> str:
    """Guarantee a non-empty error string for patch_fn and debug payloads."""
    if error_text.strip():
        return error_text
    if result.stderr.strip():
        return result.stderr.strip()
    if result.returncode != 0:
        return f"sidecar exited with code {result.returncode}"
    if not result.responses:
        return "sidecar produced no responses"
    return "compilation failed"


def compile_outcome_from_sidecar(result: SidecarIpcResult) -> tuple[bool, str]:
    """Classify sidecar IPC as compile success or failure with error text."""
    error_text = format_compile_error(result.responses, result.stderr)

    if not result.responses:
        return False, ensure_error_text(error_text, result)

    for resp in result.responses:
        if not resp.get("ok"):
            return False, ensure_error_text(error_text, result)
        payload = resp.get("result")
        if isinstance(payload, dict) and payload.get("ok") is False:
            return False, ensure_error_text(error_text, result)

    if contains_python_or_manim_error(result.stderr):
        return False, ensure_error_text(error_text, result)
    if contains_python_or_manim_error(error_text):
        return False, ensure_error_text(error_text, result)

    if result.returncode != 0:
        return False, ensure_error_text(error_text, result)

    return True, ""