"""tools — MCP tool implementations for the wiki vault.

Split into read.py (default, no permission) and write.py (--write / --admin).
All tools share a VaultContext that carries the vault root and the active
permission mode.

M4 / F1 — provenance + idempotency helpers live here so every write tool can
reach them without reimplementing the JSON file dance. The store is per-vault
(under ``<vault>/.mcp/idempotency.json``), append-only, and intentionally
lock-free: the multi-agent write caveat in AGENTS.md §3 still applies —
idempotency prevents accidental *retry*, not concurrent writers.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional


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
    """Build a VaultContext.

    Default vault follows the same destination as `cli._resolve_vault`
    and `db._default_vault` (one level above the `mcp/` package = vault
    root). Note this file lives one level deeper than the other two
    helpers (inside `mcp/tools/`), so the walk-up needs three `.parent`
    calls instead of two — the destination is the same.
    """
    if vault is None:
        # parent.parent.parent = .../mcp/tools/__init__.py
        #                     → .../mcp/tools/ → .../mcp/ → .../<vault-root>
        vault = Path(__file__).resolve().parent.parent.parent
    return VaultContext(vault=Path(vault), mode=mode)


# ─────────────── M4 / F1 — provenance + idempotency ───────────────


# Default actor when the caller does not identify themselves. Surfaced in
# frontmatter and log entries so we can always answer "who wrote this?".
ANONYMOUS_ACTOR = "anonymous"


def normalize_actor(actor: Optional[str]) -> str:
    """Normalize an actor string.

    Strips whitespace; falls back to ``ANONYMOUS_ACTOR`` for ``None`` /
    empty / whitespace-only input. Does *not* validate against a user
    registry — MCP has no such concept and AGENTS.md §3 calls out that
    multi-agent identity is the caller's responsibility.
    """
    if actor is None:
        return ANONYMOUS_ACTOR
    cleaned = actor.strip()
    return cleaned or ANONYMOUS_ACTOR


def _idempotency_path(vault: Path) -> Path:
    """Where the idempotency store lives for a given vault.

    ``.mcp/`` is gitignored elsewhere — this file is intentionally not
    part of the vault's source of truth. It is best-effort persistence
    for retry suppression across MCP server restarts.
    """
    return vault / ".mcp" / "idempotency.json"


def _load_idempotency_store(vault: Path) -> dict[str, dict[str, Any]]:
    """Read the idempotency store from disk. Returns ``{}`` on miss / error.

    Failures are swallowed (logged to stderr) so a corrupted store never
    blocks a legitimate write — the trade-off is documented in F1 as
    "best-effort persistence".
    """
    path = _idempotency_path(vault)
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        if isinstance(data, dict):
            return data
        # Wrong shape — treat as empty.
        return {}
    except (OSError, json.JSONDecodeError) as exc:
        import sys
        print(f"⚠️  idempotency store unreadable ({exc}); treating as empty",
              file=sys.stderr)
        return {}


def _save_idempotency_store(vault: Path, store: dict[str, dict[str, Any]]) -> bool:
    """Atomically persist the idempotency store.

    Writes to a sibling temp file then ``os.replace``s into place so a
    crash mid-write never leaves a half-truncated JSON on disk. Returns
    True on success, False on error (caller decides whether to fail-closed).
    """
    path = _idempotency_path(vault)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(
            prefix="idempotency.", suffix=".tmp", dir=path.parent
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(store, fh, ensure_ascii=False, indent=2, sort_keys=True)
            os.replace(tmp_name, path)
            return True
        except Exception:
            # Clean up the temp file if the replace never happened.
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
            raise
    except OSError as exc:
        import sys
        print(f"⚠️  could not persist idempotency store: {exc}", file=sys.stderr)
        return False


def params_fingerprint(params: dict[str, Any]) -> str:
    """Stable short hash of the write parameters.

    Used to detect a *different* write that happens to reuse the same
    idempotency_key — in that case we surface a clear error instead of
    silently returning a stale cached result.
    """
    # sort_keys=True plus separators produces a canonical encoding.
    blob = json.dumps(params, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def now_iso() -> str:
    """Local-time ISO-8601 timestamp (seconds precision, no tz suffix).

    The vault is a single-machine artefact; UTC offsets are noise. We
    match the existing `dt.datetime.now().isoformat()` style used by
    ``wiki_delete`` / ``wiki_rename``.
    """
    return dt.datetime.now().replace(microsecond=0).isoformat()


def lookup_idempotent(
    vault: Path,
    idempotency_key: Optional[str],
    tool: str,
    params: dict[str, Any],
) -> Optional[dict[str, Any]]:
    """Return the cached response if ``idempotency_key`` was already used.

    Returns ``None`` when:
      - ``idempotency_key`` is falsy (no protection requested), or
      - the key is not in the store (first call), or
      - the cached ``tool``/``fingerprint`` does not match (key reuse for
        a *different* write → caller should treat as conflict).

    A fingerprint mismatch is reported via ``{"_idempotency_conflict": True,
    "stored": {...}}`` so the tool can fail-closed with a clear message.
    """
    if not idempotency_key:
        return None
    store = _load_idempotency_store(vault)
    entry = store.get(idempotency_key)
    if entry is None:
        return None
    fp = params_fingerprint(params)
    if entry.get("tool") != tool or entry.get("fingerprint") != fp:
        return {"_idempotency_conflict": True, "stored": entry}
    return entry.get("response")


def record_idempotent(
    vault: Path,
    idempotency_key: Optional[str],
    tool: str,
    params: dict[str, Any],
    response: dict[str, Any],
) -> None:
    """Persist the response under ``idempotency_key`` for future retries.

    No-op when ``idempotency_key`` is falsy. Failure to persist is logged
    but never raised — losing the idempotency cache just means a retry
    will re-execute, which is the pre-F1 behavior.
    """
    if not idempotency_key:
        return
    store = _load_idempotency_store(vault)
    store[idempotency_key] = {
        "tool": tool,
        "fingerprint": params_fingerprint(params),
        "timestamp": now_iso(),
        "response": response,
    }
    _save_idempotency_store(vault, store)


def append_log_entry(
    vault: Path,
    action: str,
    subject: str,
    actor: str,
    idempotency_key: Optional[str] = None,
    extras: Optional[list[str]] = None,
) -> bool:
    """Append a provenance entry to ``<vault>/log.md``.

    Format mirrors the existing entries (e.g. ``## [2026-06-24] create | SCHEMA``)
    with optional M4/F1 sub-bullets for actor and idempotency_key. Returns
    True on success, False on error — the caller is expected to surface
    the failure in its response but never let it crash a write that
    already mutated files.
    """
    try:
        log_path = vault / "log.md"
        today = dt.date.today().isoformat()
        lines = [f"\n## [{today}] {action} | {subject} via mcp"]
        lines.append(f"- actor: {actor}")
        if idempotency_key:
            lines.append(f"- idempotency_key: {idempotency_key}")
        if extras:
            for extra in extras:
                lines.append(f"- {extra}")
        with log_path.open("a", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")
        return True
    except OSError as exc:
        import sys
        print(f"⚠️  could not append log.md entry: {exc}", file=sys.stderr)
        return False