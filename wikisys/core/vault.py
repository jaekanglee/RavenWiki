"""vault — single-vault handle.

A vault is any folder on disk containing:
    .vault.json    — metadata (name, mode, owner, created, description)
    content/       — user markdown (Obsidian-style hierarchy)
    _meta/         — system markdown (SCHEMA, RULES, scripts)
    wiki.db        — sqlite index (build artifact, gitignored)

The CLI resolves the *active* vault via:
  1. `--vault NAME` flag (explicit override)
  2. `WIKI_VAULT` env var
  3. registry's `default` vault
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .registry import registry, VaultMeta


@dataclass
class Vault:
    """In-memory handle to a single vault on disk."""

    meta: VaultMeta
    root: Path

    @classmethod
    def load(cls, meta: VaultMeta) -> "Vault":
        root = meta.path
        if not root.exists():
            raise FileNotFoundError(f"vault path missing: {root}")
        return cls(meta=meta, root=root)

    @classmethod
    def create(cls, name: str, path: Path, mode: str = "personal", owner: str = "user", description: str = "") -> "Vault":
        """Create a new vault on disk and register it."""
        path = Path(path).expanduser().resolve()
        path.mkdir(parents=True, exist_ok=True)
        meta = VaultMeta(
            name=name,
            path=path,
            mode=mode,
            owner=owner,
            created=__import__("datetime").date.today().isoformat(),
            description=description,
        )
        # write per-vault meta
        (path / ".vault.json").write_text(json.dumps(meta.to_json(), indent=2, ensure_ascii=False))
        # register
        registry().add(meta)
        return cls(meta=meta, root=path)

    # ─── path helpers ──────────────────────────────

    @property
    def db_path(self) -> Path:
        return self.root / "wiki.db"

    @property
    def content_root(self) -> Path:
        return self.root / "content"

    @property
    def meta_root(self) -> Path:
        return self.root / "_meta"

    # ─── bootstrap helpers ─────────────────────────

    def ensure_dirs(self) -> None:
        self.content_root.mkdir(parents=True, exist_ok=True)
        self.meta_root.mkdir(parents=True, exist_ok=True)


def resolve_active_vault(name: Optional[str] = None) -> Vault:
    """Resolve which vault to operate on.

    Priority:
      1. explicit `name` arg
      2. `WIKI_VAULT` env var
      3. registry default
    """
    reg = registry()
    chosen_name = (
        name
        or os.environ.get("WIKI_VAULT", "").strip()
        or reg._data.get("default", "")
    )
    if chosen_name:
        meta = reg.get(chosen_name)
        if meta is None:
            raise ValueError(f"vault {chosen_name!r} not in registry")
        return Vault.load(meta)
    default = reg.default()
    if default is None:
        raise ValueError(
            "no vaults registered. Create one first:\n"
            "  wikisys vault create <name> <path>"
        )
    return Vault.load(default)
