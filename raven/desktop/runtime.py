"""Desktop Python Core — starts the real Raven API on a random loopback port.

Readiness protocol (unchanged from spike):
  stdout line 1 → {"host": "127.0.0.1", "port": <int>}

The Tauri shell reads this line, then exposes the endpoint to the webview
via the ``core_endpoint`` command.
"""
from __future__ import annotations

import json
import os
import signal
import socket
import sys
import threading
import time


LOOPBACK_HOST = "127.0.0.1"


def _free_port() -> int:
    """Bind to port 0 to let the OS assign a free port, then release."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((LOOPBACK_HOST, 0))
        return s.getsockname()[1]


def main() -> int:
    import uvicorn

    port = _free_port()

    # CORS: allow the Tauri webview origin (prod + dev) before app import.
    extra = os.environ.get("RAVEN_EXTRA_CORS_ORIGIN", "")
    os.environ["RAVEN_EXTRA_CORS_ORIGIN"] = (
        f"{extra},http://tauri.localhost,http://localhost:5173"
        if extra
        else "http://tauri.localhost,http://localhost:5173"
    )

    config = uvicorn.Config(
        "raven.api:app",
        host=LOOPBACK_HOST,
        port=port,
        log_level="warning",
    )
    server = uvicorn.Server(config)

    def stop(_signum: int, _frame: object) -> None:
        server.should_exit = True

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)

    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    deadline = time.monotonic() + 10
    while not server.started:
        if time.monotonic() > deadline:
            print("Python Core: uvicorn startup timeout", file=sys.stderr)
            return 1
        time.sleep(0.05)

    print(json.dumps({"host": LOOPBACK_HOST, "port": port}), flush=True)

    try:
        while not server.should_exit:
            time.sleep(0.1)
    except KeyboardInterrupt:
        pass
    server.should_exit = True
    thread.join(timeout=5)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
