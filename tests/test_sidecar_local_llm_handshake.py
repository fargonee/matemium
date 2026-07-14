"""Unit tests for the sidecar LLM configuration handshake over IPC."""

from __future__ import annotations

import os
from typing import Any
import pytest

from matemium.ipc.handlers import dispatch
from matemium.ipc.events import EventEmitter


@pytest.fixture
def clean_env() -> None:
    """Ensure environment variables are clean before and after tests."""
    vars_to_clean = ["MATEMIUM_USE_LOCAL_LLM", "MATEMIUM_LOCAL_LLM_MODEL_PATH"]
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
    assert "Sure, I can help you add text" in result["message"]["content"]
    assert result["code_edit"] is not None
    assert result["code_edit"]["search"] == "builder.add_heading(\"Intro\")"
    assert "Hello offline world" in result["code_edit"]["replace"]
    assert isinstance(result["model"], str) and len(result["model"]) > 0


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

