#!/usr/bin/env python3
"""spa_server.py — SPA-aware static file server with /api/* reverse proxy.

역할:
  1. /api/* → API 서버(PORT_API)로 리버스 프록시
  2. 정적 파일 존재 → 그대로 반환
  3. 정적 파일 없음 → index.html 반환 (React Router SPA fallback)

Vite dev server의 proxy 설정을 프로덕션에서도 동일하게 재현.

Usage:
    python spa_server.py \\
        --port 5173 --bind 0.0.0.0 \\
        --dir /app/dashboard/dist \\
        --api-url http://127.0.0.1:8765
"""
from __future__ import annotations

import argparse
import http.client
import io
import os
import urllib.parse
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

_API_URL: str = "http://127.0.0.1:8765"
_STATIC_DIR: str = "."


class SPAHandler(SimpleHTTPRequestHandler):
    """Serve static files (SPA fallback) + reverse-proxy /api/* to API server."""

    # ── routing ──────────────────────────────────────────────────────────────

    def _is_api(self) -> bool:
        return self.path.startswith("/api")

    # ── reverse proxy ────────────────────────────────────────────────────────

    def _proxy(self, method: str) -> None:
        parsed = urllib.parse.urlparse(_API_URL)
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or 8765

        try:
            conn = http.client.HTTPConnection(host, port, timeout=30)
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length) if length else None

            hop_by_hop = {"host", "connection", "transfer-encoding", "keep-alive",
                          "proxy-authenticate", "proxy-authorization", "te", "trailers", "upgrade"}
            fwd_headers: dict[str, str] = {
                k: v for k, v in self.headers.items()
                if k.lower() not in hop_by_hop
            }
            fwd_headers["Host"] = f"{host}:{port}"

            conn.request(method, self.path, body=body, headers=fwd_headers)
            resp = conn.getresponse()
            resp_body = resp.read()

            self.send_response(resp.status)
            for k, v in resp.getheaders():
                if k.lower() not in hop_by_hop:
                    self.send_header(k, v)
            self.send_header("Content-Length", str(len(resp_body)))
            self.end_headers()
            self.wfile.write(resp_body)
        except Exception as exc:
            msg = f"API proxy error: {exc}".encode()
            self.send_response(502)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(msg)))
            self.end_headers()
            self.wfile.write(msg)
        finally:
            try:
                conn.close()  # type: ignore[possibly-undefined]
            except Exception:
                pass

    # ── HTTP methods ─────────────────────────────────────────────────────────

    def do_GET(self) -> None:  # noqa: N802
        if self._is_api():
            self._proxy("GET")
            return
        # SPA fallback: 파일이 없으면 index.html 서빙
        path_only = self.path.split("?")[0].split("#")[0]
        abs_path = Path(_STATIC_DIR) / path_only.lstrip("/")
        if not abs_path.exists():
            self.path = "/index.html"
        super().do_GET()

    def do_HEAD(self) -> None:  # noqa: N802
        if self._is_api():
            self._proxy("HEAD")
            return
        super().do_HEAD()

    def do_POST(self) -> None:  # noqa: N802
        if self._is_api():
            self._proxy("POST")
        else:
            self.send_error(405)

    def do_PUT(self) -> None:  # noqa: N802
        if self._is_api():
            self._proxy("PUT")
        else:
            self.send_error(405)

    def do_DELETE(self) -> None:  # noqa: N802
        if self._is_api():
            self._proxy("DELETE")
        else:
            self.send_error(405)

    def do_PATCH(self) -> None:  # noqa: N802
        if self._is_api():
            self._proxy("PATCH")
        else:
            self.send_error(405)

    # ── logging ──────────────────────────────────────────────────────────────

    def log_message(self, fmt: str, *args: object) -> None:
        if args and "favicon" in str(args[0]):
            return
        super().log_message(fmt, *args)


def main() -> None:
    global _API_URL, _STATIC_DIR

    parser = argparse.ArgumentParser(description="SPA static file server + API reverse proxy")
    parser.add_argument("--port", type=int, default=5173)
    parser.add_argument("--bind", default="0.0.0.0")
    parser.add_argument("--dir", default=".")
    parser.add_argument(
        "--api-url",
        default=os.environ.get(
            "API_URL",
            f"http://127.0.0.1:{os.environ.get('PORT_API', '8765')}",
        ),
        help="API 서버 base URL (default: http://127.0.0.1:PORT_API)",
    )
    args = parser.parse_args()

    _API_URL = args.api_url.rstrip("/")
    _STATIC_DIR = os.path.abspath(args.dir)
    os.chdir(_STATIC_DIR)

    # SimpleHTTPRequestHandler가 translate_path()에서 self.directory를 사용
    SPAHandler.directory = _STATIC_DIR  # type: ignore[attr-defined]

    print(f"[spa_server] static  → {_STATIC_DIR}")
    print(f"[spa_server] /api/*  → {_API_URL}")
    print(f"[spa_server] listen  → {args.bind}:{args.port}")

    server = ThreadingHTTPServer((args.bind, args.port), SPAHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[spa_server] Shutting down.")
        server.shutdown()


if __name__ == "__main__":
    main()
