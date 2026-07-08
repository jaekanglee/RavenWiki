"""vault — single-vault handle.

A vault is any folder on disk containing:
    .vault.json    — metadata (name, mode, owner, created, description)
    content/       — user markdown (Obsidian-style hierarchy)
    _meta/         — system markdown and optional agent-facing workflow guides
    _archive/      — archived pages (gitignored — see archive.py)
    wiki.db        — sqlite index (build artifact, gitignored)

The CLI resolves the *active* vault via:
  1. `--vault NAME` flag (explicit override)
  2. `WIKI_VAULT` env var
  3. registry's `default` vault

Tier boundary policy (v2026-06-26, 2-tier model):
    Tier 1 = raven package (this codebase) — owns its own docs, build, lint
    Tier 2 = user vault (~/Raven/<name>/ by default) — user runtime data, NEVER receives
             raven-internal operational docs (OPERATIONS.md, agent/*, raven-policy.md).
    Lite bootstrap policy: vault create() only copies user-facing essentials.
    To read raven-internal docs, use `raven docs`.
"""
from __future__ import annotations

import datetime as _dt
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from .registry import registry, VaultMeta

if TYPE_CHECKING:
    from .verify import BootstrapVerifyResult


# Lite bootstrap whitelist — agent-facing operational essentials only.
# v0.7.65+: 3 entries — must match template_map in _bootstrap_lite().
_LITE_BOOTSTRAP_FILES = (
    "_meta/agents/SCHEMA.md",
    "_meta/agents/PROJECT-WORKFLOW.md",
    "_meta/agents/CURATION.md",
    "log.md",
)

# v0.6.38+: basic profile whitelist — human-first Obsidian-style vault.
# Only WELCOME.md (1 file) — no schema/rules/agents forced on the user.
# LLM Wiki patterns are opt-in via _meta/system/features.json.
_BASIC_BOOTSTRAP_FILES = (
    "WELCOME.md",
)


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
        
        # v0.7.121+: 자가치유 (Self-heal)
        # 만약 .vault.json 파일이 존재하고, 그 안의 path 필드가 현재의 root 경로와 다르다면
        # 실제 현재 로컬 경로로 .vault.json 파일을 자동 갱신해준다.
        vjson = root / ".vault.json"
        if vjson.exists():
            try:
                import json
                data = json.loads(vjson.read_text(encoding="utf-8"))
                saved_path = data.get("path")
                if saved_path and str(root.resolve()) != str(Path(saved_path).expanduser().resolve()):
                    data["path"] = str(root.resolve())
                    vjson.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
            except Exception:
                pass

        # v0.7.34+: 자동 마이그레이션 실드 (AGENTS.md -> README.md)
        old_path = root / "_meta" / "system" / "AGENTS.md"
        new_path = root / "_meta" / "system" / "README.md"
        if old_path.exists() and not new_path.exists():
            try:
                old_path.rename(new_path)
            except Exception as e:
                print(f"⚠️  Failed to migrate AGENTS.md to README.md: {e}")

        return cls(meta=meta, root=root)

    @property
    def is_llm_wiki(self) -> bool:
        """Check if LLM Wiki patterns are enabled for this vault."""
        if hasattr(self.meta, "features") and dict(self.meta.features).get("llm_wiki") is True:
            return True
        vf = self.root / ".vault.json"
        if vf.exists():
            try:
                import json
                data = json.loads(vf.read_text(encoding="utf-8"))
                if data.get("features", {}).get("llm_wiki") is True:
                    return True
            except Exception:
                pass
        # Structural opt-in: agent workflow docs indicate the user
        # intentionally enabled the LLM Wiki layer. `raw/` and `log.md` are
        # excluded because some non-wiki flows may still create them.
        if (self.root / "_meta" / "agents").exists():
            return True
        return False

    # ────────────────────────── v0.7.37+: agents policy ─────────────────────
    #
    # When `.vault.json` lists an `agents` allowlist, ONLY callers whose
    # actor string (or dict `.name`) appears in that list may write to
    # this vault. Empty list = permissive (every actor allowed) — full
    # backward compatibility with vaults that haven't opted in.
    #
    # Reads (`search`, `get_page`, `graph`, `lint`, `log`, MCP read
    # tools) are NEVER gated here; the policy is write-only by design.
    # Doing it this way keeps federation / cross-vault wikilinks free
    # while preventing rogue actors from silently mutating another
    # vault's content.

    def write_allowed_for(self, actor: Optional[object]) -> bool:
        """Return True if `actor` may write to this vault under the
        `agents` opt-in policy.

        Args:
            actor: One of:
                * None — anonymous caller (treated as `"anonymous"`).
                * str — actor identifier (e.g. `"hermes"`, `"wiki-agent"`).
                * dict — must carry `"name"` (used as actor id).
                * any object with `.name` attribute — used as actor id.

        Returns:
            True if `actor` may write. False ONLY when the vault has an
            opt-in allowlist (`meta.agents` non-empty) AND the actor id
            is not in that list. Otherwise True (default).
        """
        allowlist = self.meta.agents
        if not allowlist:
            # No policy declared → allow every actor (current behavior).
            return True

        # Normalize actor → str
        if actor is None:
            actor_id = "anonymous"
        elif isinstance(actor, str):
            actor_id = actor
        elif isinstance(actor, dict):
            actor_id = str(actor.get("name", "anonymous"))
        else:
            name = getattr(actor, "name", None)
            actor_id = str(name) if name else "anonymous"

        return actor_id in allowlist

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
        profile: str = "llm-wiki",
        workspace_path: str = "",
    ) -> "Vault":
        """Create a new vault on disk and register it.

        Args:
            name, path, mode, owner, description: standard vault meta.
            bootstrap: if True (default), apply the profile bootstrap.
                Use False when registering an existing folder.
            profile: v0.6.38+ bootstrap profile selector. Default is "llm-wiki".
                - "llm-wiki" (default): project/agent-ready vault. Copies 2-file
                  Lite bootstrap (SCHEMA + PROJECT-WORKFLOW) + log.md.
                - "basic": Obsidian-style human-first vault. Only copies
                  WELCOME.md (1 file). No SCHEMA/RULES/agent workflow — user
                  opts in later if they want LLM Wiki patterns.
            workspace_path: associated local project workspace path.
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
            workspace_path=workspace_path,
        )
        # write per-vault meta
        (path / ".vault.json").write_text(json.dumps(meta.to_json(), indent=2, ensure_ascii=False))
        if bootstrap:
            if profile == "basic":
                cls._bootstrap_basic(path)
            else:
                cls._bootstrap_lite(path)
            # M4 F3 — Bootstrap Self-Test (read-back verification).
            # Lite bootstrap = user-facing files. README.md §9 silent-failure policy:
            # verify failure emits a warning, write itself succeeds.
            try:
                from . import verify as _verify
                _verify.verify_and_warn(path, context=f"vault.create({name}, profile={profile})")
            except Exception:
                # Verify must never break vault create (defensive).
                pass
        else:
            # Even without bootstrap, content/ + _meta/ should exist as empty dirs
            # so users have a writable starting point. (v0.4 fix — discovered via clone test)
            (path / "content").mkdir(parents=True, exist_ok=True)
            (path / "_meta").mkdir(parents=True, exist_ok=True)
        # register
        registry().add(meta)

        # log.md에 create entry 자동 append (silent write 방지, README.md §8/§9).
        # ensure_log()가 log.md 부재 시 템플릿에서 1회 생성 → 첫 vault create 안전.
        # log append 실패는 무시 — vault create 자체는 성공 유지 (db.py와 동일 패턴).
        # v0.6.38+: basic profile은 log.md 없음 → log append skip.
        instance = cls(meta=meta, root=path)
        if profile != "basic":
            try:
                from . import log as _log
                _log.ensure_log(instance)
                _log.append(
                    instance,
                    action="create",
                    subject=f"vault created (mode={mode}, profile={profile})",
                    files=[".vault.json"],
                    note=f"path={path}",
                )
            except Exception:
                pass

        # git init + initial commit — SCHEMA.md declares markdown as the
        # vault's SoT "tracked by git"; make that true from vault creation
        # onward instead of leaving it as an unmet doc promise. Best-effort:
        # missing git binary or init failure must never break vault create.
        cls._ensure_git_repo(path)

        return instance

    @staticmethod
    def _ensure_git_repo(path: Path) -> None:
        """Best-effort `git init` + initial commit for a freshly created vault."""
        import shutil
        import subprocess

        if (path / ".git").exists() or shutil.which("git") is None:
            return
        gitignore = path / ".gitignore"
        if not gitignore.exists():
            # SCHEMA.md: wiki.db is the query index, explicitly gitignored.
            gitignore.write_text("wiki.db\n", encoding="utf-8")
        try:
            run = lambda *args: subprocess.run(
                ["git", *args], cwd=path, check=True, capture_output=True, text=True
            )
            run("init", "-q")
            run("config", "user.email", "raven@local")
            run("config", "user.name", "raven")
            run("add", "-A")
            run("commit", "-q", "-m", "chore: initial vault bootstrap")
        except Exception:
            pass

    @classmethod
    def _bootstrap_basic(cls, path: Path) -> None:
        """v0.6.38+ basic profile bootstrap.

        Obsidian-style human-first vault. Only copies WELCOME.md (1 file).
        User decides if/when to enable LLM Wiki patterns via
        _meta/system/features.json (opt-in, never forced).

        Creates:
            content/                     (empty)
            _meta/                       (empty)
            WELCOME.md                   (human-friendly welcome guide)

        Does NOT copy:
            SCHEMA.md, PROJECT-WORKFLOW.md, log.md
            → user enables LLM Wiki patterns manually if desired
        """
        from importlib import resources

        content_dir = path / "content"
        meta_dir = path / "_meta"

        content_dir.mkdir(parents=True, exist_ok=True)
        meta_dir.mkdir(parents=True, exist_ok=True)

        # Copy WELCOME.md to vault root (visible immediately)
        template_map = {
            "WELCOME.md": "templates/system/WELCOME.md",
        }

        for rel_target, tmpl_path in template_map.items():
            target = path / rel_target
            if target.exists():
                continue  # never overwrite user-edited files
            try:
                src = resources.files("raven.core").joinpath(tmpl_path)
                target.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
            except Exception as e:
                raise RuntimeError(
                    f"Basic bootstrap failed: could not copy {rel_target} "
                    f"from {tmpl_path}: {e}"
                ) from e

    @classmethod
    def _bootstrap_lite(cls, path: Path) -> None:
        """Lite bootstrap (v0.7.65+: agent-only 2-file set): copy ONLY the
        agent-facing operational essentials.

        Creates:
            content/                          (empty)
            _meta/agents/SCHEMA.md            (데이터 계약: frontmatter/type/tag/wikilink/raw 권한/lint)
            _meta/agents/PROJECT-WORKFLOW.md  (운영 사실: 읽기순서/MCP매핑/권한/저장신호/협업규칙)
            log.md                            (빈 로그 헤더)

        Does NOT copy:
            OPERATIONS.md  → raven internal docs, use `raven docs operations`
            agent/*        → raven LLM agent behavior, use `raven docs agent`
            raven-policy.md → raven internal policy, use `raven docs policy`

        v0.7.65+: dropped `_meta/system/{SCHEMA,RULES,README}.md` — merged into
        the 2 files above. No human-manual content is injected into the vault;
        only facts an agent needs to operate this vault/tool correctly.

        Idempotent: existing files are NOT overwritten. To refresh templates
        after raven upgrade, use `raven meta sync --lite`.
        """
        from importlib import resources

        content_dir = path / "content"
        meta_dir = path / "_meta"
        agents_dir = meta_dir / "agents"

        content_dir.mkdir(parents=True, exist_ok=True)
        meta_dir.mkdir(parents=True, exist_ok=True)
        agents_dir.mkdir(parents=True, exist_ok=True)

        # Map: target relative path → template resource path
        template_map = {
            "_meta/agents/SCHEMA.md":            "templates/agent/SCHEMA.md",
            "_meta/agents/PROJECT-WORKFLOW.md":  "templates/agent/PROJECT-WORKFLOW.md",
            "_meta/agents/CURATION.md":          "templates/agent/CURATION.md",
            "log.md":                            "templates/log.md",
        }

        for rel_target, tmpl_path in template_map.items():
            target = path / rel_target
            if target.exists():
                continue  # never overwrite user-edited files
            try:
                src = resources.files("raven.core").joinpath(tmpl_path)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
            except Exception as e:
                # Loud, not silent — caller (CLI) will surface this.
                raise RuntimeError(
                    f"Lite bootstrap failed: could not copy {rel_target} "
                    f"from {tmpl_path}: {e}"
                ) from e

    def sync_meta(self, *, lite: bool = True, force: bool = False) -> dict:
        """Re-copy meta templates into the vault.

        Args:
            lite: if True (default), copy the 2-file agent-facing set
                  (SCHEMA.md, PROJECT-WORKFLOW.md) + log.md. If False
                  ("full"), copies the identical set — v0.7.65+ removed
                  the old superset that injected Tier 1 internal docs
                  (OPERATIONS, agent/*, raven-policy), since that has
                  been banned since v0.7.1 (Tier 1 ↔ Tier 2 boundary).
                  The only behavioral difference for lite=False is the
                  safety check below.
            force: if False (default), do not overwrite existing files
                   (user-edited protection). If True, overwrite.

        Returns dict with counts of copied/skipped files.

        Raises:
            ValueError: if lite=False and force=False and any target file
                        already exists — safety check protecting
                        user-edited files on the explicit non-lite path.
        """
        from importlib import resources

        # Determine target files based on lite flag
        # v0.7.65+: lite and full are now identical (2-file agent-only set) —
        # `full` no longer adds Tier 1 internal docs (that policy predates
        # v0.7.1's Tier 1 leak ban and was already dead code).
        file_map = {
            "_meta/agents/SCHEMA.md":            "templates/agent/SCHEMA.md",
            "_meta/agents/PROJECT-WORKFLOW.md":  "templates/agent/PROJECT-WORKFLOW.md",
            "_meta/agents/CURATION.md":          "templates/agent/CURATION.md",
            "log.md":                            "templates/log.md",
        }
        if not lite and not force:
            # Safety: full set without force could overwrite user-edited files.
            for rel_target in file_map:
                target = self.root / rel_target
                if target.exists():
                    raise ValueError(
                        f"sync_meta(full): target exists at {target}. "
                        f"Refusing to overwrite without force=True. "
                        f"This protects user-edited raven-internal docs."
                    )

        agents_dir = self.meta_root / "agents"
        agents_dir.mkdir(parents=True, exist_ok=True)

        out = {"copied": [], "skipped": [], "errors": []}

        for rel_target, tmpl_path in file_map.items():
            target = self.root / rel_target
            if target.exists() and not force:
                out["skipped"].append(str(target.relative_to(self.root)))
                continue
            try:
                src = resources.files("raven.core").joinpath(tmpl_path)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
                out["copied"].append(str(target.relative_to(self.root)))
            except Exception as e:
                out["errors"].append({"file": rel_target, "error": str(e)})
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
        copy_meta: bool = False,
        data_only: bool = False,
    ) -> "Vault":
        """Create a new vault by copying `src`'s content to `path`.

        Args:
            src: source Vault instance.
            name: new vault name (must not already be registered).
            path: absolute path for new vault directory.
            mode, owner, description: optional overrides (default: copy from src).
            copy_meta: if False (default, v2026-06-26 Lite policy), do NOT copy
                       src's _meta/. If True, copy _meta/ from src.
                       NOTE: copy_meta=True can leak Tier 1 raven-internal docs
                       from source vault (OPERATIONS, agent/*, raven-policy).
                       Use only for explicit dev/debug workflows.
            data_only: if True, copy ONLY content/ (no _meta/, no .vault.json
                       policy inheritance). Use for data migration / backup
                       where you don't want source vault's policy semantics
                       to leak into the new vault. Mutually exclusive with
                       copy_meta=True (data_only wins).

        Returns:
            New Vault instance (already registered in the registry).

        Copies:
            content/  — all user markdown (1:1) [always]
            _meta/    — system docs (only if copy_meta=True AND not data_only)

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
        # content/ 1:1 (always)
        src_content = src.root / "content"
        if src_content.exists():
            shutil.copytree(src_content, new_path / "content")
        else:
            (new_path / "content").mkdir(exist_ok=True)

        # _meta/ optional copy (only if copy_meta=True AND not data_only)
        copy_meta = copy_meta and not data_only
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
        # log.md 자동 보장 (없으면 빈 헤더)
        from . import log as _log
        _log.ensure_log(self)

    # ─── bootstrap self-test (F3, M4) ────────────

    def verify_bootstrap(self) -> "BootstrapVerifyResult":
        """Verify this vault's Lite bootstrap files match the source templates.

        Returns:
            BootstrapVerifyResult with per-file status + overall `ok` flag.

        Use case:
            - CLI: `raven vault verify <name>`
            - API: `POST /api/vaults/{name}/verify`
            - Direct: `Vault.load(meta).verify_bootstrap()`

        Does NOT raise on missing/mismatched files — caller inspects `result.ok`.
        """
        from . import verify as _verify
        return _verify.verify_bootstrap(self.root)


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
