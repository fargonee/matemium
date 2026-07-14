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

@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools matching the agent schemas."""
    return [
        Tool(
            name="view_file",
            description="Return current code so the agent has context. Only 'scenes.py' or 'assets.py'.",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "enum": ["scenes.py", "assets.py"],
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
                    "filename": {"type": "string", "enum": ["scenes.py", "assets.py"]},
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
                        "enum": ["preview", "draft", "low", "medium", "high", "final"],
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
            name="run_lifecycle",
            description="Execute the complete 5-phase multi-agent lifecycle to generate, synchronize, and compile mathematical animations.",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_prompt": {"type": "string", "description": "The creative prompt explaining the mathematical animation concept"},
                    "mode": {"type": "string", "enum": ["audio", "mute"], "description": "Audio-First (renders audio + timestamps) vs Mute-Mode (beat-cadence estimations)", "default": "mute"},
                    "model_tier": {"type": "string", "enum": ["standard", "elite", "deep"], "default": "standard"},
                    "account_tier": {"type": "string", "enum": ["basic", "premium"], "default": "basic"},
                },
                "required": ["user_prompt"],
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
            # In full setup, workspace comes from env or param
            ws = os.environ.get("MATEMIUM_ROOT") or "."
            path = Path(ws) / filename
            if path.exists():
                content = path.read_text(encoding="utf-8", errors="replace")
                return [TextContent(type="text", text=content)]
            return [TextContent(type="text", text=f"ERROR: {filename} not found")]

        elif name == "edit_file":
            filename = arguments.get("filename")
            patches = arguments.get("patches", "")
            instructions = arguments.get("instructions", "")
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

        elif name == "run_lifecycle":
            user_prompt = arguments.get("user_prompt")
            mode_str = arguments.get("mode", "mute")
            model_tier_str = arguments.get("model_tier", "standard")
            account_tier_str = arguments.get("account_tier", "basic")
            
            from .agent.models import ProcessingMode, ModelTier, AccountTier
            from .agent.coordinator import run_lifecycle
            
            mode = ProcessingMode(mode_str)
            model_tier = ModelTier(model_tier_str)
            account_tier = AccountTier(account_tier_str)
            
            ws = os.environ.get("MATEMIUM_ROOT") or "."
            
            # Execute the 5-phase lifecycle
            result = run_lifecycle(
                project_dir=ws,
                user_prompt=user_prompt,
                mode=mode,
                model_tier=model_tier,
                account_tier=account_tier,
            )
            
            # Prepare serializable result dict
            output = {
                "ok": True,
                "duration": result.post_production.total_duration,
                "segments_count": len(result.blueprint.segments),
                "tokens_spent": result.token_ledger.total_credits_spent(),
                "artifacts": {
                    "scenes_created": (Path(ws) / "scenes.py").exists(),
                    "assets_created": (Path(ws) / "assets.py").exists(),
                }
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
            uri="matemium://workspace/assets.py",
            name="assets.py",
            description="Supporting assets and computations",
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
    if uri == "matemium://workspace/assets.py":
        ws = os.environ.get("MATEMIUM_ROOT", ".")
        content = (Path(ws) / "assets.py").read_text(errors="replace")
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
