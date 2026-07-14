"""Unit tests for the PydanticAI-style Type-Safe Agent Bridge and GBNF grammars."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch
import pytest
from pydantic import BaseModel

from matemium.agent.grammars import AIDER_DIFF_GBNF, SIMPLE_JSON_GBNF
from matemium.agent.pydantic_ai_bridge import PydanticAIAgent, RunResult


class ThemeModel(BaseModel):
    """Pydantic model used to verify structured agent schema parsing and validation."""
    name: str
    contrast: float
    dark_mode: bool


def test_gbnf_grammar_presence() -> None:
    """Verify that both Aider diff and simple JSON GBNF grammars are properly declared."""
    assert "SEARCH" in AIDER_DIFF_GBNF
    assert "REPLACE" in AIDER_DIFF_GBNF
    assert "pair" in SIMPLE_JSON_GBNF
    assert "string" in SIMPLE_JSON_GBNF


@patch("matemium.agent.local_runner.LocalInferenceRunner.generate")
def test_pydantic_ai_bridge_fallback(mock_generate: MagicMock) -> None:
    """Verify that PydanticAIAgent fallback parser extracts, parses, and validates json responses."""
    # Mock GGUF response returning correct schema-conforming JSON
    mock_response = """
```json
{
  "name": "Neon Cyan",
  "contrast": 0.88,
  "dark_mode": true
}
```
"""
    mock_generate.return_value = mock_response

    # Initialize the bridge agent
    agent = PydanticAIAgent(
        model_name="local:qwen-coder-7b",
        result_type=ThemeModel,
        system_prompt="Create a high-contrast educational color palette.",
    )

    # Execute the agent
    result = agent.run_sync("Give me a cool dark math background theme.")

    # Assert outputs
    assert isinstance(result, RunResult)
    assert isinstance(result.data, ThemeModel)
    assert result.data.name == "Neon Cyan"
    assert result.data.contrast == 0.88
    assert result.data.dark_mode is True

    # Assert model was called with the Pydantic schema details
    mock_generate.assert_called_once()
    system_prompt_arg = mock_generate.call_args[0][0]
    assert "dark_mode" in system_prompt_arg
    assert "contrast" in system_prompt_arg
    # Verify that simple JSON grammar was passed to local_runner
    passed_kwargs = mock_generate.call_args[1]
    assert passed_kwargs.get("grammar") == SIMPLE_JSON_GBNF


@patch("matemium.agent.local_runner.LocalInferenceRunner.generate")
def test_pydantic_ai_bridge_validation_failure(mock_generate: MagicMock) -> None:
    """Verify that PydanticAIAgent raises ValueError on malformed or schema-violating response payloads."""
    # Mock a corrupt/invalid GGUF output
    mock_generate.return_value = '{"name": "Broken", "contrast": "invalid_float", "dark_mode": true}'

    agent = PydanticAIAgent(
        model_name="local:qwen-coder-7b",
        result_type=ThemeModel,
        system_prompt="Irrelevant",
    )

    with pytest.raises(ValueError) as exc_info:
        agent.run_sync("Request")

    assert "Fallback Validation Failed" in str(exc_info.value)
