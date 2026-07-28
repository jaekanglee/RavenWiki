"""Desktop Python Core — starts the real Raven API on a random loopback port.

Readiness protocol:
  stdout line 1 → {"host": "127.0.0.1", "port": <int>}
  With --mcp:    → {"host": "127.0.0.1", "port": <int>, "mcp_port": <int>}

The Tauri shell reads this line, then exposes the endpoint(s) to the webview
via the ``core_endpoint`` / ``mcp_endpoint`` commands.

External access (Tailscale):
  --host 0.0.0.0  binds all interfaces (same pattern as ``python -m raven.api``).
  The readiness JSON always reports 127.0.0.1 so the local webview keeps working.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import signal
import socket
import sys
import threading
import time


LOOPBACK_HOST = "127.0.0.1"
DEFAULT_MCP_PORT = 8765


def _free_port(host: str = LOOPBACK_HOST) -> int:
    """Bind to port 0 to let the OS assign a free port, then release."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((host, 0))
        return s.getsockname()[1]


def _build_mcp_app(mode: str):
    """Create the FastMCP streamable-http Starlette app (same as raven.mcp.cli)."""
    from mcp.server.fastmcp import FastMCP
    from mcp.server.transport_security import TransportSecuritySettings
    from raven.mcp.cli import register_tools
    from raven.mcp.resources import register_resources
    from raven.core.registry import registry

    reg = registry()
    vault_names = sorted(v.name for v in reg.list())

    mcp = FastMCP(
        "wiki",
        transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
        instructions=(
            "Raven multi-vault Markdown PKM MCP server. "
            f"Registered vaults: {', '.join(vault_names) or '(none)'}."
        ),
    )
    register_tools(mcp, mode)
    register_resources(mcp)
    return mcp.streamable_http_app()


def main() -> int:
    parser = argparse.ArgumentParser(prog="raven-desktop-core")
    parser.add_argument(
        "--host",
        default=LOOPBACK_HOST,
        help="Bind address (127.0.0.1 default; 0.0.0.0 for Tailscale/external access)",
    )
    parser.add_argument("--mcp", action="store_true", help="Enable MCP HTTP listener")
    parser.add_argument("--mcp-port", type=int, default=DEFAULT_MCP_PORT, help="MCP HTTP port")
    parser.add_argument("--mcp-mode", choices=["read", "write", "admin"], default="read")
    args = parser.parse_args()

    import uvicorn

    bind_host = os.environ.get("RAVEN_HOST", args.host)
    if bind_host.lower() in ("tailscale", "auto-tailscale", "ts") or bind_host == "0.0.0.0":
        from raven.api.main import get_tailscale_ip
        ts_ip = get_tailscale_ip()
        if ts_ip and bind_host.lower() in ("tailscale", "auto-tailscale", "ts"):
            bind_host = ts_ip
            print(f"🔒 [Desktop Core] Auto-bound to Tailscale IP: {ts_ip}", file=sys.stderr)

    api_port = _free_port(bind_host)

    # CORS: allow the Tauri webview origin (prod + dev) before app import.
    extra = os.environ.get("RAVEN_EXTRA_CORS_ORIGIN", "")
    os.environ["RAVEN_EXTRA_CORS_ORIGIN"] = (
        f"{extra},http://tauri.localhost,http://localhost:5173"
        if extra
        else "http://tauri.localhost,http://localhost:5173"
    )

    api_config = uvicorn.Config(
        "raven.api:app",
        host=bind_host,
        port=api_port,
        log_level="warning",
    )
    api_server = uvicorn.Server(api_config)

    # Optional MCP server
    mcp_server: uvicorn.Server | None = None
    if args.mcp:
        mcp_app = _build_mcp_app(args.mcp_mode)
        mcp_config = uvicorn.Config(
            mcp_app,
            host=bind_host,
            port=args.mcp_port,
            log_level="warning",
        )
        mcp_server = uvicorn.Server(mcp_config)

    def stop(_signum: int, _frame: object) -> None:
        api_server.should_exit = True
        if mcp_server is not None:
            mcp_server.should_exit = True

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)

    api_thread = threading.Thread(target=api_server.run, daemon=True)
    api_thread.start()

    mcp_thread: threading.Thread | None = None
    if mcp_server is not None:
        mcp_thread = threading.Thread(target=mcp_server.run, daemon=True)
        mcp_thread.start()

    # Wait for API readiness
    deadline = time.monotonic() + 10
    while not api_server.started:
        if time.monotonic() > deadline:
            print("Python Core: uvicorn startup timeout", file=sys.stderr)
            return 1
        time.sleep(0.05)

    # Wait for MCP readiness (if enabled)
    if mcp_server is not None:
        mcp_deadline = time.monotonic() + 10
        while not mcp_server.started:
            if time.monotonic() > mcp_deadline:
                print("Python Core: MCP uvicorn startup timeout", file=sys.stderr)
                return 1
            time.sleep(0.05)

    ready = {"host": LOOPBACK_HOST, "port": api_port}
    if args.mcp:
        ready["mcp_port"] = args.mcp_port
    print(json.dumps(ready), flush=True)

    try:
        while not api_server.should_exit:
            time.sleep(0.1)
    except KeyboardInterrupt:
        pass
    api_server.should_exit = True
    if mcp_server is not None:
        mcp_server.should_exit = True
    api_thread.join(timeout=5)
    if mcp_thread is not None:
        mcp_thread.join(timeout=5)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
