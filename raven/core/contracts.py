"""contracts.py — single write contract shared by all entrypoints (v0.6.2+).

Why this module exists
----------------------
v0.5.6 changelog §8 P1-1 promised: "write-path 단일화
(`raven.core.contracts.write_page()` 같은 단일 진입 함수로 모든 write path 통합)".

Before v0.6.2, the same 4-step write recipe was duplicated in 4 places:

  - raven/cli/__main__.py:page_new   (slug validate → FM merge → write → log)
  - raven/api/server.py:create_page  (same recipe + extra HTTP exception types)
  - raven/api/server.py:update_page  (same recipe with `created` preservation)
  - raven/agents/agent.py:AgentVault.write  (same recipe + agent provenance)

That meant every change to the recipe (e.g. add `confidence` field, change
log format, add telemetry) had to be applied in 4 places — and each one
risked drifting out of sync with the others.

After v0.6.2, the recipe lives in `contracts.write_page()`. Each entrypoint
calls it with its own arguments; the entrypoint-specific concerns
(HTTPException types, typer.Exit codes, agent provenance block) stay at
the boundary layer.

Scope (deliberately limited)
----------------------------
- `write_page()` only. `delete_page()` / `rename_page()` are not yet
  unified (archive.py is a richer surface; deferred to v0.6.3).
- MCP `wiki_update` is NOT switched to call this function yet — MCP's
  write path adds lock + idempotency + provenance that other entrypoints
  don't need. Routing MCP through the same function would force every
  entrypoint to plumb those kwargs. Deferred to v0.6.3 (per-arg path).
"""
from __future__ import annotations

import datetime as _dt
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

from . import frontmatter as frontmatter_module
from . import log as log_module
from . import slug as slug_module
from .lock import lock_for_file
from .vault import Vault


# ────────────────────────── result type ────────────────────────────


@dataclass(frozen=True)
class WriteResult:
    """Outcome of a `write_page()` call.

    Attributes mirror the keys the entrypoints previously returned so
    callers can swap implementations without changing their return-handling
    code.

    `slug` is the *normalized* slug (after `slug_module.normalize_prefix`)
    so callers can echo back what was actually written — differs from the
    raw input when a short name like `foo` was auto-prefixed to
    `content/foo`.
    """

    ok: bool
    slug: str
    path: Optional[Path] = None
    bytes_written: int = 0
    created: bool = False  # True = new file, False = overwrite
    created_date: Optional[str] = None  # ISO date string, set on new file
    error: Optional[str] = None
    message: str = ""


# ────────────────────────── write contract ──────────────────────────


def write_page(
    vault: Vault,
    slug: str,
    content: str,
    *,
    title: Optional[str] = None,
    type: Optional[str] = None,
    tags: Optional[Iterable[str]] = None,
    actor: Optional[object] = None,
    overwrite: bool = True,
    normalize: bool = True,
    body: Optional[str] = None,
) -> WriteResult:
    """Create or overwrite a markdown page through the shared write contract.

    Steps (identical to the previous inline recipes):
      1. Normalize + validate slug (`slug_module.normalize_prefix` + `validate`).
         Set `normalize=False` to skip auto-prefix (Agent semantics:
         LLM agents should pass explicit `content/...` paths).
      2. Parse existing frontmatter (if any) for `created` preservation.
      3. Merge updates (title/type/tags/updated) + optional agent provenance.
      4. Render markdown + write file.
      5. Append a `log.md` entry (action="create" or "update").

    Args:
        vault: A loaded `Vault` handle.
        slug: User-supplied slug. Short names are auto-prefixed to
            `content/<name>` (matches CLI/API pre-v0.6.2 behavior) unless
            `normalize=False`.
        content: Markdown body. If `body` is also provided, `content`
            wins (callers may pass either).
        title/type/tags: Frontmatter fields. None means "preserve
            existing" (overwrite) or "use defaults" (create).
        actor: Optional agent identity. When provided, an `agents:` block
            is attached to the frontmatter — same shape AgentVault.write
            produced pre-v0.6.2. Accepts a dict (Agent-style provenance
            with `name`/`run_id`/`intent` keys) or any object with a
            `name` attribute (str fallback). `None` skips provenance.
        overwrite: If False and the target file already exists, returns
            `WriteResult(ok=False, error="exists")` without touching the
            filesystem. Matches CLI/API pre-v0.6.2 "create-only" semantics.
        normalize: If False, skip `slug_module.normalize_prefix` (Agent
            entrypoint semantics — bare `hello` lands at vault root).
        body: Legacy alias for `content`; `content` takes precedence.

    Returns:
        WriteResult — `ok=True` on success, `ok=False` + `error` on
        validation failure (slug error, exists-when-overwrite=False, etc).
    """
    if body is not None and content is None:
        content = body

    # ── 1. slug normalize + validate
    raw_slug = slug if not normalize else slug_module.normalize_prefix(slug)
    try:
        safe_path = slug_module.validate(raw_slug, vault_root=vault.root)
    except slug_module.SlugError as e:
        return WriteResult(ok=False, slug=raw_slug, error=f"invalid slug: {e}")

    fp = safe_path.with_suffix(".md")

    try:
        with lock_for_file(vault.root, fp):
            # ── 2. existence check
            if fp.exists() and not overwrite:
                return WriteResult(ok=False, slug=raw_slug, error="exists")

            # ── 3. parse existing frontmatter (preserve `created`, `agents`)
            existing_meta: dict = {}
            if fp.exists():
                try:
                    existing_text = fp.read_text(encoding="utf-8")
                    existing_meta, _ = frontmatter_module.parse(existing_text)
                except Exception:
                    # Corrupt frontmatter: treat as empty so the write still
                    # succeeds (matches pre-v0.6.2 AgentVault.write behavior).
                    existing_meta = {}

            today = _dt.date.today().isoformat()
            updates: dict = {"updated": today}
            if title is not None:
                updates["title"] = title
            if type is not None:
                updates["type"] = type
            if tags is not None:
                updates["tags"] = list(tags)

            # `created` only set on first write (matches API create_page pre-v0.6.2)
            if "created" not in existing_meta:
                updates["created"] = today

            merged = frontmatter_module.merge(existing_meta, updates, today=today)

            # Strict Schema & WIP guardrail check for agents
            if vault.is_llm_wiki and actor is not None:
                # raw/ 및 _meta/system/ 등 불변(Immutable) 영역에 대한 에이전트 쓰기 원천 차단
                slug_lower = raw_slug.lower()
                if (
                    slug_lower.startswith("raw/") or
                    slug_lower.startswith("content/raw/") or
                    slug_lower.startswith("_meta/system/")
                ):
                    return WriteResult(
                        ok=False,
                        slug=raw_slug,
                        error="permission_denied",
                        message="Raw sources 및 시스템 메타 영역은 불변(Immutable)이므로 에이전트가 수정할 수 없습니다."
                    )

                missing = validate_gardening_schema(vault, raw_slug, content or "", merged)
                if missing:
                    return WriteResult(
                        ok=False,
                        slug=raw_slug,
                        error="strict_schema_violated",
                        message=(
                            "WIP가 아닌 메인 content/ 페이지는 Frontmatter와 규약을 완전히 갖춰야 합니다. "
                            f"누락된 항목: {', '.join(missing)}. "
                            "임시 작업은 content/wip/ 아래에 작성해 주세요."
                        )
                    )

            # Optional agent provenance — matches AgentVault.write pre-v0.6.2 shape.
            # Stored as list-of-dict so frontmatter_module.render serializes it as
            # a YAML list (matches the YAML format pre-v0.6.2 produced).
            if actor is not None:
                provenance_list = list(merged.get("agents") or [])
                if isinstance(actor, dict):
                    entry = dict(actor)
                elif hasattr(actor, "__dict__"):
                    entry = {k: v for k, v in vars(actor).items() if not k.startswith("_")}
                else:
                    entry = {"name": str(actor)}
                if "timestamp" not in entry:
                    entry["timestamp"] = _dt.datetime.now().isoformat()
                provenance_list.append(entry)
                merged["agents"] = provenance_list

            # ── 4. render + write
            # `frontmatter.render` expects `agents` as a separate kwarg (rendered
            # as a YAML list block), not as a meta dict entry (which would be
            # serialized via Python repr).
            agents_list: Optional[list[dict]] = None
            if actor is not None:
                # We've already appended into merged["agents"] above — extract it
                # back out for the dedicated render path.
                agents_list = merged.pop("agents", None)
            rendered = frontmatter_module.render(merged, content or "", agents=agents_list)
            fp.parent.mkdir(parents=True, exist_ok=True)
            fp.write_text(rendered, encoding="utf-8")

            is_create = not existing_meta  # empty parsed meta ⇒ new file

            # ── 5. log.md append (best-effort; matches pre-v0.6.2 try/except wrap)
            try:
                actor_name = ""
                if isinstance(actor, dict):
                    name_val = actor.get("name")
                    if isinstance(name_val, str):
                        actor_name = name_val
                log_module.append(
                    vault,
                    action="create" if is_create else "update",
                    subject=raw_slug,
                    files=[raw_slug],
                    note=f"actor={actor_name}" if actor_name else "",
                )
            except Exception:
                pass
    except TimeoutError as exc:
        return WriteResult(
            ok=False,
            slug=raw_slug,
            error=f"concurrency lock timeout: {exc}",
            message=f"failed to write {raw_slug} due to lock timeout",
        )

    return WriteResult(
        ok=True,
        slug=raw_slug,
        path=fp,
        bytes_written=len(rendered),
        created=is_create,
        created_date=merged.get("created"),
        message=f"wrote {raw_slug}",
    )


def validate_gardening_schema(vault, slug: str, content: str, meta: dict) -> list[str]:
    """Validate that the document has required llm_wiki metadata and sections.
    Returns a list of missing items (empty if valid).
    """
    slug_lower = slug.lower()
    if (
        slug_lower.startswith("content/wip/") or 
        slug_lower.startswith("content/scratch/") or 
        slug_lower.startswith("wip/") or 
        slug_lower.startswith("scratch/") or
        slug_lower.startswith("_meta/")
    ):
        return []

    from raven.core.lint import (
        _has_why_it_matters,
        _has_oppose_heading,
        COG_GOV_CONFIDENCE_LEVELS,
        COG_GOV_EXEMPT_TYPES,
    )
    
    missing = []
    
    # 1. Check type
    ptype = (meta.get("type") or "").strip().lower()
    valid_types = {"concept", "person", "tool", "comparison", "project", "rule", "query", "journal"}
    if not ptype or ptype not in valid_types:
        missing.append("올바른 type (frontmatter)")
        return missing

    # If it is an exempt type, we skip confidence, why it matters, and opposing views checks
    if ptype in COG_GOV_EXEMPT_TYPES:
        return []

    # 2. Check confidence
    conf = meta.get("confidence")
    if not isinstance(conf, str) or conf.strip().lower() not in COG_GOV_CONFIDENCE_LEVELS:
        missing.append("confidence (frontmatter)")
        
    # 3. Check why it matters
    if not _has_why_it_matters(content):
        missing.append("Why it matters 섹션/패턴")
        
    # 4. Check opposing heading
    if not _has_oppose_heading(content):
        missing.append("반대 입장/한계/대안 섹션")
        
    return missing
