"""registry — vault discovery.

Sources of truth (in priority order):
  1. `WIKI_VAULTS_DIR` env var — root for vault lookup (default: `~/vaults`)
  2. `$WIKI_VAULTS_DIR/.registry.json` — vault index (name → meta)
  3. each `<vault>/.vault.json` — per-vault metadata

Env overrides (all optional):
  WIKI_VAULTS_DIR   — vaults root (e.g. ~/Documents/vaults, /tmp/x)
  WIKI_VAULT        — currently active vault name (for CLI/GUI default)
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# ─────────────── env-driven paths ───────────────


def VAULTS_ROOT() -> Path:
    """Vaults root. Override via $WIKI_VAULTS_DIR."""
    override = os.environ.get("WIKI_VAULTS_DIR", "").strip()
    return Path(override).expanduser().resolve() if override else (Path.home() / "vaults").resolve()


def REGISTRY_PATH() -> Path:
    """Per-install vault index."""
    return VAULTS_ROOT() / ".registry.json"


# ─────────────── data model ───────────────


@dataclass(frozen=True)
class VaultMeta:
    """Single vault entry — name + path + meta."""

    name: str
    path: Path
    mode: str = "personal"      # personal | shared | agent
    owner: str = "user"
    created: str = ""
    description: str = ""
    default: bool = False

    @classmethod
    def from_json(cls, name: str, data: dict, default_name: str = "") -> "VaultMeta":
        path = Path(data["path"]).expanduser().resolve()
        return cls(
            name=name,
            path=path,
            mode=data.get("mode", "personal"),
            owner=data.get("owner", "user"),
            created=data.get("created", ""),
            description=data.get("description", ""),
            default=(name == default_name) or data.get("default", False),
        )

    def to_json(self) -> dict:
        out = {
            "path": str(self.path),
            "mode": self.mode,
            "owner": self.owner,
        }
        if self.created:
            out["created"] = self.created
        if self.description:
            out["description"] = self.description
        return out


# ─────────────── registry ───────────────


class VaultRegistry:
    """Loads/saves `.registry.json` and provides discovery helpers."""

    def __init__(self, root: Optional[Path] = None):
        self.root = root or VAULTS_ROOT()
        self.path = self.root / ".registry.json"
        self._data: dict = {}
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            self._data = {"version": 1, "default": "", "vaults": {}}
            return
        try:
            self._data = json.loads(self.path.read_text())
        except (OSError, json.JSONDecodeError):
            self._data = {"version": 1, "default": "", "vaults": {}}

    def _save(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self._data, indent=2, ensure_ascii=False))

    # ─── queries ─────────────────────────────────

    def list(self) -> list[VaultMeta]:
        default = self._data.get("default", "")
        return [
            VaultMeta.from_json(name, data, default)
            for name, data in self._data.get("vaults", {}).items()
        ]

    def get(self, name: str) -> Optional[VaultMeta]:
        data = self._data.get("vaults", {}).get(name)
        if not data:
            return None
        return VaultMeta.from_json(name, data, self._data.get("default", ""))

    def default(self) -> Optional[VaultMeta]:
        """The registry-default vault (or first if none marked)."""
        name = self._data.get("default", "")
        if name:
            v = self.get(name)
            if v:
                return v
        # fall back to first
        all_v = self.list()
        return all_v[0] if all_v else None

    # ─── mutations ──────────────────────────────

    def add(self, meta: VaultMeta) -> None:
        """Register a vault. Marks it default if it's the first."""
        vaults = self._data.setdefault("vaults", {})
        vaults[meta.name] = meta.to_json()
        if not self._data.get("default"):
            self._data["default"] = meta.name
        self._save()

    def remove(self, name: str) -> bool:
        """Remove from registry (does NOT touch the vault directory itself)."""
        vaults = self._data.get("vaults", {})
        if name not in vaults:
            return False
        del vaults[name]
        if self._data.get("default") == name:
            self._data["default"] = next(iter(vaults), "")
        self._save()
        return True

    def set_default(self, name: str) -> bool:
        if name not in self._data.get("vaults", {}):
            return False
        self._data["default"] = name
        self._save()
        return True


# ─────────────── module-level singleton ───────────────


def registry() -> VaultRegistry:
    """Lazy singleton — re-reads env on every call."""
    return VaultRegistry()
