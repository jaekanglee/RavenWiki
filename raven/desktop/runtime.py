"""Minimal local Python Core process for the Desktop Runtime spike.

This is intentionally not the production Raven API.  It proves that a desktop
shell can own a Python child process, receive its dynamically assigned loopback
endpoint, probe readiness, and terminate it without touching a vault.
"""
from __future__ import annotations

import json
import signal
import sys
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


LOOPBACK_HOST = "127.0.0.1"


class _HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802 - stdlib handler contract
        if self.path != "/health":
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        body = b'{"status": "ready"}'
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        """Keep stdout reserved for the one readiness payload."""


def main() -> int:
    server = ThreadingHTTPServer((LOOPBACK_HOST, 0), _HealthHandler)

    def stop(_signum: int, _frame: object) -> None:
        # shutdown() must run outside serve_forever's thread to avoid deadlock.
        threading.Thread(target=server.shutdown, daemon=True).start()

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)

    print(json.dumps({"host": LOOPBACK_HOST, "port": server.server_port}), flush=True)
    try:
        server.serve_forever(poll_interval=0.1)
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
