"""agent.py — the Agent adapter.

An Agent is a named worker (e.g. "hermes-writer", "codex-codegen") bound to
one or more vaults by an explicit scope. Agents never read or write outside
their scope — that's the whole point of the adapter layer.

Three layers:
    Agent       — identity + scope config (who am I, what can I touch)
    AgentVault  — vault-bound operations (the actual API surface agents call)
    Result      — typed return values (so agents don't have to parse strings)

This module is intentionally dependency-free at the top level: only
wikisys.core (vault/db/lint/link) is used. No HTTP, no shell, no CLI.
"""
from __future__ import annotations

import datetime as _dt
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Optional, Union

from wikisys.core import resolve_active_vault, registry, link_module
from wikisys.core import slug_module, frontmatter_module
from wikisys.core.vault import Vault


# ────────────────────────── data types ──────────────────────────


@dataclass(frozen=True)
class AgentScope:
    """What an Agent is allowed to touch.

    Either a list of vault names, or `"<active>"` to bind to whatever vault
    is currently active at call time (useful for interactive agents).
    """
    vault_names: tuple[str, ...] = ()
    allow_create: bool = True
    allow_delete: bool = False       # default: agents can't delete
    default_type: str = "concept"
    default_tags: tuple[str, ...] = ("agent-output",)

    @classmethod
    def single(cls, name: str, **kw) -> "AgentScope":
        return cls(vault_names=(name,), **kw)

    def allows(self, vault_name: str) -> bool:
        return vault_name in self.vault_names


@dataclass(frozen=True)
class Provenance:
    """Who wrote this and when. Embedded in frontmatter as `agents:`."""
    agent_name: str
    run_id: str = ""
    timestamp: str = ""
    intent: str = ""

    def __post_init__(self):
        if not self.timestamp:
            object.__setattr__(self, "timestamp", _dt.datetime.now().isoformat(timespec="seconds"))


@dataclass
class Result:
    """Typed return for write operations. Always include `ok: bool`."""
    ok: bool
    slug: Optional[str] = None
    path: Optional[str] = None
    bytes_written: int = 0
    message: str = ""
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "slug": self.slug,
            "path": self.path,
            "bytes_written": self.bytes_written,
            "message": self.message,
            "error": self.error,
        }


# ────────────────────────── Agent ──────────────────────────


@dataclass
class Agent:
    """A named worker with a fixed scope. Build via `Agent.named(...)`."""

    name: str
    scope: AgentScope
    provenance: Provenance = field(default_factory=lambda: Provenance("unnamed"))

    @classmethod
    def named(
        cls,
        name: str,
        scope: Union[str, AgentScope, None] = None,
        run_id: str = "",
        intent: str = "",
    ) -> "Agent":
        """Convenience constructor.

        Examples:
            Agent.named("hermes-writer", scope="agent-output")
            Agent.named("codex-codegen",  scope=AgentScope.single("sandbox"))
            Agent.named("hermes-writer")   # active vault
        """
        if scope is None or scope == "<active>":
            scope_obj = AgentScope(vault_names=("<active>",))
        elif isinstance(scope, str):
            scope_obj = AgentScope.single(scope)
        elif isinstance(scope, AgentScope):
            scope_obj = scope
        else:
            raise TypeError(f"scope must be str or AgentScope, got {type(scope)}")
        prov = Provenance(agent_name=name, run_id=run_id, intent=intent)
        return cls(name=name, scope=scope_obj, provenance=prov)

    # ─── vault resolution ──────────────────────

    def vault(self, name: Optional[str] = None) -> "AgentVault":
        """Bind to a vault. Resolves scope at call time."""
        if name:
            if not self.scope.allows(name):
                raise PermissionError(f"agent {self.name!r} not allowed in vault {name!r}")
            v = registry().get(name)
            if v is None:
                raise ValueError(f"vault {name!r} not in registry")
            return AgentVault(agent=self, vault=Vault.load(v))
        # active vault mode
        if "<active>" not in self.scope.vault_names:
            raise PermissionError(f"agent {self.name!r} requires explicit vault name (no <active> in scope)")
        active = resolve_active_vault()
        if not self.scope.allows(active.meta.name) and not self.scope.allows("<active>"):
            raise PermissionError(f"agent {self.name!r} not allowed in vault {active.meta.name!r}")
        return AgentVault(agent=self, vault=active)


# ────────────────────────── AgentVault ──────────────────────────


@dataclass
class AgentVault:
    """The API surface an Agent sees for one vault.

    Methods:
        write(slug, content, *, title=None, type=None, tags=None)
        read(slug) -> Optional[str]
        exists(slug) -> bool
        list(*, type=None, tag=None) -> list[dict]
        search(query, *, top_k=10) -> list[dict]
        delete(slug) -> Result   (only if scope.allow_delete)
    """
    agent: Agent
    vault: Vault

    # ─── path helpers ──────────────────────

    def _path(self, slug: str) -> Path:
        return self.vault.root / f"{slug}.md"

    def _safe_path(self, slug: str) -> Path:
        """Validate slug against vault root; return absolute .md path.

        v0.3+: shared slug safety with CLI/API. Raises slug_module.SlugError
        on bad input (caller decides whether to swallow as Result or raise).
        """
        return slug_module.validate(slug, vault_root=self.vault.root).with_suffix(".md")

    # ─── frontmatter helpers ─────────────────

    @staticmethod
    def _split_frontmatter(text: str) -> tuple[dict, str]:
        """v0.3.2: thin wrapper kept for back-compat. Delegates to fm_module."""
        return frontmatter_module.parse(text)

    def _render(self, meta: dict, body: str) -> str:
        """v0.3.2: delegates to frontmatter.render() with agents provenance."""
        return frontmatter_module.render(
            meta,
            body,
            agents=[{
                "name": self.agent.provenance.agent_name,
                "timestamp": self.agent.provenance.timestamp,
                "run_id": self.agent.provenance.run_id,
                "intent": self.agent.provenance.intent,
            }],
        )

    # ─── write ──────────────────────

    def write(
        self,
        slug: str,
        content: str,
        *,
        title: Optional[str] = None,
        type: Optional[str] = None,
        tags: Optional[Iterable[str]] = None,
    ) -> Result:
        """Create or overwrite a page. Adds/updates `agents:` provenance.

        v0.3+:
            - slug is validated (same rules as CLI/API)
            - 'created' preserved on overwrite (via frontmatter.merge)
        """
        # v0.3+: validate slug (raises SlugError on bad path)
        try:
            fp = self._safe_path(slug)
        except slug_module.SlugError as e:
            return Result(ok=False, slug=slug, error=f"invalid slug: {e}")

        fp.parent.mkdir(parents=True, exist_ok=True)

        today = _dt.date.today().isoformat()
        # Use fm_module.parse for existing meta (handles nested agents block gracefully)
        existing_text = fp.read_text(encoding="utf-8") if fp.exists() else ""
        existing_meta, _ = frontmatter_module.parse(existing_text)

        updates: dict = {
            "title": title if title is not None else existing_meta.get("title") or slug.split("/")[-1],
            "type": type if type is not None else existing_meta.get("type") or self.agent.scope.default_type,
            "tags": list(tags) if tags is not None else (
                existing_meta.get("tags") if isinstance(existing_meta.get("tags"), list)
                else self.agent.scope.default_tags
            ),
        }
        meta = frontmatter_module.merge(existing_meta, updates, today=today)
        rendered = self._render(meta, content)
        fp.write_text(rendered, encoding="utf-8")
        return Result(
            ok=True,
            slug=slug,
            path=str(fp),
            bytes_written=len(rendered),
            message=f"wrote {slug}",
        )

    def read(self, slug: str) -> Optional[str]:
        fp = self._path(slug)
        if not fp.exists():
            return None
        return fp.read_text()

    def exists(self, slug: str) -> bool:
        return self._path(slug).exists()

    def delete(self, slug: str) -> Result:
        if not self.agent.scope.allow_delete:
            return Result(ok=False, error=f"agent {self.agent.name!r} not allowed to delete (scope.allow_delete=False)")
        try:
            fp = self._safe_path(slug)
        except slug_module.SlugError as e:
            return Result(ok=False, slug=slug, error=f"invalid slug: {e}")
        if not fp.exists():
            return Result(ok=False, slug=slug, error="not found")
        # archive instead of hard delete — mirror original path under _archive (v0.3+)
        archive = self.vault.root / "_archive"
        archive.mkdir(exist_ok=True)
        ts = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
        rel = fp.relative_to(self.vault.root)
        dest = archive / rel.parent / f"{rel.stem}-{ts}.md"
        dest.parent.mkdir(parents=True, exist_ok=True)
        fp.rename(dest)
        return Result(ok=True, slug=slug, path=str(dest), message=f"archived to {dest.name}")

    # ─── queries ──────────────────────

    def list(self, *, type: Optional[str] = None, tag: Optional[str] = None) -> list[dict]:
        out = []
        for fp in self.vault.content_root.rglob("*.md"):
            text = fp.read_text(errors="replace")
            meta, _ = self._split_frontmatter(text)
            if type and meta.get("type") != type:
                continue
            if tag and tag not in meta.get("tags", ""):
                continue
            slug = str(fp.relative_to(self.vault.root))[:-3]
            out.append({
                "slug": slug,
                "title": meta.get("title", slug),
                "type": meta.get("type", "?"),
                "updated": meta.get("updated", ""),
            })
        return out

    def search(self, query: str, *, top_k: int = 10) -> list[dict]:
        """Lightweight in-process BM25-ish search.

        Walks content/, scores each page by term frequency, returns top_k.
        No external index — fast enough for vault-sized corpora (<10k pages).
        """
        terms = [t.lower() for t in re.findall(r"\w+", query) if t]
        if not terms:
            return []
        scores: list[tuple[float, dict]] = []
        for fp in self.vault.content_root.rglob("*.md"):
            text = fp.read_text(errors="replace").lower()
            meta, body = self._split_frontmatter(text)
            slug = str(fp.relative_to(self.vault.root))[:-3]
            score = sum(text.count(t) for t in terms)
            if score == 0:
                continue
            scores.append((score, {
                "slug": slug,
                "title": meta.get("title", slug),
                "type": meta.get("type", "?"),
                "score": score,
                "snippet": self._snippet(body, terms),
            }))
        scores.sort(key=lambda x: x[0], reverse=True)
        return [s for _, s in scores[:top_k]]

    @staticmethod
    def _snippet(text: str, terms: list[str], radius: int = 60) -> str:
        text_l = text.lower()
        for t in terms:
            i = text_l.find(t)
            if i >= 0:
                start = max(0, i - radius)
                end = min(len(text), i + radius)
                snippet = text[start:end].replace("\n", " ").strip()
                return ("…" if start > 0 else "") + snippet + ("…" if end < len(text) else "")
        return text[:120].replace("\n", " ").strip()
