"""test_mcp_concurrency.py — M5/F4 advisory lock integration with write tools.

End-to-end tests for the four MCP write tools (``wiki_update``,
``wiki_ingest``, ``wiki_delete``, ``wiki_rename``) under the F4
advisory-lock contract. Every test uses an isolated temporary vault so
no real wiki state is touched.

What we verify (matches the F4 spec):

  1. wiki_update
     - no lock → ``_lock_holder=None``, ``_advisory_conflict`` absent/false
     - same actor holds lock → ``_lock_holder`` is self, no conflict
     - different actor holds lock → ``_lock_holder`` carries their name,
       ``_advisory_conflict=True``, write still succeeds (F4 is advisory)
  2. wiki_ingest — same three cases on the derived dest slug
  3. wiki_delete — same three cases on the slug
  4. wiki_rename — both old_slug and new_slug are probed; first conflict
     wins (write still succeeds)
  5. Backward compatibility — pre-F4 callers (no lock layer touched)
     still get all F1 keys plus ``_lock_holder=None``
  6. Independence — locking one slug doesn't taint a sibling
  7. Response shape — every write response carries ``_lock_holder``;
     the dict (or None) is the single source of truth for the caller
"""
from __future__ import annotations

import json
import uuid
from pathlib import Path

import pytest

from raven.mcp.tools import (
    ADMIN,
    ANONYMOUS_ACTOR,
    VaultContext,
    WRITE,
    acquire_lock,
)
from raven.mcp.tools.write import (
    wiki_delete,
    wiki_ingest,
    wiki_rename,
    wiki_update,
)


# ─────────────── fixtures ───────────────


@pytest.fixture
def temp_vault(tmp_path: Path) -> Path:
    """A minimal isolated vault for write-tool tests."""
    (tmp_path / "raw").mkdir()
    (tmp_path / "_archive").mkdir()
    (tmp_path / "queries").mkdir()
    (tmp_path / "log.md").write_text(
        "# Wiki Log\n\n> append-only provenance\n\n",
        encoding="utf-8",
    )
    return tmp_path


def _stage_page(vault: Path, slug: str, title: str = "test") -> Path:
    abs_path = vault / f"{slug}.md"
    abs_path.parent.mkdir(parents=True, exist_ok=True)
    abs_path.write_text(
        f"---\ntitle: {title}\ntype: query\n---\n\nbody for {slug}\n",
        encoding="utf-8",
    )
    return abs_path


def _locks_store(vault: Path) -> dict:
    p = vault / ".mcp" / "locks.json"
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


# ─────────────── wiki_update — lock integration ───────────────


def test_update_no_lock_yields_empty_holder(temp_vault: Path):
    slug = f"queries/f4u_{uuid.uuid4().hex[:8]}"
    _stage_page(temp_vault, slug)
    ctx = VaultContext(vault=temp_vault, mode=WRITE)

    r = wiki_update(slug=slug, content="body\n", actor="alice", ctx=ctx)
    assert r["ok"] is True
    assert r["_lock_holder"] is None
    assert r.get("_advisory_conflict") in (False, None)


def test_update_same_actor_lock_is_self(temp_vault: Path):
    slug = f"queries/f4u_{uuid.uuid4().hex[:8]}"
    _stage_page(temp_vault, slug)
    ctx = VaultContext(vault=temp_vault, mode=WRITE)

    acquire_lock(temp_vault, slug, "alice")
    r = wiki_update(slug=slug, content="body\n", actor="alice", ctx=ctx)
    assert r["ok"] is True
    holder = r["_lock_holder"]
    assert holder is not None
    assert holder["actor"] == "alice"
    assert holder["_self"] is True
    assert holder["_advisory_conflict"] is False
    assert r.get("_advisory_conflict") in (False, None)


def test_update_foreign_actor_lock_advisory_only(temp_vault: Path):
    """The F4 spec scenario: bob writes while alice holds. Write still succeeds."""
    slug = f"queries/f4u_{uuid.uuid4().hex[:8]}"
    abs_path = _stage_page(temp_vault, slug)
    ctx = VaultContext(vault=temp_vault, mode=WRITE)

    acquire_lock(temp_vault, slug, "alice")
    pre = abs_path.read_text(encoding="utf-8")
    r = wiki_update(slug=slug, content="bob body\n", actor="bob", ctx=ctx)

    # Write succeeded — F4 is advisory, never blocking.
    assert r["ok"] is True
    assert "bob body" in abs_path.read_text(encoding="utf-8")
    assert pre != abs_path.read_text(encoding="utf-8")

    # Caller sees the conflict.
    holder = r["_lock_holder"]
    assert holder is not None
    assert holder["actor"] == "alice"
    assert holder["_self"] is False
    assert holder["_advisory_conflict"] is True
    assert r.get("_advisory_conflict") is True


def test_update_default_actor_advisory_self(temp_vault: Path):
    """Anonymous caller sees their own (anonymous) claim as self."""
    slug = f"queries/f4u_{uuid.uuid4().hex[:8]}"
    _stage_page(temp_vault, slug)
    ctx = VaultContext(vault=temp_vault, mode=WRITE)

    acquire_lock(temp_vault, slug, None)  # anonymous
    r = wiki_update(slug=slug, content="body\n", ctx=ctx)
    assert r["ok"] is True
    holder = r["_lock_holder"]
    assert holder is not None
    assert holder["actor"] == ANONYMOUS_ACTOR
    assert holder["_self"] is True


# ─────────────── wiki_ingest — lock integration ───────────────


def test_ingest_dest_slug_uses_lock(temp_vault: Path):
    """Lock on the derived ``raw/<project>/<src>`` slug must be observed."""
    src = temp_vault / f"src_{uuid.uuid4().hex[:8]}.md"
    src.write_text("# raw\n", encoding="utf-8")
    ctx = VaultContext(vault=temp_vault, mode=WRITE)

    dest_slug = "raw/proj/" + src.name
    acquire_lock(temp_vault, dest_slug, "alice")
    r = wiki_ingest(source=str(src), project="proj", actor="bob", ctx=ctx)

    assert r["ok"] is True
    holder = r["_lock_holder"]
    assert holder is not None
    assert holder["actor"] == "alice"
    assert r.get("_advisory_conflict") is True


def test_ingest_no_lock(temp_vault: Path):
    src = temp_vault / f"src_{uuid.uuid4().hex[:8]}.md"
    src.write_text("# raw\n", encoding="utf-8")
    ctx = VaultContext(vault=temp_vault, mode=WRITE)

    r = wiki_ingest(source=str(src), project="proj", actor="alice", ctx=ctx)
    assert r["ok"] is True
    assert r["_lock_holder"] is None


# ─────────────── wiki_delete — lock integration ───────────────


def test_delete_foreign_actor_advisory(temp_vault: Path):
    slug = f"queries/f4d_{uuid.uuid4().hex[:8]}"
    _stage_page(temp_vault, slug)
    ctx = VaultContext(vault=temp_vault, mode=ADMIN)

    acquire_lock(temp_vault, slug, "alice")
    r = wiki_delete(slug=slug, actor="bob", ctx=ctx)
    assert r["ok"] is True  # advisory only — delete proceeded
    holder = r["_lock_holder"]
    assert holder is not None
    assert holder["actor"] == "alice"
    assert r.get("_advisory_conflict") is True

    # Restore so the temp vault stays clean.
    archive = temp_vault / r["archived"]
    if archive.exists():
        archive.rename(temp_vault / f"{slug}.md")


def test_delete_no_lock(temp_vault: Path):
    slug = f"queries/f4d_{uuid.uuid4().hex[:8]}"
    _stage_page(temp_vault, slug)
    ctx = VaultContext(vault=temp_vault, mode=ADMIN)

    r = wiki_delete(slug=slug, actor="alice", ctx=ctx)
    assert r["ok"] is True
    assert r["_lock_holder"] is None

    archive = temp_vault / r["archived"]
    if archive.exists():
        archive.rename(temp_vault / f"{slug}.md")


# ─────────────── wiki_rename — both slugs probed ───────────────


def test_rename_old_slug_lock_advisory(temp_vault: Path):
    old = f"queries/f4ro_{uuid.uuid4().hex[:8]}"
    new = f"queries/f4rn_{uuid.uuid4().hex[:8]}"
    _stage_page(temp_vault, old)
    ctx = VaultContext(vault=temp_vault, mode=ADMIN)

    acquire_lock(temp_vault, old, "alice")
    r = wiki_rename(old_slug=old, new_slug=new, actor="bob", ctx=ctx)
    assert r["ok"] is True  # advisory only
    holder = r["_lock_holder"]
    assert holder is not None
    assert holder["actor"] == "alice"
    assert r.get("_advisory_conflict") is True

    (temp_vault / f"{new}.md").unlink()


def test_rename_new_slug_lock_advisory(temp_vault: Path):
    """Lock on the *target* slug must also surface (rename touches both)."""
    old = f"queries/f4ro_{uuid.uuid4().hex[:8]}"
    new = f"queries/f4rn_{uuid.uuid4().hex[:8]}"
    _stage_page(temp_vault, old)
    ctx = VaultContext(vault=temp_vault, mode=ADMIN)

    # Lock the destination slug only.
    acquire_lock(temp_vault, new, "carol")
    r = wiki_rename(old_slug=old, new_slug=new, actor="bob", ctx=ctx)
    assert r["ok"] is True
    holder = r["_lock_holder"]
    assert holder is not None
    # The probe walks old → new; both are free of foreign claims until new.
    assert holder["actor"] == "carol"
    assert r.get("_advisory_conflict") is True

    (temp_vault / f"{new}.md").unlink()


def test_rename_no_lock(temp_vault: Path):
    old = f"queries/f4ro_{uuid.uuid4().hex[:8]}"
    new = f"queries/f4rn_{uuid.uuid4().hex[:8]}"
    _stage_page(temp_vault, old)
    ctx = VaultContext(vault=temp_vault, mode=ADMIN)

    r = wiki_rename(old_slug=old, new_slug=new, actor="alice", ctx=ctx)
    assert r["ok"] is True
    assert r["_lock_holder"] is None

    (temp_vault / f"{new}.md").unlink()


# ─────────────── invariants ───────────────


def test_lock_on_sibling_slug_does_not_taint(temp_vault: Path):
    """Locking slug A must not surface when slug B is written."""
    a = f"queries/f4a_{uuid.uuid4().hex[:8]}"
    b = f"queries/f4b_{uuid.uuid4().hex[:8]}"
    _stage_page(temp_vault, a)
    _stage_page(temp_vault, b)
    ctx = VaultContext(vault=temp_vault, mode=WRITE)

    acquire_lock(temp_vault, a, "alice")
    r = wiki_update(slug=b, content="x\n", actor="carol", ctx=ctx)
    assert r["ok"] is True
    assert r["_lock_holder"] is None
    assert r.get("_advisory_conflict") in (False, None)


def test_lock_store_persists_only_on_real_claim(temp_vault: Path):
    """A no-lock write must not write locks.json on its own."""
    slug = f"queries/f4p_{uuid.uuid4().hex[:8]}"
    _stage_page(temp_vault, slug)
    ctx = VaultContext(vault=temp_vault, mode=WRITE)

    wiki_update(slug=slug, content="body\n", actor="alice", ctx=ctx)
    assert _locks_store(temp_vault) == {}


def test_lock_layer_does_not_break_f1_response_keys(temp_vault: Path):
    """Pre-F1 response keys + F1 keys must still all be present."""
    slug = f"queries/f4f1_{uuid.uuid4().hex[:8]}"
    _stage_page(temp_vault, slug)
    ctx = VaultContext(vault=temp_vault, mode=WRITE)

    acquire_lock(temp_vault, slug, "alice")
    r = wiki_update(
        slug=slug, content="body\n",
        actor="alice",
        idempotency_key=f"k-{uuid.uuid4().hex[:8]}",
        ctx=ctx,
    )
    # F1 contract — unchanged.
    assert r["ok"] is True
    assert r["actor"] == "alice"
    assert r["idempotency_key"]
    assert "timestamp" in r
    # F4 contract — additive.
    assert "_lock_holder" in r
