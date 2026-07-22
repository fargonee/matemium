"""Unit tests for the Matemium MCP Server and its integrated agent tools."""

from __future__ import annotations

import json
import pytest

from matemium.mcp_server import list_tools, call_tool


@pytest.mark.anyio
async def test_mcp_list_tools() -> None:
    """The MCP surface exposes gated lifecycle helpers, not the legacy bypass."""
    tools = await list_tools()
    
    # Assert all necessary tool names are exposed
    tool_names = [t.name for t in tools]
    assert "view_file" in tool_names
    assert "edit_file" in tool_names
    assert "compile_manim" in tool_names
    assert "retrieve" in tool_names
    assert "create_tape_content" in tool_names
    assert "lifecycle_status" in tool_names
    assert "run_lifecycle" not in tool_names

    tape_tool = next(t for t in tools if t.name == "create_tape_content")
    assert tape_tool.inputSchema["required"] == ["slug", "title"]


@pytest.mark.anyio
async def test_mcp_lifecycle_status_and_tape_creation(tmp_path, monkeypatch) -> None:
    """MCP can inspect the gate and create bounded additional tape files."""
    brief = tmp_path / "brief"
    (brief / "tapes").mkdir(parents=True)
    (brief / "passport.json").write_text(
        json.dumps({"production_path": "custom_audio", "readiness": {"status": "ready", "missing_fields": []}}),
        encoding="utf-8",
    )
    (brief / "roadmap.json").write_text(
        json.dumps({
            "production_path": "custom_audio",
            "current_phase": "tape_content",
            "phases": [{"id": "tape_content", "title": "Tape content", "status": "in_progress"}],
            "invalidated_phases": [],
            "blockers": [],
        }),
        encoding="utf-8",
    )
    monkeypatch.setenv("MATEMIUM_ROOT", str(tmp_path))

    status = await call_tool("lifecycle_status", {})
    payload = json.loads(status[0].text)
    assert payload["production_path"] == "custom_audio"
    assert payload["current_phase"]["id"] == "tape_content"

    created = await call_tool("create_tape_content", {"slug": "comparison", "title": "Comparison"})
    assert json.loads(created[0].text)["ok"] is True
    assert (brief / "tapes" / "comparison.md").is_file()

    escaped = await call_tool("create_tape_content", {"slug": "../escape", "title": "Escape"})
    assert escaped[0].text.startswith("ERROR:")
