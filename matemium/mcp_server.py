"""Lightweight MCP server for the Matemium sidecar.

Exposes the agent tools (view_file, edit_file, compile_manim) and RAG resources
as local MCP tools/resources. This is the grounded source of truth for the
user's workspace (per PRODUCT-ARCHITECTURE-DECISIONS.md).

Run as: python -m matemium.mcp_server
Or integrated via the sidecar process.

Uses the mcp Python SDK (add via `pip install mcp` or the intelligence extra).
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import (
        CallToolResult,
        TextContent,
        Tool,
        Resource,
        ResourceContents,
    )
    HAS_MCP = True
except ImportError:
    HAS_MCP = False
    # Mock fallback stubs to prevent import-time compilation or crash failures
    class Server:
        def __init__(self, name: str):
            self.name = name
        def list_tools(self):
            return lambda fn: fn
        def call_tool(self):
            return lambda fn: fn
        def list_resources(self):
            return lambda fn: fn
        def read_resource(self):
            return lambda fn: fn
        async def run(self, *args, **kwargs):
            raise ImportError("MCP SDK is not installed in the current environment.")
    class Tool:
        def __init__(self, name: str, description: str, inputSchema: dict[str, Any]):
            self.name = name
            self.description = description
            self.inputSchema = inputSchema
    class Resource:
        def __init__(self, uri: str, name: str, description: str, mimeType: str | None = None):
            self.uri = uri
            self.name = name
            self.description = description
            self.mimeType = mimeType
    class ResourceContents:
        def __init__(self, uri: str, mimeType: str, text: str):
            self.uri = uri
            self.mimeType = mimeType
            self.text = text
    class TextContent:
        def __init__(self, type: str, text: str):
            self.type = type
            self.text = text

from .ipc.events import EventEmitter
from .ipc.protocol import Request

# Simple in-memory emitter for MCP context
class SimpleEmitter(EventEmitter):
    def __init__(self):
        super().__init__(stream=sys.stderr)  # logs to stderr

    def emit(self, event: str, **data: Any) -> None:
        print(f"[MCP-EVENT] {event}: {data}", file=sys.stderr)

server = Server("matemium-sidecar-mcp")

EDITABLE_PROJECT_FILES = [
    "scenes.py",
    "helpers.py",
    "brief/passport.json",
    "brief/description.md",
    "brief/tapes/main.md",
    "brief/orchestration.md",
    "brief/roadmap.json",
    "brief/tts-narration.md",
    "brief/tts-narration-style.md",
    "brief/audio-description.md",
    "brief/custom-narration.md",
    "brief/transcript.md",
    "brief/timestamps.json",
]

_TAPE_PATH = re.compile(r"^brief/tapes/[a-z0-9][a-z0-9_-]{0,63}\.md$")


def _approved_project_path(workspace: Path, filename: str, *, require_exists: bool = True) -> Path:
    if filename not in EDITABLE_PROJECT_FILES and not _TAPE_PATH.fullmatch(filename):
        raise ValueError(f"Path is outside the approved project policy: {filename}")
    root = workspace.resolve()
    candidate = (root / filename).resolve()
    if root not in candidate.parents:
        raise ValueError(f"Path escapes the project workspace: {filename}")
    if require_exists and not candidate.is_file():
        raise FileNotFoundError(filename)
    return candidate

@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools matching the agent schemas."""
    return [
        Tool(
            name="view_file",
            description="Return an approved code or project-brief file.",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "pattern": r"^(scenes\.py|helpers\.py|brief/(passport\.json|description\.md|orchestration\.md|roadmap\.json|tts-narration\.md|tts-narration-style\.md|audio-description\.md|custom-narration\.md|transcript\.md|timestamps\.json|tapes/[a-z0-9][a-z0-9_-]{0,63}\.md))$",
                    }
                },
                "required": ["filename"],
            },
        ),
        Tool(
            name="edit_file",
            description="Apply localized edits using SEARCH/REPLACE patches. Never full rewrites unless new project.",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "pattern": r"^(scenes\.py|helpers\.py|brief/(passport\.json|description\.md|orchestration\.md|roadmap\.json|tts-narration\.md|tts-narration-style\.md|audio-description\.md|custom-narration\.md|transcript\.md|timestamps\.json|tapes/[a-z0-9][a-z0-9_-]{0,63}\.md))$"},
                    "instructions": {"type": "string", "description": "One-line summary of the edit intent"},
                    "patches": {
                        "type": "string",
                        "description": "One or more SEARCH/REPLACE blocks (Aider style)",
                    },
                },
                "required": ["filename", "patches"],
            },
        ),
        Tool(
            name="compile_manim",
            description="Verify animation compiles via sidecar. Always targets 'scenes.py'.",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "enum": ["scenes.py"], "default": "scenes.py"},
                    "scene_name": {"type": "string"},
                    "quality": {
                        "type": "string",
                        "enum": ["fast_preview", "preview", "draft", "low", "medium", "high", "final"],
                        "default": "preview",
                    },
                },
                "required": ["scene_name"],
            },
        ),
        Tool(
            name="retrieve",
            description="RAG retrieve relevant code chunks (vector or keyword fallback).",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "top_k": {"type": "integer", "default": 8},
                    "workspace": {"type": "string", "description": "Optional workspace path"},
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="create_tape_content",
            description="Create an additional bounded Markdown file for one tape's visible mathematical content. Use only during the tape-content phase.",
            inputSchema={
                "type": "object",
                "properties": {
                    "slug": {"type": "string", "pattern": "^[a-z0-9][a-z0-9_-]{0,63}$"},
                    "title": {"type": "string", "minLength": 1, "maxLength": 120},
                },
                "required": ["slug", "title"],
                "additionalProperties": False,
            },
        ),
        Tool(
            name="lifecycle_status",
            description="Inspect the Passport and AI-owned Roadmap and report the current gated production phase without advancing it.",
            inputSchema={
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
        ),
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Execute the tool by delegating to sidecar handlers or direct impl."""
    emitter = SimpleEmitter()

    try:
        if name == "view_file":
            filename = arguments.get("filename")
            if not filename:
                return [TextContent(type="text", text="ERROR: filename required")]
            # For MCP in sidecar, read the file directly from workspace (grounded)
            ws = Path(os.environ.get("MATEMIUM_ROOT") or ".")
            path = _approved_project_path(ws, filename)
            content = path.read_text(encoding="utf-8", errors="replace")
            return [TextContent(type="text", text=content)]

        elif name == "edit_file":
            filename = arguments.get("filename")
            patches = arguments.get("patches", "")
            instructions = arguments.get("instructions", "")
            ws = Path(os.environ.get("MATEMIUM_ROOT") or ".")
            _approved_project_path(ws, str(filename))
            # Delegate to sidecar logic if possible, but edit is desktop side.
            # For local MCP, simulate or call a handler.
            # In practice, desktop would apply, but for sidecar MCP we can provide patch result.
            # For now, return the intended edit for client to apply, or implement simple apply.
            # To keep grounded, we can write to file here for demo, but better return.
            result = {
                "ok": True,
                "filename": filename,
                "instructions": instructions,
                "applied_patches": patches,  # client should apply
                "note": "Patch returned; apply via desktop patch engine in full integration.",
            }
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "compile_manim":
            filename = arguments.get("filename", "scenes.py")
            scene_name = arguments.get("scene_name")
            quality = arguments.get("quality", "preview")
            if not scene_name:
                return [TextContent(type="text", text="ERROR: scene_name required")]

            # Delegate to sidecar dispatch
            req = Request(
                id="mcp-compile",
                command="check_project",
                params={"workspace": os.environ.get("MATEMIUM_ROOT", "."), "scene": scene_name, "path": filename},
            )
            # Use programmatic handler
            from .ipc.server import handle_request
            resp = handle_request(req, emitter)
            if not resp.ok:
                return [TextContent(type="text", text=f"COMPILE_CHECK_FAILED: {resp.error}")]

            # Then render if check ok
            req2 = Request(
                id="mcp-render",
                command="render_project",
                params={
                    "workspace": os.environ.get("MATEMIUM_ROOT", "."),
                    "scene": scene_name,
                    "quality": quality,
                },
            )
            resp2 = handle_request(req2, emitter)
            if resp2.ok:
                return [TextContent(type="text", text=json.dumps(resp2.result, indent=2))]
            return [TextContent(type="text", text=f"COMPILE_FAILED: {resp2.error}")]

        elif name == "retrieve":
            query = arguments.get("query", "")
            top_k = arguments.get("top_k", 8)
            ws = arguments.get("workspace") or os.environ.get("MATEMIUM_ROOT")
            params = {"query": query, "top_k": top_k}
            if ws:
                params["workspace"] = ws
            # Use the retrieve handler
            req = Request(id="mcp-retrieve", command="retrieve", params=params)
            from .ipc.server import handle_request
            resp = handle_request(req, emitter)
            if resp.ok:
                return [TextContent(type="text", text=json.dumps(resp.result, indent=2))]
            return [TextContent(type="text", text=f"RETRIEVE_FAILED: {resp.error}")]

        elif name == "create_tape_content":
            slug = str(arguments.get("slug", ""))
            title = str(arguments.get("title", "")).strip()
            if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", slug) or not title:
                return [TextContent(type="text", text="ERROR: valid slug and title required")]
            ws = Path(os.environ.get("MATEMIUM_ROOT") or ".")
            filename = f"brief/tapes/{slug}.md"
            path = _approved_project_path(ws, filename, require_exists=False)
            if path.exists():
                return [TextContent(type="text", text=f"ERROR: {filename} already exists")]
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                f"# Tape content — {title}\n\n"
                "Keep only the visible mathematical/reasoning content here. "
                "Use stable beat identifiers and put staging in brief/orchestration.md.\n\n"
                "## beat-opening — Opening\n\n"
                "- **Visible statement:**\n"
                "- **Mathematical content:**\n"
                "- **Diagram or labels:**\n"
                "- **Reveal/hold intent:**\n"
                "- **Accuracy notes:**\n",
                encoding="utf-8",
            )
            return [TextContent(type="text", text=json.dumps({"ok": True, "path": filename}))]

        elif name == "lifecycle_status":
            ws = Path(os.environ.get("MATEMIUM_ROOT") or ".")
            passport = json.loads(_approved_project_path(ws, "brief/passport.json").read_text(encoding="utf-8"))
            roadmap = json.loads(_approved_project_path(ws, "brief/roadmap.json").read_text(encoding="utf-8"))
            phases = roadmap.get("phases") if isinstance(roadmap.get("phases"), list) else []
            current_id = roadmap.get("current_phase")
            current = next((phase for phase in phases if phase.get("id") == current_id), None)
            output = {
                "production_path": passport.get("production_path"),
                "passport_readiness": passport.get("readiness"),
                "current_phase": current,
                "invalidated_phases": roadmap.get("invalidated_phases", []),
                "blockers": roadmap.get("blockers", []),
            }
            return [TextContent(type="text", text=json.dumps(output, indent=2))]

        return [TextContent(type="text", text=f"ERROR: unknown tool {name}")]

    except Exception as e:
        return [TextContent(type="text", text=f"ERROR: {str(e)}")]

# Optional: expose resources for vector chunks etc.
@server.list_resources()
async def list_resources() -> list[Resource]:
    return [
        Resource(
            uri="matemium://workspace/scenes.py",
            name="scenes.py",
            description="Current visual timeline code",
            mimeType="text/x-python",
        ),
        Resource(
            uri="matemium://workspace/helpers.py",
            name="helpers.py",
            description="Supporting computations and reusable project data",
            mimeType="text/x-python",
        ),
        Resource(
            uri="matemium://rag/recent",
            name="Recent RAG chunks",
            description="Recently retrieved or indexed code patterns",
        ),
    ]

@server.read_resource()
async def read_resource(uri: str) -> list[ResourceContents]:
    if uri == "matemium://workspace/scenes.py":
        ws = os.environ.get("MATEMIUM_ROOT", ".")
        content = (Path(ws) / "scenes.py").read_text(errors="replace")
        return [ResourceContents(uri=uri, mimeType="text/x-python", text=content)]
    if uri == "matemium://workspace/helpers.py":
        ws = os.environ.get("MATEMIUM_ROOT", ".")
        content = (Path(ws) / "helpers.py").read_text(errors="replace")
        return [ResourceContents(uri=uri, mimeType="text/x-python", text=content)]
    if uri == "matemium://rag/recent":
        # Could call retrieve with default
        return [ResourceContents(uri=uri, mimeType="application/json", text=json.dumps({"note": "Use retrieve tool for RAG"}))]
    raise ValueError(f"Unknown resource: {uri}")

async def main():
    """Run the MCP server over stdio (standard for local MCP clients)."""
    if not HAS_MCP:
        raise ImportError("MCP SDK not installed. Install with: pip install 'matemium[intelligence]' or 'mcp'")

    # Ensure workspace context if needed
    if "MATEMIUM_ROOT" not in os.environ:
        print("Warning: MATEMIUM_ROOT not set. MCP will use CWD for workspace files.", file=sys.stderr)

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )

if __name__ == "__main__":
    asyncio.run(main())
