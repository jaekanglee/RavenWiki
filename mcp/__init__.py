"""mcp — Model Context Protocol server for the wiki vault.

Provides a standardized MCP interface (7 tools + 5 resources) over wiki.db.
Default mode is read-only; write/admin require explicit CLI flags.

Submodules:
    server      — FastMCP CLI entrypoint (stdio + streamable-http transports)
    db          — wiki.db query helpers (read-only)
    tools       — MCP tool implementations (read.py, write.py)
    resources   — MCP resource providers
"""
__version__ = "0.1.0"