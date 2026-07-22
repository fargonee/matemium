"""Tests for the crash boundary around native llama.cpp inference."""

from __future__ import annotations

import io
from pathlib import Path

import pytest

from matemium.agent import llm_worker


def test_worker_prompt_preserves_message_roles() -> None:
    prompt = llm_worker._prompt_from_messages(
        [
            {"role": "system", "content": "Use tools."},
            {"role": "user", "content": "Inspect scenes.py"},
        ]
    )

    assert "<|im_start|>system\nUse tools.<|im_end|>" in prompt
    assert "<|im_start|>user\nInspect scenes.py<|im_end|>" in prompt
    assert prompt.endswith("<|im_start|>assistant\n")


def test_native_worker_crash_becomes_recoverable_python_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class CrashedProcess:
        stdin = io.StringIO()
        stdout = io.StringIO("")

        def poll(self) -> int:
            return -11

    process = CrashedProcess()
    monkeypatch.setattr(llm_worker, "_start_worker", lambda *_args: process)
    monkeypatch.setattr(llm_worker, "shutdown_worker", lambda: None)

    with pytest.raises(RuntimeError, match="desktop sidecar is still running"):
        llm_worker.generate_in_worker(
            model_path=Path("/models/qwen-7b.gguf"),
            context_window=18432,
            messages=[{"role": "user", "content": "Inspect scenes.py"}],
        )

    assert '"command": "generate"' in process.stdin.getvalue()
