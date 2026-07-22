"""Matemium engine sidecar — JSON-line IPC over stdin/stdout for Tauri."""

from __future__ import annotations

import argparse
import sys

from .ipc.server import run_server
from .paths import ensure_on_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="matemium-sidecar",
        description="Matemium engine sidecar (desktop IPC daemon)",
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="Print version and exit (does not start the request loop)",
    )
    parser.add_argument(
        "--mcp",
        action="store_true",
        help="Run as MCP server (stdio) exposing tools/resources for local agents/clients. Requires 'mcp' extra.",
    )
    parser.add_argument(
        "--llm-worker",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--local-openai-server",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    parser.add_argument("--host", default="127.0.0.1", help=argparse.SUPPRESS)
    parser.add_argument("--port", type=int, default=0, help=argparse.SUPPRESS)
    return parser


def main(argv: list[str] | None = None) -> int:
    ensure_on_path()
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.version:
        from .__version__ import __version__
        from .ipc.protocol import IPC_PROTOCOL_VERSION

        print(f"matemium-sidecar {__version__} (protocol {IPC_PROTOCOL_VERSION})")
        return 0

    if args.mcp:
        # Run MCP server mode (for local MCP clients)
        from .mcp_server import main as run_mcp
        import asyncio
        asyncio.run(run_mcp())
        return 0

    if args.llm_worker:
        from .agent.llm_worker import worker_main

        return worker_main()

    if args.local_openai_server:
        from .agent.local_openai_server import main as run_local_openai_server

        return run_local_openai_server(["--host", args.host, "--port", str(args.port)])

    # Sidecar protocol traffic uses stdout; keep stderr for engine logs.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(line_buffering=True)
    return run_server(stdin=sys.stdin, stdout=sys.stdout)


if __name__ == "__main__":
    raise SystemExit(main())
