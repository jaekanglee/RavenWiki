"""api.main — uvicorn entry point.

Usage:
    python -m raven.api                            # 127.0.0.1:8765
    python -m raven.api --host 0.0.0.0 --port 9000
"""
from __future__ import annotations

import argparse
import sys

import uvicorn


import os

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="raven-api")
    default_host = os.environ.get("RAVEN_HOST", "0.0.0.0" if os.environ.get("RAVEN_ALLOW_ALL_CORS") else "127.0.0.1")
    default_port = int(os.environ.get("RAVEN_PORT", os.environ.get("PORT_API", "8765")))
    parser.add_argument("--host", default=default_host, help="Host to bind (default: RAVEN_HOST or 127.0.0.1)")
    parser.add_argument("--port", type=int, default=default_port, help="Port to bind (default: RAVEN_PORT or 8765)")
    parser.add_argument("--reload", action="store_true", help="dev: auto-reload")
    args = parser.parse_args(argv)
    uvicorn.run(
        "raven.api:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info",
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
