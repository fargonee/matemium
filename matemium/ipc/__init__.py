"""JSON-line IPC protocol for the Matemium desktop sidecar."""

from .protocol import IPC_PROTOCOL_VERSION
from .server import run_server

__all__ = ["IPC_PROTOCOL_VERSION", "run_server"]