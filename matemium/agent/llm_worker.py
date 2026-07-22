"""Crash-isolated llama.cpp worker used by the desktop sidecar.

llama.cpp is native code: a SIGSEGV cannot be caught by Python. Keeping model
evaluation in a child process prevents one bad model/backend combination from
terminating the desktop sidecar.
"""

from __future__ import annotations

import gc
import json
import os
import subprocess
import sys
import threading
import uuid
from pathlib import Path
from typing import Any, TextIO


_WORKER_LOCK = threading.Lock()
_WORKER_PROCESS: subprocess.Popen[str] | None = None
_WORKER_KEY: tuple[str, int] | None = None


def _worker_command() -> list[str]:
    if getattr(sys, "frozen", False):
        return [sys.executable, "--llm-worker"]
    return [sys.executable, "-u", "-m", "matemium.sidecar", "--llm-worker"]


def _start_worker(model_path: Path, context_window: int) -> subprocess.Popen[str]:
    global _WORKER_PROCESS, _WORKER_KEY
    key = (str(model_path.resolve()), context_window)
    if _WORKER_PROCESS is not None and _WORKER_PROCESS.poll() is None and _WORKER_KEY == key:
        return _WORKER_PROCESS
    shutdown_worker()
    env = os.environ.copy()
    process = subprocess.Popen(
        _worker_command(),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        bufsize=1,
        env=env,
    )
    _WORKER_PROCESS = process
    _WORKER_KEY = key
    return process


def shutdown_worker() -> None:
    """Stop and forget the current native model worker, if any."""
    global _WORKER_PROCESS, _WORKER_KEY
    process = _WORKER_PROCESS
    _WORKER_PROCESS = None
    _WORKER_KEY = None
    if process is None or process.poll() is not None:
        return
    try:
        if process.stdin is not None:
            process.stdin.write('{"command":"shutdown"}\n')
            process.stdin.flush()
        process.wait(timeout=3)
    except Exception:
        process.terminate()
        try:
            process.wait(timeout=2)
        except Exception:
            process.kill()


def generate_in_worker(
    *,
    model_path: Path,
    context_window: int,
    messages: list[dict[str, str]],
    grammar: str | None = None,
) -> str:
    """Generate one response, converting worker death into a Python error."""
    with _WORKER_LOCK:
        process = _start_worker(model_path, context_window)
        request_id = str(uuid.uuid4())
        request = {
            "id": request_id,
            "command": "generate",
            "model_path": str(model_path.resolve()),
            "context_window": context_window,
            "messages": messages,
            "grammar": grammar,
        }
        try:
            if process.stdin is None or process.stdout is None:
                raise RuntimeError("Local model worker pipes are unavailable.")
            process.stdin.write(json.dumps(request, ensure_ascii=False) + "\n")
            process.stdin.flush()
            line = process.stdout.readline()
        except (BrokenPipeError, OSError) as exc:
            line = ""
            pipe_error: Exception | None = exc
        else:
            pipe_error = None
        if not line:
            exit_code = process.poll()
            shutdown_worker()
            detail = f"exit code {exit_code}" if exit_code is not None else "closed IPC"
            raise RuntimeError(
                "The isolated local model worker terminated unexpectedly "
                f"({detail}). The desktop sidecar is still running. "
                "Try the 3B model or cloud transport; the local llama.cpp backend "
                "could not safely evaluate this model."
            ) from pipe_error
        response = json.loads(line)
        if response.get("id") != request_id:
            raise RuntimeError("Local model worker returned a mismatched response.")
        if not response.get("ok"):
            raise RuntimeError(str(response.get("error") or "Local model generation failed."))
        return str(response.get("content") or "")


def _prompt_from_messages(messages: list[dict[str, str]]) -> str:
    return "".join(
        f"<|im_start|>{message.get('role', 'user')}\n"
        f"{message.get('content', '')}<|im_end|>\n"
        for message in messages
    ) + "<|im_start|>assistant\n"


def worker_main(stdin: TextIO = sys.stdin, stdout: TextIO = sys.stdout) -> int:
    """Run the private NDJSON worker protocol."""
    model: Any = None
    loaded_key: tuple[str, int] | None = None
    for raw_line in stdin:
        try:
            request = json.loads(raw_line)
            if request.get("command") == "shutdown":
                return 0
            request_id = str(request.get("id") or "")
            model_path = str(request["model_path"])
            context_window = int(request["context_window"])
            key = (model_path, context_window)
            if model is None or loaded_key != key:
                model = None
                gc.collect()
                from llama_cpp import Llama

                # Conservative CPU settings matter on memory-constrained
                # machines and avoid large parallel prompt-evaluation spikes.
                cpu_threads = max(1, min(6, (os.cpu_count() or 2) // 2))
                model = Llama(
                    model_path=model_path,
                    n_ctx=context_window,
                    n_gpu_layers=0,
                    n_batch=128,
                    n_ubatch=128,
                    n_threads=cpu_threads,
                    n_threads_batch=cpu_threads,
                    offload_kqv=False,
                    use_mmap=True,
                    use_mlock=False,
                    verbose=False,
                )
                loaded_key = key
            grammar_text = request.get("grammar")
            grammar = None
            if grammar_text:
                from llama_cpp import LlamaGrammar

                grammar = LlamaGrammar.from_string(str(grammar_text))
            output = model(
                _prompt_from_messages(list(request.get("messages") or [])),
                max_tokens=2048,
                temperature=0.1,
                stop=["<|im_end|>", "<|im_start|>"],
                echo=False,
                grammar=grammar,
            )
            response = {
                "id": request_id,
                "ok": True,
                "content": str(output["choices"][0]["text"]),
            }
        except Exception as exc:
            response = {
                "id": str(locals().get("request_id", "")),
                "ok": False,
                "error": f"{type(exc).__name__}: {exc}",
            }
        stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
        stdout.flush()
    return 0
