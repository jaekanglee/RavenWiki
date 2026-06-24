"""tools — MCP tool implementations for the wiki vault.

Split into read.py (default, no permission) and write.py (--write / --admin).
All tools share a VaultContext that carries the vault root and the active
permission mode.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


# ─────────────── permission model ───────────────


READ = "read"
WRITE = "write"
ADMIN = "admin"

# Tools that require --write (mutate content)
WRITE_TOOLS: frozenset[str] = frozenset({"wiki_update", "wiki_ingest"})

# Tools that require --admin (destructive)
ADMIN_TOOLS: frozenset[str] = frozenset({"wiki_delete", "wiki_rename"})


class PermissionError_(Exception):
    """Raised when a tool is called in a mode that doesn't permit it."""


def check_permission(tool_name: str, mode: str) -> None:
    """Raise if `tool_name` cannot run under `mode`.

    mode ∈ {"read", "write", "admin"}.
    """
    if tool_name in ADMIN_TOOLS and mode != ADMIN:
        raise PermissionError_(
            f"{tool_name!r} requires --admin (current mode: {mode!r})"
        )
    if tool_name in WRITE_TOOLS and mode == READ:
        raise PermissionError_(
            f"{tool_name!r} requires --write (current mode: {mode!r})"
        )


# ─────────────── shared context ───────────────


@dataclass
class VaultContext:
    """Per-server vault handle + permission mode."""

    vault: Path
    mode: str = READ

    def require(self, tool_name: str) -> None:
        """Check that `tool_name` is permitted in self.mode."""
        check_permission(tool_name, self.mode)


def make_context(
    vault: Optional[Path | str] = None, mode: str = READ
) -> VaultContext:
    """Build a VaultContext; default vault = mcp/..."""
    if vault is None:
        vault = Path(__file__).resolve().parent.parent.parent
    return VaultContext(vault=Path(vault), mode=mode)