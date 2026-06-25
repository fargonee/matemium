"""Run with: python -m matemium_server"""

from __future__ import annotations

import uvicorn

from .config import settings


def main() -> None:
    # In production / PaaS (Northflank etc.), bind to 0.0.0.0 so the platform can reach us.
    # Keep 127.0.0.1 only for explicit local dev.
    host = settings.host
    if host in ("127.0.0.1", "localhost") and settings.env != "development":
        host = "0.0.0.0"

    uvicorn.run(
        "matemium_server.app:app",
        host=host,
        port=settings.port,
        reload=settings.env == "development",
    )


if __name__ == "__main__":
    main()