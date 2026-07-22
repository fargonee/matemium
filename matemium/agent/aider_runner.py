"""Aider-backed workspace agent runner.

This module intentionally shells out to the ``aider`` CLI instead of importing
its internals. The CLI is the stable integration boundary and lets Aider own the
model/tool loop while Matemium keeps workspace routing, settings, and UI state.
"""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys
import time
from typing import Mapping, Sequence
import urllib.error
import urllib.request


class AiderUnavailableError(RuntimeError):
    """Raised when the Aider CLI cannot be used on this machine."""


AIDER_VERSION = "0.86.2"
AIDER_PYTHON = "3.12"
LOCAL_AIDER_MODEL = "openai/matemium-local"
_LOCAL_PROVIDER_PROCESS: subprocess.Popen[str] | None = None
_LOCAL_PROVIDER_BASE_URL: str | None = None


@dataclass(frozen=True)
class AiderRunResult:
    output: str
    model: str
    files: tuple[str, ...]
    trace: tuple[dict[str, object], ...] = ()


class AiderAgentRunner:
    """Runs a single Aider task against a Matemium project workspace."""

    def __init__(
        self,
        *,
        executable: str | None = None,
        env: Mapping[str, str] | None = None,
        timeout_seconds: float = 600.0,
    ) -> None:
        self.executable = executable or os.environ.get("MATEMIUM_AIDER_BIN")
        self.env = dict(os.environ)
        self.env.update(env or {})
        self.timeout_seconds = timeout_seconds

    def prepare_runtime(self) -> str:
        """Ensure the managed Aider executable exists and return its path."""
        return self._resolve_command()[0]

    def run(
        self,
        *,
        workspace: str | Path,
        prompt: str,
        model: str | None = None,
        provider: str | None = None,
        use_local_model: bool = False,
        extra_context: Sequence[str] = (),
    ) -> AiderRunResult:
        workspace_path = Path(workspace).resolve()
        if not workspace_path.is_dir():
            raise FileNotFoundError(f"Aider workspace does not exist: {workspace_path}")

        target_files = self._target_files(workspace_path)
        env = dict(self.env)
        env.setdefault("AIDER_ANALYTICS", "false")
        env.setdefault("AIDER_CHECK_UPDATE", "false")
        if use_local_model:
            base_url = self._ensure_local_model_server_available(env)
            env["OPENAI_API_BASE"] = f"{base_url}/v1"
            env["OPENAI_BASE_URL"] = f"{base_url}/v1"
            env.setdefault("OPENAI_API_KEY", "matemium-local")
            resolved_model = LOCAL_AIDER_MODEL
        else:
            resolved_model = self._resolve_model(
                model=model,
                provider=provider,
                use_local_model=False,
            )

        task_prompt = self._compose_prompt(prompt, extra_context)
        cmd = [
            *self._resolve_command(),
            "--yes-always",
            "--no-auto-commits",
            "--no-git",
            "--no-show-model-warnings",
            "--no-show-release-notes",
            "--no-pretty",
            "--no-stream",
            "--no-notifications",
            "--model",
            resolved_model,
            "--message",
            task_prompt,
            *target_files,
        ]

        completed = subprocess.run(
            cmd,
            cwd=workspace_path,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=self.timeout_seconds,
            check=False,
        )
        output = (completed.stdout or "").strip()
        if completed.returncode != 0:
            raise RuntimeError(f"Aider failed with exit code {completed.returncode}:\n{output}")
        trace = self._trace_from_output(output, target_files)
        summary = self._summary_from_trace(trace, target_files)
        return AiderRunResult(
            output=summary,
            model=resolved_model,
            files=tuple(target_files),
            trace=tuple(trace),
        )

    def _resolve_command(self) -> list[str]:
        explicit = (self.executable or "").strip()
        if explicit:
            path = Path(explicit)
            if path.is_file():
                return [str(path)]
            executable_path = shutil.which(explicit)
            if executable_path:
                return [executable_path]
            raise AiderUnavailableError(
                f"Configured Aider executable was not found: {explicit}"
            )

        managed = self._managed_aider_executable()
        if managed:
            return [str(managed)]

        executable_path = shutil.which("aider")
        if executable_path:
            return [executable_path]

        raise AiderUnavailableError(
            "Aider runtime could not be provisioned automatically. The app needs "
            "a bundled uv executable or MATEMIUM_UV_BIN/MATEMIUM_AIDER_BIN set by "
            "the launcher."
        )

    def _managed_aider_executable(self) -> Path | None:
        for runtime_dir in self._candidate_runtime_dirs():
            for relative in (
                Path("bin") / "aider",
                Path("Scripts") / "aider.exe",
                Path("Scripts") / "aider",
            ):
                candidate = runtime_dir / relative
                if candidate.is_file():
                    return candidate
            provisioned = self._provision_runtime(runtime_dir)
            if provisioned:
                return provisioned
        return None

    def _provision_runtime(self, runtime_dir: Path) -> Path | None:
        configured = self.env.get("MATEMIUM_AIDER_RUNTIME_DIR", "").strip()
        if not configured:
            return None

        uv = self._resolve_uv()
        if uv is None:
            return None

        runtime_dir.mkdir(parents=True, exist_ok=True)
        cache_dir = runtime_dir.parent / "uv-cache"
        tool_env = dict(self.env)
        tool_env.setdefault("UV_CACHE_DIR", str(cache_dir))
        tool_env.setdefault("UV_PYTHON_INSTALL_DIR", str(runtime_dir.parent / "uv-python"))
        tool_env.setdefault("UV_NO_PROGRESS", "1")

        self._run_provision_command(
            [
                uv,
                "venv",
                "--python",
                self.env.get("MATEMIUM_AIDER_PYTHON", AIDER_PYTHON),
                str(runtime_dir),
            ],
            tool_env,
        )
        python = runtime_dir / "bin" / "python"
        if not python.is_file():
            python = runtime_dir / "Scripts" / "python.exe"
        if not python.is_file():
            raise AiderUnavailableError(
                f"uv created {runtime_dir}, but no Python executable was found."
            )

        version = self.env.get("MATEMIUM_AIDER_VERSION", AIDER_VERSION)
        self._run_provision_command(
            [uv, "pip", "install", "--python", str(python), f"aider-chat=={version}"],
            tool_env,
        )

        for relative in (
            Path("bin") / "aider",
            Path("Scripts") / "aider.exe",
            Path("Scripts") / "aider",
        ):
            candidate = runtime_dir / relative
            if candidate.is_file():
                return candidate
        raise AiderUnavailableError(
            f"Aider installation completed but no executable was found in {runtime_dir}."
        )

    def _resolve_uv(self) -> str | None:
        explicit = self.env.get("MATEMIUM_UV_BIN", "").strip()
        if explicit:
            path = Path(explicit)
            if path.is_file():
                return str(path)
            resolved = shutil.which(explicit)
            if resolved:
                return resolved
            raise AiderUnavailableError(f"Configured uv executable was not found: {explicit}")

        for name in ("uv",):
            resolved = shutil.which(name)
            if resolved:
                return resolved

        home_uv = Path.home() / ".local" / "bin" / "uv"
        if home_uv.is_file():
            return str(home_uv)
        return None

    def _run_provision_command(self, cmd: list[str], env: Mapping[str, str]) -> None:
        completed = subprocess.run(
            cmd,
            env=dict(env),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=self.timeout_seconds,
            check=False,
        )
        if completed.returncode != 0:
            output = (completed.stdout or "").strip()
            raise AiderUnavailableError(
                f"Failed to provision Aider runtime with uv: {' '.join(cmd)}\n{output}"
            )

    def _candidate_runtime_dirs(self) -> list[Path]:
        candidates: list[Path] = []
        configured = self.env.get("MATEMIUM_AIDER_RUNTIME_DIR", "").strip()
        if configured:
            candidates.append(Path(configured).expanduser())

        env_root = self.env.get("MATEMIUM_ROOT", "").strip()
        if env_root:
            candidates.append(Path(env_root).expanduser() / "bin" / "aider-runtime")

        try:
            from ..paths import ROOT

            candidates.append(ROOT / ".aider-runtime")
            candidates.append(ROOT / "bin" / "aider-runtime")
        except Exception:
            pass

        cwd = Path.cwd()
        candidates.append(cwd / ".aider-runtime")
        candidates.append(cwd / "bin" / "aider-runtime")

        deduped: list[Path] = []
        seen: set[Path] = set()
        for candidate in candidates:
            resolved = candidate.resolve()
            if resolved not in seen:
                seen.add(resolved)
                deduped.append(resolved)
        return deduped

    def _target_files(self, workspace: Path) -> list[str]:
        files = []
        for name in (
            "scenes.py",
            "helpers.py",
            "brief/passport.json",
            "brief/description.md",
            "brief/tape.md",
            "brief/roadmap.json",
            "brief/narration.md",
        ):
            if (workspace / name).is_file():
                files.append(name)
        if not files:
            raise FileNotFoundError(
                f"Aider workspace must contain approved project files: {workspace}"
            )
        return files

    def _resolve_model(
        self,
        *,
        model: str | None,
        provider: str | None,
        use_local_model: bool,
    ) -> str:
        override = self.env.get("MATEMIUM_AIDER_MODEL", "").strip()
        if override:
            return override

        selected = (model or "").strip()
        provider_name = (provider or "").strip().lower()
        if use_local_model:
            return LOCAL_AIDER_MODEL

        if not selected:
            selected = "gpt-4o-mini"
        if "/" in selected:
            return selected
        if provider_name in {"anthropic", "openrouter", "gemini", "groq", "deepseek", "xai"}:
            return f"{provider_name}/{selected}"
        return selected

    def _ensure_local_model_server_available(self, env: Mapping[str, str]) -> str:
        return self._start_local_provider(env)

    def _start_local_provider(self, env: Mapping[str, str]) -> str:
        global _LOCAL_PROVIDER_BASE_URL, _LOCAL_PROVIDER_PROCESS
        if _LOCAL_PROVIDER_BASE_URL and self._probe_local_provider(_LOCAL_PROVIDER_BASE_URL):
            return _LOCAL_PROVIDER_BASE_URL

        if _LOCAL_PROVIDER_PROCESS is not None and _LOCAL_PROVIDER_PROCESS.poll() is None:
            _LOCAL_PROVIDER_PROCESS.terminate()
        port = self._free_local_port()
        base_url = f"http://127.0.0.1:{port}"
        command = self._local_provider_command(port)
        process = subprocess.Popen(
            command,
            env=dict(env),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        _LOCAL_PROVIDER_PROCESS = process
        _LOCAL_PROVIDER_BASE_URL = base_url

        deadline = time.time() + 10.0
        while time.time() < deadline:
            if process.poll() is not None:
                raise AiderUnavailableError(
                    "The Matemium local model provider exited before becoming ready."
                )
            if self._probe_local_provider(base_url):
                return base_url
            time.sleep(0.1)
        raise AiderUnavailableError(
            "The Matemium local model provider did not become ready in time."
        )

    def _probe_local_provider(self, base_url: str) -> bool:
        try:
            req = urllib.request.Request(f"{base_url}/v1/models", method="GET")
            with urllib.request.urlopen(req, timeout=0.5) as resp:
                return resp.status == 200
        except Exception:
            return False

    def _local_provider_command(self, port: int) -> list[str]:
        if getattr(sys, "frozen", False):
            return [sys.executable, "--local-openai-server", "--host", "127.0.0.1", "--port", str(port)]
        return [
            sys.executable,
            "-u",
            "-m",
            "matemium.sidecar",
            "--local-openai-server",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ]

    def _free_local_port(self) -> int:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", 0))
            return int(sock.getsockname()[1])

    def _compose_prompt(self, prompt: str, extra_context: Sequence[str]) -> str:
        instructions = (
            "You are editing a Matemium animation workspace. Keep changes scoped to "
            "scenes.py, helpers.py, and brief/. Use the existing CanvasBuilder and CanvasScene "
            "style. After editing, summarize the changed files and any validation the "
            "user should run."
        )
        context = "\n\n".join(part.strip() for part in extra_context if part.strip())
        if context:
            return f"{instructions}\n\nAdditional context:\n{context}\n\nUser task:\n{prompt}"
        return f"{instructions}\n\nUser task:\n{prompt}"

    def _trace_from_output(
        self, output: str, target_files: Sequence[str]
    ) -> list[dict[str, object]]:
        now_ms = int(time.time() * 1000)
        events: list[dict[str, object]] = [
            {
                "type": "model_request_started",
                "summary": "Started Aider workspace agent.",
                "details": {"files": list(target_files)},
                "sequence": 1,
                "timestamp_ms": now_ms,
            }
        ]
        added_files: list[str] = []
        edited_files: list[str] = []
        token_summary: str | None = None
        warnings: list[str] = []

        for raw_line in output.splitlines():
            line = self._clean_output_line(raw_line)
            if not line:
                continue
            added = re.match(r"Added\s+(.+?)\s+to the chat\.", line)
            if added:
                added_files.append(added.group(1))
                continue
            applied = re.match(r"Applied edit to\s+(.+)", line)
            if applied:
                edited_files.append(applied.group(1))
                continue
            if line.startswith("Tokens:"):
                token_summary = line
                continue
            if line.startswith("Warning") or "summarization failed" in line.lower():
                warnings.append(line)

        sequence = len(events) + 1
        if added_files:
            events.append({
                "type": "context_referenced",
                "summary": f"Loaded {len(added_files)} workspace file{'s' if len(added_files) != 1 else ''}.",
                "details": {"files": added_files},
                "sequence": sequence,
                "timestamp_ms": now_ms,
            })
            sequence += 1
        if edited_files:
            events.append({
                "type": "action_completed",
                "summary": f"Applied edits to {', '.join(edited_files)}.",
                "details": {"tool": "aider_edit", "files": edited_files},
                "sequence": sequence,
                "timestamp_ms": now_ms,
            })
            sequence += 1
        if token_summary:
            events.append({
                "type": "model_request_completed",
                "summary": "Aider model request completed.",
                "details": {"usage": token_summary},
                "sequence": sequence,
                "timestamp_ms": now_ms,
            })
            sequence += 1
        for warning in warnings[:5]:
            events.append({
                "type": "agent_warning",
                "summary": "Aider reported a non-fatal warning.",
                "details": {"message": warning},
                "sequence": sequence,
                "timestamp_ms": now_ms,
            })
            sequence += 1
        events.append({
            "type": "terminal",
            "summary": "Aider finished the workspace task.",
            "details": {"outcome": "finished", "edited_files": edited_files},
            "sequence": sequence,
            "timestamp_ms": now_ms,
        })
        return events

    def _summary_from_trace(
        self, trace: Sequence[dict[str, object]], target_files: Sequence[str]
    ) -> str:
        edited: list[str] = []
        for event in trace:
            details = event.get("details")
            if isinstance(details, dict) and isinstance(details.get("edited_files"), list):
                edited = [str(item) for item in details["edited_files"]]
        if edited:
            return f"Done. Aider updated {', '.join(edited)}."
        return f"Aider finished. Checked {', '.join(target_files)}."

    def _clean_output_line(self, line: str) -> str:
        cleaned = re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", line).strip()
        cleaned = cleaned.strip("─ ")
        return cleaned
