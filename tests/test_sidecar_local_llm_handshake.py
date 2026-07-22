"""Unit tests for the sidecar LLM configuration handshake over IPC."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any
import pytest

from matemium.ipc.handlers import (
    _looks_like_workspace_evidence_request,
    _looks_like_workspace_edit_request,
    _looks_like_workspace_task_request,
    dispatch,
)
from matemium.ipc.events import EventEmitter


@pytest.fixture
def clean_env() -> None:
    """Ensure environment variables are clean before and after tests."""
    vars_to_clean = [
        "MATEMIUM_USE_LOCAL_LLM",
        "MATEMIUM_LOCAL_LLM_MODEL_PATH",
        "MATEMIUM_LOCAL_LLM_CONTEXT_SIZE",
    ]
    for v in vars_to_clean:
        if v in os.environ:
            del os.environ[v]
    yield
    for v in vars_to_clean:
        if v in os.environ:
            del os.environ[v]


def test_update_llm_config_handshake(clean_env: None) -> None:
    """Verify that dispatching the update_llm_config command configures env variables."""
    events = EventEmitter()
    
    # 1. Enable local LLM
    params: dict[str, Any] = {
        "use_local_llm": True,
        "model_path": "/home/user/models/qwen-3b.gguf"
    }
    
    result = dispatch("update_llm_config", params, events)
    
    assert result["ok"] is True
    assert "use_local_llm" in result["configured"]
    assert "model_path" in result["configured"]
    
    assert os.environ.get("MATEMIUM_USE_LOCAL_LLM") == "true"
    assert os.environ.get("MATEMIUM_LOCAL_LLM_MODEL_PATH") == "/home/user/models/qwen-3b.gguf"

    # 2. Disable local LLM
    params_disable: dict[str, Any] = {
        "use_local_llm": False,
        "model_path": "/home/user/models/qwen-3b.gguf"
    }

    result_disable = dispatch("update_llm_config", params_disable, events)

    assert result_disable["ok"] is True
    assert os.environ.get("MATEMIUM_USE_LOCAL_LLM") == "false"
    # Path is preserved or kept in env
    assert os.environ.get("MATEMIUM_LOCAL_LLM_MODEL_PATH") == "/home/user/models/qwen-3b.gguf"


def test_model_context_window_is_sized_for_memory(clean_env: None) -> None:
    from matemium.agent.local_runner import LocalInferenceRunner

    assert LocalInferenceRunner("qwen2.5-coder-3b-q4.gguf").context_window == 32768
    assert LocalInferenceRunner("qwen2.5-coder-7b-q4.gguf").context_window == 18432
    assert LocalInferenceRunner("llama-8b-q4.gguf").context_window == 18432

    os.environ["MATEMIUM_LOCAL_LLM_CONTEXT_SIZE"] = "12000"
    assert LocalInferenceRunner("qwen2.5-coder-7b-q4.gguf").context_window == 18432


def test_switching_model_unloads_cached_gguf(
    clean_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    import matemium.agent.local_runner as local_runner

    cached = object()
    monkeypatch.setattr(local_runner, "_LLAMA_CPP_MODEL", cached)
    monkeypatch.setattr(local_runner, "_LLAMA_CPP_MODEL_PATH", "/models/old.gguf")
    os.environ["MATEMIUM_LOCAL_LLM_MODEL_PATH"] = "/models/old.gguf"

    result = dispatch(
        "update_llm_config",
        {"use_local_llm": True, "model_path": "/models/new.gguf"},
        EventEmitter(),
    )

    assert result["ok"] is True
    assert local_runner._LLAMA_CPP_MODEL is None
    assert local_runner._LLAMA_CPP_MODEL_PATH is None
    assert os.environ["MATEMIUM_LOCAL_LLM_MODEL_PATH"] == "/models/new.gguf"


def test_local_chat_handler(clean_env: None, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify that dispatching 'local_chat' routes through LocalInferenceRunner and parses search/replace edits."""
    events = EventEmitter()

    # Mock is_ollama_running to return True so we can test the Ollama path without compiling llama-cpp-python in tests
    monkeypatch.setattr("matemium.agent.local_runner.LocalInferenceRunner.is_ollama_running", lambda self: True)
    
    # Mock Ollama generation response containing an aider-style Search/Replace block
    mock_response = (
        "Sure, I can help you add text to your scene!\n"
        "<<<<<<< SEARCH\n"
        "builder.add_heading(\"Intro\")\n"
        "=======\n"
        "builder.add_heading(\"Intro\")\n"
        "builder.add_text(\"Hello offline world\")\n"
        ">>>>>>> REPLACE"
    )
    monkeypatch.setattr(
        "matemium.agent.local_runner.LocalInferenceRunner._generate_via_ollama_messages",
        lambda self, messages: mock_response
    )

    params: dict[str, Any] = {
        "messages": [
            {"role": "user", "content": "How do I add text to the intro?"}
        ],
        "scenes_excerpt": "builder.add_heading(\"Intro\")\n"
    }

    result = dispatch("local_chat", params, events)

    assert "id" in result
    assert result["message"]["role"] == "assistant"
    assert "validated, bounded edit" in result["message"]["content"]
    assert result["code_edit"] is not None
    assert result["code_edit"]["search"] == "builder.add_heading(\"Intro\")"
    assert "Hello offline world" in result["code_edit"]["replace"]
    assert isinstance(result["model"], str) and len(result["model"]) > 0


def test_workspace_edit_request_detection_is_generic() -> None:
    assert _looks_like_workspace_edit_request("rename this class to NewName")
    assert _looks_like_workspace_edit_request("revert that change back")
    assert _looks_like_workspace_edit_request("update the animation timing")
    assert not _looks_like_workspace_edit_request("what files are in this project?")


def test_workspace_evidence_request_detection_is_generic() -> None:
    assert _looks_like_workspace_evidence_request("what animation does this scene code generate?")
    assert _looks_like_workspace_evidence_request("explain this scene")
    assert not _looks_like_workspace_evidence_request("hello")


def test_workspace_task_request_detection_routes_general_chat_away_from_tools() -> None:
    assert _looks_like_workspace_task_request("rename this class to NewName")
    assert _looks_like_workspace_task_request("what animation does this scene code generate?")
    assert _looks_like_workspace_task_request("compile scenes.py")
    assert not _looks_like_workspace_task_request("who are you")


def test_plain_local_chat_does_not_send_workspace_context(
    clean_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    events = EventEmitter()
    monkeypatch.setattr("matemium.agent.local_runner.LocalInferenceRunner.is_ollama_running", lambda self: True)

    captured_messages: list[dict[str, str]] = []

    def mock_generate(self, messages):
        nonlocal captured_messages
        captured_messages = messages
        return "Hello."

    monkeypatch.setattr(
        "matemium.agent.local_runner.LocalInferenceRunner._generate_via_ollama_messages",
        mock_generate,
    )

    result = dispatch(
        "local_chat",
        {
            "messages": [{"role": "user", "content": "hello"}],
            "scenes_excerpt": "class LargeScene:\n    pass\n",
        },
        events,
    )

    assert result["message"]["content"] == "Hello."
    assert len(captured_messages) == 2
    assert "Current scenes.py" not in captured_messages[0]["content"]
    assert "LargeScene" not in "\n".join(message["content"] for message in captured_messages)


def test_local_chat_handler_with_references(clean_env: None, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify that 'local_chat' correctly parses references out of scenes_excerpt."""
    events = EventEmitter()

    monkeypatch.setattr("matemium.agent.local_runner.LocalInferenceRunner.is_ollama_running", lambda self: True)

    captured_messages = []
    def mock_generate(self, messages):
        nonlocal captured_messages
        captured_messages = messages
        return "Stub response"

    monkeypatch.setattr(
        "matemium.agent.local_runner.LocalInferenceRunner._generate_via_ollama_messages",
        mock_generate
    )

    params: dict[str, Any] = {
        "messages": [
            {"role": "user", "content": "Refer to the formula."}
        ],
        "scenes_excerpt": "--- REFERENCE FILE: references/formula.txt ---\nE = mc^2\n---------------------------------------\n\n// --- workspace context below ---\nbuilder.add_heading(\"Physics\")"
    }

    dispatch("local_chat", params, events)

    assert len(captured_messages) == 4
    assert captured_messages[0]["role"] == "system"
    assert captured_messages[1]["role"] == "system"
    assert "Reference documents" in captured_messages[1]["content"]
    assert "E = mc^2" in captured_messages[1]["content"]
    assert captured_messages[2]["role"] == "system"
    assert "Current scenes.py" in captured_messages[2]["content"]
    assert "builder.add_heading" in captured_messages[2]["content"]
    assert captured_messages[3]["role"] == "user"


def test_autonomous_local_chat_routes_workspace_task_to_aider(
    clean_env: None,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from matemium.agent.aider_runner import AiderRunResult

    events = EventEmitter()
    (tmp_path / "scenes.py").write_text("class Demo:\n    pass\n", encoding="utf-8")
    captured: dict[str, Any] = {}

    def fake_run(self, **kwargs):
        captured.update(kwargs)
        return AiderRunResult(
            output="Changed scenes.py",
            model="openai/matemium-local",
            files=("scenes.py",),
            trace=(
                {
                    "type": "action_completed",
                    "summary": "Applied edits to scenes.py.",
                    "details": {"tool": "aider_edit", "files": ["scenes.py"]},
                },
            ),
        )

    monkeypatch.setattr("matemium.agent.aider_runner.AiderAgentRunner.run", fake_run)
    monkeypatch.setattr(
        "matemium.agent.local_runner.LocalInferenceRunner.is_ollama_running",
        lambda self: True,
    )

    result = dispatch(
        "local_chat",
        {
            "messages": [{"role": "user", "content": "add a heading to the scene"}],
            "scenes_excerpt": "class Demo:\n    pass\n",
            "workspace": str(tmp_path),
            "model": "llm-qwen-coder-3b-q4",
            "use_local_llm": True,
            "use_autonomous_agent": True,
        },
        events,
    )

    assert result["message"]["content"] == "Changed scenes.py"
    assert result["agent_trace"][0]["type"] == "action_completed"
    assert result["code_edit"] is None
    assert result["agent_runtime_version"] == "aider-v1"
    assert result["billing_mode"] == "local"
    assert captured["workspace"] == tmp_path.resolve()
    assert captured["use_local_model"] is True
    assert captured["model"] == "llm-qwen-coder-3b-q4"


def test_autonomous_local_chat_hides_aider_provider_errors(
    clean_env: None,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events = EventEmitter()
    (tmp_path / "scenes.py").write_text("class Demo:\n    pass\n", encoding="utf-8")

    def fail(self, **kwargs):
        from matemium.agent.aider_runner import AiderUnavailableError

        raise AiderUnavailableError("Provider connection refused")

    monkeypatch.setattr("matemium.agent.aider_runner.AiderAgentRunner.run", fail)

    result = dispatch(
        "local_chat",
        {
            "messages": [{"role": "user", "content": "rename this class"}],
            "scenes_excerpt": "class Demo:\n    pass\n",
            "workspace": str(tmp_path),
            "model": "llm-qwen-coder-3b-q4",
            "use_local_llm": True,
            "use_autonomous_agent": True,
        },
        events,
    )

    assert "Local autonomous editing is not ready" in result["message"]["content"]
    assert "Provider connection refused" not in result["message"]["content"]
    assert result["agent_trace"][0]["details"]["error"] == "Provider connection refused"


def test_prepare_agent_runtime_reports_readiness(
    clean_env: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "matemium.agent.aider_runner.AiderAgentRunner.prepare_runtime",
        lambda self: "/managed/aider-runtime/bin/aider",
    )

    result = dispatch("prepare_agent_runtime", {}, EventEmitter())

    assert result["ok"] is True
    assert result["runtime"] == "aider-v1"
    assert result["executable"] == "/managed/aider-runtime/bin/aider"


def test_prepare_agent_runtime_returns_structured_failure(
    clean_env: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail(self):
        raise RuntimeError("uv unavailable")

    monkeypatch.setattr(
        "matemium.agent.aider_runner.AiderAgentRunner.prepare_runtime",
        fail,
    )

    result = dispatch("prepare_agent_runtime", {}, EventEmitter())

    assert result["ok"] is False
    assert result["runtime"] == "aider-v1"
    assert "uv unavailable" in result["error"]
