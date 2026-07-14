"""Unit tests for the Matemium MCP Server and its integrated agent tools."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch
import pytest

from matemium.mcp_server import list_tools, call_tool


@pytest.mark.anyio
async def test_mcp_list_tools() -> None:
    """Verify that list_tools returns all core tools including the new run_lifecycle tool."""
    tools = await list_tools()
    
    # Assert all necessary tool names are exposed
    tool_names = [t.name for t in tools]
    assert "view_file" in tool_names
    assert "edit_file" in tool_names
    assert "compile_manim" in tool_names
    assert "retrieve" in tool_names
    assert "run_lifecycle" in tool_names

    # Check run_lifecycle schema expectations
    lifecycle_tool = next(t for t in tools if t.name == "run_lifecycle")
    assert "user_prompt" in lifecycle_tool.inputSchema["required"]
    assert "mode" in lifecycle_tool.inputSchema["properties"]


@pytest.mark.anyio
@patch("matemium.agent.coordinator.run_lifecycle")
async def test_mcp_call_tool_run_lifecycle(mock_run_lifecycle: MagicMock) -> None:
    """Verify that call_tool successfully dispatches run_lifecycle requests to the coordinator."""
    # 1. Setup mock LifecycleResult output
    mock_result = MagicMock()
    mock_result.post_production.total_duration = 12.5
    mock_result.blueprint.segments = [1, 2, 3]
    mock_result.token_ledger.total_credits_spent.return_value = 150
    mock_run_lifecycle.return_value = mock_result

    # 2. Invoke the tool
    arguments = {
        "user_prompt": "Animate a revolving helix.",
        "mode": "mute",
        "model_tier": "standard",
        "account_tier": "basic",
    }
    
    results = await call_tool("run_lifecycle", arguments)
    
    assert len(results) == 1
    assert results[0].type == "text"
    
    # Parse output JSON payload
    data = json.loads(results[0].text)
    assert data["ok"] is True
    assert data["duration"] == 12.5
    assert data["segments_count"] == 3
    assert data["tokens_spent"] == 150

    # Ensure coordinator was called with parsed enums
    mock_run_lifecycle.assert_called_once()
    passed_args, passed_kwargs = mock_run_lifecycle.call_args
    assert passed_kwargs["user_prompt"] == "Animate a revolving helix."
    assert passed_kwargs["mode"].value == "mute"
    assert passed_kwargs["model_tier"].value == "standard"
    assert passed_kwargs["account_tier"].value == "basic"
