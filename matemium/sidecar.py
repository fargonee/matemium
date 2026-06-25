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

    # Sidecar protocol traffic uses stdout; keep stderr for engine logs.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(line_buffering=True)
    return run_server(stdin=sys.stdin, stdout=sys.stdout)


if __name__ == "__main__":
    raise SystemExit(main())