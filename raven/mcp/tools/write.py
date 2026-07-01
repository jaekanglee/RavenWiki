"""write.py — 2 mutating MCP tools (require --write).

Tools:
    wiki_update — overwrite a markdown file (frontmatter-aware)
    wiki_ingest — turn a raw source into a vault page (lightweight)

NOTE: this module does NOT touch git. The orchestrator (Hermes) commits
the diff after a batch of writes. Tools only mutate files.
"""
from __future__ import annotations

import datetime as dt
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

import frontmatter

from raven.mcp import db
from raven.mcp.tools import (
    VaultContext,
    append_log_entry,
    check_lock,
    check_permission,
    lookup_idempotent,
    normalize_actor,
    now_iso,
    record_idempotent,
)


# ─────────────── shared helpers ───────────────


def _resolve_md_path(vault: Path, slug: str) -> Path:
    """Resolve a slug to an absolute markdown path.

    The slug may be a vault-relative path with or without the .md suffix
    (e.g. ``"concepts/wiki"`` or ``"_meta/system/SCHEMA.md"``).
    """
    p = Path(slug)
    if p.suffix != ".md":
        p = p.with_suffix(".md")
    return vault / p


def _is_immutable_agent_path(slug: str) -> bool:
    """Return True when the slug points at a protected agent read-only area."""
    normalized = slug.strip().lower()
    if normalized.endswith(".md"):
        normalized = normalized[:-3]
    return (
        normalized == "log" or
        normalized.startswith("raw/") or
        normalized.startswith("content/raw/") or
        normalized.startswith("_meta/")
    )


def _rebuild_db(vault: Path) -> None:
    """Re-run scripts/build_db.py so wiki.db reflects on-disk changes.

    Best-effort: prints to stderr on failure but does not raise (admin
    operations should succeed even if DB rebuild fails — the caller can
    manually rerun build_db later).
    """
    build_script = vault / "scripts" / "build_db.py"
    if not build_script.exists():
        return
    try:
        subprocess.run(
            [sys.executable, str(build_script), str(vault)],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as e:
        sys.stderr.write(f"⚠️  build_db.py failed: {e.stderr or e.stdout}\n")


# ─────────────── M4 / F1 — provenance + idempotency ───────────────
#
# The four write tools all follow the same shape:
#
#   1. normalize actor
#   2. check idempotency_key (short-circuit if already executed)
#   3. do the actual write (page archive / frontmatter rewrite / etc.)
#   4. attach actor/idempotency_key/timestamp to the response
#   5. record provenance in log.md
#   6. persist idempotency cache for future retries
#
# Steps 1, 2, 4, 5, 6 are tool-agnostic and live in helpers below.
# Step 3 — the real work — is intentionally untouched per F1 spec.

# Common response keys attached to every successful write. Tools merge
# these into their existing return dicts so README.md §8 ("additive-only
# response keys") is honored.
_PROVENANCE_KEYS = ("actor", "idempotency_key", "timestamp")


def _attach_provenance(
    response: dict,
    *,
    actor: str,
    idempotency_key: Optional[str],
    timestamp: Optional[str] = None,
) -> dict:
    """Return a copy of ``response`` with provenance keys attached."""
    out = dict(response)
    out["actor"] = actor
    out["idempotency_key"] = idempotency_key
    out["timestamp"] = timestamp or now_iso()
    return out


def _resolve_idempotency(
    *,
    tool: str,
    vault: Path,
    idempotency_key: Optional[str],
    params: dict,
    actor: str,
):
    """Idempotency precheck.

    Returns ``(cached_response, fingerprint_params)`` where ``cached_response``
    is one of:

      * ``None`` — first call for this key, proceed normally
      * a ``dict`` — the cached response from a previous successful call;
        attach provenance (so the caller sees actor/key/timestamp even
        on a retry) and return immediately
      * a dict with ``"_idempotency_conflict": True`` — the same key was
        used for a *different* write; fail-closed with a clear message

    ``fingerprint_params`` is the params dict the caller should pass into
    ``record_idempotent`` after a successful write (typically the same as
    the input ``params``).
    """
    cached = lookup_idempotent(vault, idempotency_key, tool, params)
    if cached is None:
        return None, params
    if cached.get("_idempotency_conflict"):
        stored = cached.get("stored", {})
        return {
            "ok": False,
            "message": (
                f"idempotency_key {idempotency_key!r} was previously used "
                f"for tool={stored.get('tool')!r} at {stored.get('timestamp')!r}; "
                "refusing to silently reuse it for a different write"
            ),
            "_idempotency_conflict": True,
            "stored": stored,
            "actor": actor,
            "idempotency_key": idempotency_key,
            "timestamp": now_iso(),
        }, params
    # Hit: re-emit cached response with current actor/timestamp attached
    # so callers always see provenance keys. Mark with _idempotent_replay
    # so callers can tell a retry from a fresh write.
    replay = _attach_provenance(
        cached,
        actor=actor,
        idempotency_key=idempotency_key,
    )
    replay["_idempotent_replay"] = True
    return replay, params


# ─────────────── M5 / F4 — advisory concurrency lock ───────────────
#
# M4/F1 attaches actor/idempotency_key/timestamp via ``_attach_provenance``.
# M5/F4 adds ``_lock_holder``: a non-blocking advisory read of any active
# lock on the slugs this write is about to touch. The write proceeds
# regardless (F4 is advisory per README.md §3); the caller sees
# ``_lock_holder`` (with ``_advisory_conflict`` if a different actor
# holds the claim) and decides whether to back off.
#
# Helpers in this section are read-only — ``acquire_lock`` itself is
# exposed in mcp.tools and is the caller's job when they want to *claim*
# a slug before editing. A write tool just *reports* the current state.


def _attach_lock_holder(
    response: dict,
    *,
    vault: Path,
    slugs: list[str],
    actor: str,
) -> dict:
    """Return a copy of ``response`` with ``_lock_holder`` attached.

    Walks ``slugs`` in order and reports the *first* non-self, non-expired
    lock it finds. "Self" here means the holder's actor equals the
    caller — re-acquiring your own lock is fine, we don't want every
    edit to look like a conflict.

    Returns the response unchanged when no advisory conflict exists.
    """
    for slug in slugs:
        if not slug:
            continue
        holder = check_lock(vault, slug)
        if holder is None:
            continue
        if holder.get("actor") == actor:
            # Our own claim — not a conflict, just metadata.
            response["_lock_holder"] = holder
            response["_lock_holder"]["_advisory_conflict"] = False
            response["_lock_holder"]["_self"] = True
            return response
        # Foreign actor — this is the F4 advisory case.
        response["_lock_holder"] = holder
        # holder already carries ``_advisory_conflict: True`` from
        # ``check_lock``; we re-state it at the response level so a
        # shallow ``if resp.get("_advisory_conflict")`` check still
        # works without descending into the lock dict.
        response["_advisory_conflict"] = True
        response["_lock_holder"]["_self"] = False
        return response
    # No active lock on any slug → explicit None so callers don't have
    # to special-case missing vs empty.
    response["_lock_holder"] = None
    return response


def _finalize_write(
    *,
    tool: str,
    vault: Path,
    action: str,
    subject: str,
    actor: str,
    idempotency_key: Optional[str],
    params: dict,
    response: dict,
    extras: Optional[list[str]] = None,
    skip_idempotency_record: bool = False,
    slugs: Optional[list[str]] = None,
) -> dict:
    """Post-write bookkeeping.

    Attaches provenance, reads the advisory lock state on ``slugs``,
    appends the log entry, persists the idempotency record (unless the
    caller is on the cached-replay path). Returns the augmented response
    dict.

    The ``slugs`` arg is the F4 hook — callers pass the slugs their write
    touched (one for update/ingest/delete, two for rename). When omitted,
    no lock probe is performed (preserves pre-F4 behavior for any
    existing caller that hasn't been migrated).
    """
    response = _attach_provenance(
        response, actor=actor, idempotency_key=idempotency_key
    )
    if slugs:
        # F4: read-only advisory lock check. The write has already
        # succeeded by this point; we just surface the conflict for the
        # caller to see.
        response = _attach_lock_holder(
            response, vault=vault, slugs=list(slugs), actor=actor,
        )
    # Skip the log append on cached replays — re-executing an idempotent
    # write should not produce a second provenance entry.
    if not response.get("_idempotent_replay"):
        log_ok = append_log_entry(
            vault, action=action, subject=subject,
            actor=actor, idempotency_key=idempotency_key, extras=extras,
        )
        response["log_appended"] = log_ok
        if not skip_idempotency_record:
            record_idempotent(vault, idempotency_key, tool, params, response)
    else:
        response["log_appended"] = False
    return response


# ─────────────── 6. wiki_update ───────────────


def wiki_update(
    slug: str,
    content: str,
    frontmatter_data: Optional[dict] = None,
    ctx: Optional[VaultContext] = None,
    actor: Optional[str] = None,
    idempotency_key: Optional[str] = None,
) -> dict:
    """Update (or create) a markdown page by slug.

    Args:
        slug: vault slug (e.g. ``"concepts/wiki"``, ``"SCHEMA"``,
              ``"_meta/system/SCHEMA.md"``). Top-level slugs (no ``/``) are
              allowed — the file simply lives at the vault root.
        content: raw markdown body (without frontmatter)
        frontmatter_data: optional dict to serialize as YAML frontmatter
        ctx: VaultContext; defaults to read/write/admin per the CLI
        actor: optional caller identity (M4/F1 provenance). Defaults to
            ``"anonymous"`` when omitted.
        idempotency_key: optional retry-suppression key (M4/F1). Re-running
            a write with the same key + same parameters returns the cached
            response without touching the file. Reusing a key with
            *different* parameters fails closed with an ``ok=False`` reply.

    Returns:
        ``{"ok": bool, "message": str, "path": str, "actor": str,
            "idempotency_key": str|None, "timestamp": str}``
    """
    ctx = ctx or VaultContext(vault=db._default_vault())
    ctx.require("wiki_update")  # raises if read mode

    # M3 fix (was: rejected any slug without "/"). We now only require
    # *some* non-empty slug — top-level pages (e.g. SCHEMA.md) are valid.
    if not slug:
        return {
            "ok": False,
            "message": "slug required", "path": "",
            "actor": normalize_actor(actor),
            "idempotency_key": idempotency_key,
            "timestamp": now_iso(),
        }

    actor_norm = normalize_actor(actor)
    vault_path = Path(ctx.vault).expanduser()

    # Idempotency precheck. Only meaningful when the file exists, because
    # the cached response is keyed on (slug, content, frontmatter_data) —
    # if the file was deleted between calls the cache should not hide the
    # "does not exist" error.
    abs_path = _resolve_md_path(vault_path, slug)
    if _is_immutable_agent_path(slug):
        rel = abs_path.relative_to(vault_path)
        return {
            "ok": False,
            "message": (
                f"{rel} is read-only for agents. "
                "raw/, _meta/, and log.md must not be updated via wiki_update."
            ),
            "path": str(rel),
            "actor": actor_norm,
            "idempotency_key": idempotency_key,
            "timestamp": now_iso(),
            "error": "permission_denied",
        }
    if idempotency_key and abs_path.exists():
        cached, _ = _resolve_idempotency(
            tool="wiki_update", vault=vault_path,
            idempotency_key=idempotency_key, actor=actor_norm,
            params={
                "slug": slug, "content": content,
                "frontmatter_data": frontmatter_data,
            },
        )
        if cached is not None:
            return cached

    holder = check_lock(vault_path, slug)
    if holder and holder.get("actor") != actor_norm:
        return {
            "ok": False,
            "message": f"Lock conflict: page '{slug}' is currently locked by agent '{holder['actor']}'. Please wait or release the lock.",
            "path": slug,
            "actor": actor_norm,
            "idempotency_key": idempotency_key,
            "timestamp": now_iso(),
            "error": "lock_conflict",
            "_lock_holder": holder,
        }

    if not abs_path.exists():
        return {
            "ok": False,
            "message": (
                f"file does not exist: {abs_path.relative_to(vault_path)}. "
                "Use wiki_ingest for new pages."
            ),
            "path": str(abs_path.relative_to(vault_path)),
            "actor": actor_norm,
            "idempotency_key": idempotency_key,
            "timestamp": now_iso(),
        }

    # Read existing frontmatter if caller didn't supply one
    existing = frontmatter.load(abs_path)
    meta = dict(frontmatter_data) if frontmatter_data else dict(existing.metadata)
    meta["updated"] = dt.date.today().isoformat()
    # M4/F1: actor provenance on the page itself.
    meta["actor"] = actor_norm

    # Validate gardening schema if llm_wiki is enabled
    from raven.core.vault import Vault
    from raven.core.registry import VaultMeta
    from raven.core.contracts import validate_gardening_schema
    
    v_meta = VaultMeta(name=vault_path.name, path=vault_path)
    vault = Vault(meta=v_meta, root=vault_path)
    
    if vault.is_llm_wiki:
        missing = validate_gardening_schema(vault, slug, content or "", meta)
        if missing:
            return {
                "ok": False,
                "message": (
                    "WIP가 아닌 메인 content/ 페이지는 Frontmatter와 규약을 완전히 갖춰야 합니다. "
                    f"누락된 항목: {', '.join(missing)}. "
                    "임시 작업은 content/wip/ 아래에 작성해 주세요."
                ),
                "path": str(abs_path.relative_to(vault_path)),
                "actor": actor_norm,
                "idempotency_key": idempotency_key,
                "timestamp": now_iso(),
            }

    post = frontmatter.Post(content, **meta)
    abs_path.write_text(frontmatter.dumps(post) + "\n", encoding="utf-8")
    rel = abs_path.relative_to(vault_path)
    response = {
        "ok": True,
        "message": f"updated {rel}",
        "path": str(rel),
        "rewritten_files": 0,
    }
    return _finalize_write(
        tool="wiki_update", vault=vault_path, action="update",
        subject=str(rel), actor=actor_norm,
        idempotency_key=idempotency_key,
        params={"slug": slug, "content": content,
                "frontmatter_data": frontmatter_data},
        response=response,
        extras=[f"path: {rel}"],
        slugs=[slug],
    )


# ─────────────── 7. wiki_ingest ───────────────


def wiki_ingest(
    source: str,
    project: Optional[str] = None,
    mode: str = "auto",
    ctx: Optional[VaultContext] = None,
    actor: Optional[str] = None,
    idempotency_key: Optional[str] = None,
) -> dict:
    """Ingest a raw source into the vault.

    Args:
        source: absolute path to a file under <vault>/raw/ (or a string
                of raw text when source ends with ':::').
        project: optional project tag (added to frontmatter)
        mode: "auto" → write to raw/<project>/ if not yet present,
              "force" → always overwrite
        ctx: VaultContext
        actor: optional caller identity (M4/F1 provenance). Defaults to
            ``"anonymous"`` when omitted.
        idempotency_key: optional retry-suppression key (M4/F1). Re-running
            a write with the same key + same parameters returns the cached
            response without touching the file. Reusing a key with
            *different* parameters fails closed with an ``ok=False`` reply.

    Returns:
        ``{"ok": bool, "message": str, "pages_created": int,
            "pages_updated": int, "actor": str,
            "idempotency_key": str|None, "timestamp": str}``
    """
    ctx = ctx or VaultContext(vault=db._default_vault())
    ctx.require("wiki_ingest")

    actor_norm = normalize_actor(actor)
    provenance = {
        "actor": actor_norm,
        "idempotency_key": idempotency_key,
        "timestamp": now_iso(),
    }
    fail = lambda msg, **kw: {  # noqa: E731
        "ok": False, "message": msg,
        "pages_created": 0, "pages_updated": 0,
        **provenance, **kw,
    }

    # M3 fix: callers sometimes pass VaultContext(vault="~/wiki") as a str.
    # Normalize to Path before any / operator, otherwise `str / "raw"`
    # raises TypeError on Py 3.11+.
    vault_path = Path(ctx.vault).expanduser()
    raw_root = vault_path / "raw"
    if not raw_root.exists():
        return fail(f"raw/ does not exist at {raw_root}")

    src_path = Path(source).expanduser()
    if not src_path.is_absolute():
        src_path = vault_path / source

    if not src_path.exists():
        return fail(f"source not found: {source}")

    # Decide destination under raw/<project>/<basename>
    project_dir = raw_root / (project or "default")
    project_dir.mkdir(parents=True, exist_ok=True)
    dest = project_dir / src_path.name

    # Idempotency precheck — only when the destination already exists,
    # because wiki_ingest already short-circuits re-ingestion in that
    # case. We layer our cache on top: the cached response takes priority
    # over the file-system "already exists" branch.
    ingest_params = {
        "source": str(src_path), "project": project,
        "mode": mode,
    }
    if idempotency_key and dest.exists():
        cached, _ = _resolve_idempotency(
            tool="wiki_ingest", vault=vault_path,
            idempotency_key=idempotency_key, actor=actor_norm,
            params=ingest_params,
        )
        if cached is not None:
            return cached

    dest_slug = f"raw/{project or 'default'}/{src_path.name}"
    holder = check_lock(vault_path, dest_slug)
    if holder and holder.get("actor") != actor_norm:
        return {
            "ok": False,
            "message": f"Lock conflict: raw path '{dest_slug}' is currently locked by agent '{holder['actor']}'. Please wait or release the lock.",
            "pages_created": 0,
            "pages_updated": 0,
            "actor": actor_norm,
            "idempotency_key": idempotency_key,
            "timestamp": now_iso(),
            "error": "lock_conflict",
            "_lock_holder": holder,
        }

    if dest.exists() and mode != "force":
        response = {
            "ok": True,
            "message": f"already ingested at {dest.relative_to(vault_path)} (use mode=force to overwrite)",
            "pages_created": 0,
            "pages_updated": 0,
        }
        # No actual copy happened — skip log/idempotency to avoid spurious
        # provenance on a no-op. Still return provenance keys so callers
        # see them.
        return _attach_provenance(response, actor=actor_norm,
                                   idempotency_key=idempotency_key)

    shutil.copy2(src_path, dest)
    response = {
        "ok": True,
        "message": f"ingested to {dest.relative_to(vault_path)}",
        "pages_created": 1,
        "pages_updated": 0,
    }
    return _finalize_write(
        tool="wiki_ingest", vault=vault_path, action="ingest",
        subject=str(dest.relative_to(vault_path)),
        actor=actor_norm, idempotency_key=idempotency_key,
        params=ingest_params, response=response,
        extras=[f"source: {src_path.name}",
                f"project: {project or 'default'}"],
        slugs=[f"raw/{project or 'default'}/{src_path.name}"],
    )


# ─────────────── 8. wiki_delete (admin) ───────────────


def wiki_delete(
    slug: str,
    ctx: Optional[VaultContext] = None,
    actor: Optional[str] = None,
    idempotency_key: Optional[str] = None,
) -> dict:
    """Delete a vault page by archiving it to ``_archive/``.

    The page is moved to ``<vault>/_archive/<slug>-YYYYMMDD.md`` (never
    permanently destroyed — git + archive both retain history). ``wiki.db``
    is then rebuilt so backlinks and search reflect the new state.

    Args:
        slug: vault slug (e.g. ``"concepts/wiki"``)
        ctx: VaultContext (must be ``admin`` mode)
        actor: optional caller identity (M4/F1 provenance). Defaults to
            ``"anonymous"`` when omitted.
        idempotency_key: optional retry-suppression key (M4/F1). Re-running
            a write with the same key + same parameters returns the cached
            response without re-archiving. Reusing a key with *different*
            parameters fails closed with an ``ok=False`` reply.

    Returns:
        ``{"ok": bool, "message": str, "archived": str|None,
            "rewritten_files": int, "actor": str,
            "idempotency_key": str|None, "timestamp": str}``
    """
    ctx = ctx or VaultContext(vault=db._default_vault(), mode="admin")
    ctx.require("wiki_delete")

    actor_norm = normalize_actor(actor)
    provenance = {
        "actor": actor_norm,
        "idempotency_key": idempotency_key,
        "timestamp": now_iso(),
    }
    fail = lambda msg, **kw: {  # noqa: E731
        "ok": False, "message": msg,
        "archived": None, "rewritten_files": 0,
        **provenance, **kw,
    }

    if not slug:
        return fail("slug required")

    vault_path = Path(ctx.vault).expanduser()
    abs_path = _resolve_md_path(vault_path, slug)

    # Idempotency precheck. Run even when the file is missing: a retry of
    # a successful archive should still return the cached "ok=True"
    # response, not the fresh "not found" branch.
    if idempotency_key:
        cached, _ = _resolve_idempotency(
            tool="wiki_delete", vault=vault_path,
            idempotency_key=idempotency_key, actor=actor_norm,
            params={"slug": slug},
        )
        if cached is not None:
            return cached

    holder = check_lock(vault_path, slug)
    if holder and holder.get("actor") != actor_norm:
        return {
            "ok": False,
            "message": f"Lock conflict: page '{slug}' is currently locked by agent '{holder['actor']}'. Please wait or release the lock.",
            "archived": None,
            "rewritten_files": 0,
            "actor": actor_norm,
            "idempotency_key": idempotency_key,
            "timestamp": now_iso(),
            "error": "lock_conflict",
            "_lock_holder": holder,
        }

    if not abs_path.exists():
        return fail(f"{slug} not found")

    archive_dir = vault_path / "_archive"
    archive_dir.mkdir(exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    archive_path = archive_dir / f"{abs_path.stem}-{stamp}.md"
    # If a same-second collision exists, suffix with a counter.
    counter = 1
    while archive_path.exists():
        archive_path = archive_dir / f"{abs_path.stem}-{stamp}-{counter}.md"
        counter += 1

    abs_path.rename(archive_path)
    _rebuild_db(vault_path)

    response = {
        "ok": True,
        "message": f"archived {slug} → {archive_path.relative_to(vault_path)}",
        "archived": str(archive_path.relative_to(vault_path)),
        "rewritten_files": 0,
    }
    return _finalize_write(
        tool="wiki_delete", vault=vault_path, action="archive",
        subject=slug, actor=actor_norm, idempotency_key=idempotency_key,
        params={"slug": slug}, response=response,
        extras=[f"archived_to: {archive_path.relative_to(vault_path)}"],
        slugs=[slug],
    )


# ─────────────── 9. wiki_rename (admin) ───────────────


def wiki_rename(
    old_slug: str,
    new_slug: str,
    ctx: Optional[VaultContext] = None,
    actor: Optional[str] = None,
    idempotency_key: Optional[str] = None,
) -> dict:
    """Rename a slug and rewrite every inbound ``[[old_slug]]`` wikilink.

    Steps:
        1. Locate ``<old>.md`` under the vault.
        2. Update its frontmatter ``slug:`` field (if present) to ``new_slug``
           and add ``aliases: [<old_slug>]`` so old links continue to resolve.
        3. Move the file to ``<new>.md``.
        4. Walk every other markdown file in the vault and rewrite
           ``[[old_slug]]`` → ``[[new_slug]]`` (preserving intent
           suffixes ``!`` / ``?``).
        5. Rebuild ``wiki.db`` so backlinks/search reflect the rename.

    Args:
        old_slug: current vault slug (file must exist)
        new_slug: target vault slug (file must NOT exist)
        ctx: VaultContext (must be ``admin`` mode)
        actor: optional caller identity (M4/F1 provenance). Defaults to
            ``"anonymous"`` when omitted.
        idempotency_key: optional retry-suppression key (M4/F1). Re-running
            a write with the same key + same parameters returns the cached
            response without re-renaming. Reusing a key with *different*
            parameters fails closed with an ``ok=False`` reply.

    Returns:
        ``{"ok": bool, "message": str, "rewritten_files": int,
            "old_slug": str, "new_slug": str, "actor": str,
            "idempotency_key": str|None, "timestamp": str}``
    """
    ctx = ctx or VaultContext(vault=db._default_vault(), mode="admin")
    ctx.require("wiki_rename")

    actor_norm = normalize_actor(actor)
    provenance = {
        "actor": actor_norm,
        "idempotency_key": idempotency_key,
        "timestamp": now_iso(),
    }
    fail = lambda msg, **kw: {  # noqa: E731
        "ok": False, "message": msg, "rewritten_files": 0,
        "old_slug": old_slug, "new_slug": new_slug,
        **provenance, **kw,
    }

    if not old_slug or not new_slug:
        return fail("old_slug and new_slug are required")

    vault_path = Path(ctx.vault).expanduser()

    # Idempotency precheck. The rename fingerprint includes both slugs
    # — a retry with the same key+slug pair returns the cached response,
    # even if old_slug no longer exists on disk (which it won't, after a
    # successful rename).
    if idempotency_key:
        cached, _ = _resolve_idempotency(
            tool="wiki_rename", vault=vault_path,
            idempotency_key=idempotency_key, actor=actor_norm,
            params={"old_slug": old_slug, "new_slug": new_slug},
        )
        if cached is not None:
            return cached

    old_holder = check_lock(vault_path, old_slug)
    if old_holder and old_holder.get("actor") != actor_norm:
        return {
            "ok": False,
            "message": f"Lock conflict: page '{old_slug}' is currently locked by agent '{old_holder['actor']}'. Please wait or release the lock.",
            "rewritten_files": 0,
            "old_slug": old_slug,
            "new_slug": new_slug,
            "actor": actor_norm,
            "idempotency_key": idempotency_key,
            "timestamp": now_iso(),
            "error": "lock_conflict",
            "_lock_holder": old_holder,
        }

    new_holder = check_lock(vault_path, new_slug)
    if new_holder and new_holder.get("actor") != actor_norm:
        return {
            "ok": False,
            "message": f"Lock conflict: page '{new_slug}' is currently locked by agent '{new_holder['actor']}'. Please wait or release the lock.",
            "rewritten_files": 0,
            "old_slug": old_slug,
            "new_slug": new_slug,
            "actor": actor_norm,
            "idempotency_key": idempotency_key,
            "timestamp": now_iso(),
            "error": "lock_conflict",
            "_lock_holder": new_holder,
        }

    old_path = _resolve_md_path(vault_path, old_slug)
    if not old_path.exists():
        return fail(f"{old_slug} not found")

    new_path = _resolve_md_path(vault_path, new_slug)
    if new_path.exists() and new_path != old_path:
        return fail(f"{new_slug} already exists")

    # 1+2+3: rewrite frontmatter and move file.
    text = old_path.read_text(encoding="utf-8")
    post = frontmatter.Post("")
    body = text
    try:
        post = frontmatter.loads(text)
        meta = dict(post.metadata)
        body = post.content
    except Exception:
        meta = {}

    meta["slug"] = new_slug
    aliases = list(meta.get("aliases") or [])
    if old_slug not in aliases:
        aliases.insert(0, old_slug)
    meta["aliases"] = aliases
    meta["updated"] = dt.date.today().isoformat()
    # M4/F1: actor provenance on the renamed page itself.
    meta["actor"] = actor_norm

    if body.startswith("---\n"):
        # safety: re-strip frontmatter if loader missed it
        body = re.sub(r"^---\n.*?\n---\n", "", text, count=1, flags=re.DOTALL)

    new_post = frontmatter.Post(body, **meta)
    new_path.parent.mkdir(parents=True, exist_ok=True)
    new_path.write_text(frontmatter.dumps(new_post) + "\n", encoding="utf-8")

    # Remove the old file (unless rename is a no-op overwrite-in-place).
    if old_path != new_path:
        old_path.unlink()

    # 4: rewrite every inbound [[old_slug]] → [[new_slug]] across the vault.
    # Capture the optional intent char (!/?) and re-emit it intact, so
    # [[old]]! / [[old]]? stay syntactically equivalent after rename.
    pattern = re.compile(r"\[\[" + re.escape(old_slug) + r"(!|\?)?\]\]")
    rewritten = 0
    excluded = {"raw", "_archive", "scripts", "node_modules", ".venv", ".git", "dashboard"}
    for md in vault_path.rglob("*.md"):
        if any(part in excluded for part in md.relative_to(vault_path).parts):
            continue
        try:
            content = md.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        new_content, n = pattern.subn(
            lambda m: "[[" + new_slug + (m.group(1) or "") + "]]",
            content,
        )
        if n > 0:
            md.write_text(new_content, encoding="utf-8")
            rewritten += n

    # 5: rebuild DB
    _rebuild_db(vault_path)

    response = {
        "ok": True,
        "message": f"renamed {old_slug} → {new_slug} ({rewritten} wikilinks rewritten)",
        "rewritten_files": rewritten,
        "old_slug": old_slug,
        "new_slug": new_slug,
    }
    return _finalize_write(
        tool="wiki_rename", vault=vault_path, action="rename",
        subject=f"{old_slug} → {new_slug}",
        actor=actor_norm, idempotency_key=idempotency_key,
        params={"old_slug": old_slug, "new_slug": new_slug},
        response=response,
        extras=[f"wikilinks_rewritten: {rewritten}"],
        slugs=[old_slug, new_slug],
    )
