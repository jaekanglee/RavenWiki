"""registry — vault discovery.

Sources of truth (in priority order):
  1. `WIKI_VAULTS_DIR` env var — root for vault lookup (default: `~/Raven`)
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
from typing import Any, Optional


# ─────────────── env-driven paths ───────────────


def VAULTS_ROOT() -> Path:
    """Vaults root. Override via $WIKI_VAULTS_DIR.

    v0.6.3+: default changed from `~/vaults` to `~/Raven` per user
    specification — `~/Raven/<vault-name>/` is the canonical location
    for new vaults. Existing installations that relied on `~/vaults/`
    can override with `WIKI_VAULTS_DIR=~/vaults` (no migration needed).
    """
    override = os.environ.get("WIKI_VAULTS_DIR", "").strip()
    if override:
        return Path(override).expanduser().resolve()
    return (Path.home() / "Raven").resolve()


def REGISTRY_PATH() -> Path:
    """Per-install vault index."""
    return VAULTS_ROOT() / ".registry.json"


# ─────────────── data model ───────────────


@dataclass(frozen=True)
class VaultMeta:
    """Single vault entry — name + path + meta.

    v0.6.39+: `mode` (personal/agent/shared) is **display-only metadata**.
    No code branches on mode. Write/lint policy is determined by `features`
    and path scope, not mode.

    v0.6.39+: `allow_tier1_leak: bool` lets users opt-in to importing
    raven-internal docs (OPERATIONS.md, agent/*, raven-policy.md) into
    their vault for customization. Default False (safe).

    v0.6.39+: `features: dict` enables LLM Wiki patterns per-vault.
    Empty by default; user adds `{"llm_wiki": true}` to opt in.

    v0.7.37+: `agents: tuple` — *opt-in* write allowlist.
    Empty tuple = no policy (every actor may write, default behavior).
    Non-empty tuple = ONLY actors in this list may write through the
    shared `write_page()` contract. Reads are always unrestricted
    (`search`, `get_page`, `graph`, etc.).

    Rationale:
        Users operate multiple vaults where each is the runtime scope of
        a distinct agent/team. A vault can opt-in to refuse writes from
        actors outside its declared agent set, so an agent cannot
        silently edit another vault's data even with valid
        credentials. Negative (`empty`) value preserves backward
        compatibility — only opt-in vaults enforce.
    """

    name: str
    path: Path
    mode: str = "personal"      # display-only metadata (v0.6.39+: no policy branches)
    owner: str = "user"
    created: str = ""
    description: str = ""
    default: bool = False
    allow_tier1_leak: bool = False   # v0.6.39+: opt-in for Tier 1 doc customization
    features: tuple = ()             # v0.6.39+: feature flags (e.g., {"llm_wiki": True})
    agents: tuple = ()               # v0.7.37+: opt-in write allowlist (empty = allow all)
    workspace_path: str = ""         # associated local project workspace path

    @classmethod
    def from_json(cls, name: str, data: dict, default_name: str = "") -> "VaultMeta":
        path = Path(data["path"]).expanduser().resolve()
        # v0.7.23+ fallback: if path doesn't exist, try resolving relative to VAULTS_ROOT()
        if not path.exists():
            fallback_path = (VAULTS_ROOT() / name).resolve()
            if fallback_path.exists():
                path = fallback_path

        features = tuple(sorted(data.get("features", {}).items()))
        # v0.7.37+: agents is opt-in allowlist. Normalize to a sorted tuple
        # so the dataclass stays hashable/frozen. Empty stays empty (= no
        # policy = write allowed for every actor).
        agents_raw = data.get("agents", [])
        if isinstance(agents_raw, (list, tuple)):
            agents: tuple = tuple(sorted(str(a) for a in agents_raw))
        else:
            agents = ()
        return cls(
            name=name,
            path=path,
            mode=data.get("mode", "personal"),
            owner=data.get("owner", "user"),
            created=data.get("created", ""),
            description=data.get("description", ""),
            default=(name == default_name) or data.get("default", False),
            allow_tier1_leak=data.get("allow_tier1_leak", False),
            features=features,
            agents=agents,
            workspace_path=data.get("workspace_path", ""),
        )

    def to_json(self) -> dict[str, Any]:
        out = {
            "path": str(self.path),
            "mode": self.mode,
            "owner": self.owner,
        }
        if self.created:
            out["created"] = self.created
        if self.description:
            out["description"] = self.description
        if self.allow_tier1_leak:
            out["allow_tier1_leak"] = True
        if self.features:
            out["features"] = dict(self.features)
        # v0.7.37+: only serialize agents when non-empty (opt-in surface).
        if self.agents:
            out["agents"] = list(self.agents)
        if self.workspace_path:
            out["workspace_path"] = self.workspace_path
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
        vaults_data = self._data.get("vaults", {})
        out = []
        dirty = False
        for name, data in list(vaults_data.items()):
            meta = VaultMeta.from_json(name, data, default)
            # v0.7.121+: 자가치유 (Self-heal)
            # .registry.json의 저장 경로가 존재하지 않아 fallback 경로로 정상 복구된 경우,
            # .registry.json 파일에 복구된 실제 물리 경로를 자동으로 덮어써준다.
            saved_path_str = data.get("path", "")
            if saved_path_str:
                try:
                    resolved_saved = Path(saved_path_str).expanduser().resolve()
                    if str(meta.path) != str(resolved_saved) and meta.path.exists():
                        self._data["vaults"][name]["path"] = str(meta.path)
                        dirty = True
                except Exception:
                    pass
            out.append(meta)
        if dirty:
            self._save()
        return out

    def get(self, name: str) -> Optional[VaultMeta]:
        data = self._data.get("vaults", {}).get(name)
        if not data:
            return None
        meta = VaultMeta.from_json(name, data, self._data.get("default", ""))
        
        # v0.7.121+: 자가치유 (Self-heal)
        saved_path_str = data.get("path", "")
        if saved_path_str:
            try:
                resolved_saved = Path(saved_path_str).expanduser().resolve()
                if str(meta.path) != str(resolved_saved) and meta.path.exists():
                    self._data["vaults"][name]["path"] = str(meta.path)
                    self._save()
            except Exception:
                pass
        return meta

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

    def update_path(self, name: str, new_path: Path) -> bool:
        """Repair a vault's registered path without touching any files.

        Use when `.registry.json` points at a path that no longer resolves
        in the current runtime (e.g. after a host/container path mismatch).
        Registry-only — never moves, copies, or deletes vault data.
        """
        vaults = self._data.get("vaults", {})
        if name not in vaults:
            return False
        vaults[name]["path"] = str(new_path)
        self._save()
        return True

    def update_workspace_path(self, name: str, workspace_path: str) -> bool:
        """Update workspace_path for a registered vault in the registry and its .vault.json."""
        vaults = self._data.get("vaults", {})
        if name not in vaults:
            return False
        if workspace_path:
            vaults[name]["workspace_path"] = str(Path(workspace_path).expanduser().resolve())
        else:
            vaults[name].pop("workspace_path", None)
        self._save()

        # Also update the vault's own .vault.json if accessible
        try:
            vault_meta = VaultMeta.from_json(name, vaults[name], self._data.get("default", ""))
            vault_dir = vault_meta.path
            vjson = vault_dir / ".vault.json"
            if vjson.exists():
                vjson.write_text(json.dumps(vault_meta.to_json(), indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass

        return True


# ─────────────── module-level singleton ───────────────


def registry() -> VaultRegistry:
    """Lazy singleton — re-reads env on every call."""
    return VaultRegistry()
