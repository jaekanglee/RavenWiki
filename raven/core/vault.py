"""vault — single-vault handle.

A vault is any folder on disk containing:
    .vault.json    — metadata (name, mode, owner, created, description)
    content/       — user markdown (Obsidian-style hierarchy)
    _meta/         — system markdown (SCHEMA, RULES, scripts)
    _archive/      — archived pages (gitignored — see archive.py)
    wiki.db        — sqlite index (build artifact, gitignored)

The CLI resolves the *active* vault via:
  1. `--vault NAME` flag (explicit override)
  2. `WIKI_VAULT` env var
  3. registry's `default` vault
"""
from __future__ import annotations

import datetime as _dt
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
    def create(
        cls,
        name: str,
        path: Path,
        mode: str = "personal",
        owner: str = "user",
        description: str = "",
        *,
        bootstrap: bool = True,
    ) -> "Vault":
        """Create a new vault on disk and register it.

        Args:
            name, path, mode, owner, description: standard vault meta.
            bootstrap: if True (default), create content/ + _meta/ and copy
                SCHEMA.md / RULES.md templates into _meta/. Use False when
                registering an existing folder that already has content.
        """
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
        if bootstrap:
            cls._bootstrap(path)
        else:
            # Even without bootstrap, content/ + _meta/ should exist as empty dirs
            # so users have a writable starting point. (v0.4 fix — discovered via clone test)
            (path / "content").mkdir(parents=True, exist_ok=True)
            (path / "_meta").mkdir(parents=True, exist_ok=True)
        # register
        registry().add(meta)
        return cls(meta=meta, root=path)

    @classmethod
    def _bootstrap(cls, path: Path) -> None:
        """Create content/, _meta/system/, _meta/agent/, and copy templates.

        Idempotent: existing files are NOT overwritten. To refresh templates,
        use `raven meta sync`.

        Structure created:
            _meta/system/{SCHEMA,RULES,OPERATIONS}.md
            _meta/agent/{README,TOOLS,WORKFLOW,SAFETY}.md
            log.md, raven-policy.md  (vault root)
        """
        from importlib import resources

        content_dir = path / "content"
        meta_dir = path / "_meta"
        system_dir = meta_dir / "system"
        agent_dir = meta_dir / "agent"

        content_dir.mkdir(parents=True, exist_ok=True)
        meta_dir.mkdir(parents=True, exist_ok=True)
        system_dir.mkdir(parents=True, exist_ok=True)
        agent_dir.mkdir(parents=True, exist_ok=True)

        # _meta/system/: SCHEMA, RULES, OPERATIONS
        for filename in ("SCHEMA.md", "RULES.md", "OPERATIONS.md"):
            target = system_dir / filename
            if target.exists():
                continue  # never overwrite user-edited files
            try:
                src = resources.files("raven.core").joinpath(f"templates/system/{filename}")
                target.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
            except Exception:
                pass

        # _meta/agent/: README, TOOLS, WORKFLOW, SAFETY
        for filename in ("README.md", "TOOLS.md", "WORKFLOW.md", "SAFETY.md"):
            target = agent_dir / filename
            if target.exists():
                continue  # never overwrite user-edited files
            try:
                src = resources.files("raven.core").joinpath(f"templates/agent/{filename}")
                target.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
            except Exception:
                pass

        # vault 루트: log.md (카파시 가이드), raven-policy.md
        for filename in ("log.md", "raven-policy.md"):
            target = path / filename
            if target.exists():
                continue
            try:
                src = resources.files("raven.core").joinpath(f"templates/{filename}")
                target.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
            except Exception:
                pass

    def sync_meta(self, with_log: bool = False) -> dict:
        """Re-copy system/* and agent/* templates (overwrites).

        Args:
            with_log: if True, also copy log.md (template) and raven-policy.md
                      to the vault root. Default False to honor 카파시 가이드
                      ("don't modify existing data without explicit user action").

        Returns dict with counts of copied/skipped files.
        Use this after raven upgrade to refresh meta docs.
        Creates _meta/system/ and _meta/agent/ if missing (idempotent).
        """
        from importlib import resources

        system_dir = self.meta_root / "system"
        agent_dir = self.meta_root / "agent"
        system_dir.mkdir(parents=True, exist_ok=True)
        agent_dir.mkdir(parents=True, exist_ok=True)

        out = {"copied": [], "errors": []}

        # _meta/system/: SCHEMA, RULES, OPERATIONS (항상 overwrite)
        for filename in ("SCHEMA.md", "RULES.md", "OPERATIONS.md"):
            target = system_dir / filename
            try:
                src = resources.files("raven.core").joinpath(f"templates/system/{filename}")
                target.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
                out["copied"].append(str(target.relative_to(self.root)))
            except Exception as e:
                out["errors"].append({"file": f"system/{filename}", "error": str(e)})

        # _meta/agent/: README, TOOLS, WORKFLOW, SAFETY (항상 overwrite)
        for filename in ("README.md", "TOOLS.md", "WORKFLOW.md", "SAFETY.md"):
            target = agent_dir / filename
            try:
                src = resources.files("raven.core").joinpath(f"templates/agent/{filename}")
                target.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
                out["copied"].append(str(target.relative_to(self.root)))
            except Exception as e:
                out["errors"].append({"file": f"agent/{filename}", "error": str(e)})

        # vault 루트: log.md + raven-policy.md (with_log=True 일 때만)
        if with_log:
            for filename in ("log.md", "raven-policy.md"):
                target = self.root / filename
                if target.exists():
                    # 이미 있으면 덮어쓰지 않음 (사용자 데이터 보호)
                    out["errors"].append({
                        "file": filename,
                        "error": f"exists at {target}, not overwritten (delete manually if you want refresh)",
                    })
                    continue
                try:
                    src = resources.files("raven.core").joinpath(f"templates/{filename}")
                    target.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
                    out["copied"].append(str(target.relative_to(self.root)))
                except Exception as e:
                    out["errors"].append({"file": filename, "error": str(e)})
        return out

    @classmethod
    def clone(
        cls,
        src: "Vault",
        name: str,
        path: Path,
        *,
        mode: Optional[str] = None,
        owner: Optional[str] = None,
        description: str = "",
        copy_meta: bool = True,
    ) -> "Vault":
        """Create a new vault by copying `src`'s content + meta to `path`.

        Args:
            src: source Vault instance.
            name: new vault name (must not already be registered).
            path: absolute path for new vault directory.
            mode, owner, description: optional overrides (default: copy from src).
            copy_meta: if True, copy _meta/ from src too. If False, leave _meta/ empty
                       (caller can run `raven meta sync` afterwards).

        Returns:
            New Vault instance (already registered in the registry).

        Copies:
            content/  — all user markdown (1:1)
            _meta/    — system docs (only if copy_meta=True)

        Skips:
            _archive/ — not transferred (it's transient)
            wiki.db   — regenerated on first build

        Raises:
            FileExistsError: if name is already in registry, or path has files.
            ValueError: if src.path equals path.
        """
        from .registry import registry as _registry

        if name in [m.name for m in _registry().list()]:
            raise FileExistsError(f"vault {name!r} already registered")
        new_path = Path(path).expanduser().resolve()
        if new_path == src.root.resolve():
            raise ValueError(f"clone target cannot be same as src: {src.root}")
        if new_path.exists() and any(new_path.iterdir()):
            raise FileExistsError(f"target path not empty: {new_path}")
        new_path.mkdir(parents=True, exist_ok=True)

        import shutil
        # content/ 1:1
        src_content = src.root / "content"
        if src_content.exists():
            shutil.copytree(src_content, new_path / "content")
        else:
            (new_path / "content").mkdir(exist_ok=True)

        # _meta/ optional copy
        if copy_meta and (src.root / "_meta").exists():
            shutil.copytree(src.root / "_meta", new_path / "_meta")
        else:
            (new_path / "_meta").mkdir(exist_ok=True)

        # write .vault.json with overrides
        meta = VaultMeta(
            name=name,
            path=new_path,
            mode=mode if mode is not None else src.meta.mode,
            owner=owner if owner is not None else src.meta.owner,
            created=_dt.date.today().isoformat(),
            description=description,
        )
        import json
        (new_path / ".vault.json").write_text(
            json.dumps(meta.to_json(), indent=2, ensure_ascii=False)
        )
        _registry().add(meta)
        return cls(meta=meta, root=new_path)

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
        # log.md 자동 보장 (없으면 템플릿에서)
        from . import log as _log
        _log.ensure_log(self)


# Re-export datetime at module scope (used by clone)
_dt = __import__("datetime")


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
            "  raven vault create <name> <path>"
        )
    return Vault.load(default)
