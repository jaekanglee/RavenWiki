"""test_mcp_write_provenance.py — M4/F1 write provenance + idempotency.

Tests the four MCP write tools (``wiki_update``, ``wiki_ingest``,
``wiki_delete``, ``wiki_rename``) under the new ``actor`` and
``idempotency_key`` kwargs. All tests use an isolated temporary vault
so they never touch the real wiki state — provenance tests should be
safe to re-run and to run in parallel.

What we verify (matches the F1 spec):

  1. Actor normalisation
     - default → "anonymous"
     - whitespace stripped
     - empty → "anonymous"

  2. Idempotency
     - same key + same params → cached response (no file write, no log entry)
     - same key + different params → ``ok=False`` conflict (fail-closed)
     - replay response has ``_idempotent_replay=True`` and provenance keys

  3. Provenance
     - response carries ``actor``, ``idempotency_key``, ``timestamp``
     - log.md gets exactly one entry per *fresh* write
     - replay and conflict produce no extra log entries
     - frontmatter carries ``actor`` after update / rename

  4. Backward compatibility
     - omitting both new kwargs still works (pre-F1 call sites)
     - existing response keys are unchanged
"""
from __future__ import annotations

import json
import shutil
import tempfile
import uuid
from pathlib import Path

import frontmatter
import pytest

from mcp.tools import (
    ADMIN,
    ANONYMOUS_ACTOR,
    READ,
    VaultContext,
    WRITE,
    normalize_actor,
    params_fingerprint,
)
from mcp.tools.write import (
    wiki_delete,
    wiki_ingest,
    wiki_rename,
    wiki_update,
)


# ─────────────── fixtures ───────────────


@pytest.fixture
def temp_vault(tmp_path: Path) -> Path:
    """A minimal isolated vault with the directories write tools expect.

    Layout mirrors the real vault just enough for the tools to run:
    ``raw/``, ``_archive/``, ``log.md`` at the root, plus a ``queries/``
    scratch dir for staging test pages.
    """
    (tmp_path / "raw").mkdir()
    (tmp_path / "_archive").mkdir()
    (tmp_path / "queries").mkdir()
    (tmp_path / "log.md").write_text(
        "# Wiki Log\n\n> append-only provenance\n\n",
        encoding="utf-8",
    )
    return tmp_path


def _stage_page(vault: Path, slug: str, title: str = "test") -> Path:
    """Write a minimal valid markdown page under ``vault/<slug>.md``."""
    abs_path = vault / f"{slug}.md"
    abs_path.parent.mkdir(parents=True, exist_ok=True)
    abs_path.write_text(
        f"---\ntitle: {title}\ntype: query\n---\n\nbody for {slug}\n",
        encoding="utf-8",
    )
    return abs_path


def _read_log(vault: Path) -> str:
    return (vault / "log.md").read_text(encoding="utf-8")


def _idem_store(vault: Path) -> dict:
    p = vault / ".mcp" / "idempotency.json"
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


# ─────────────── actor normalisation ───────────────


def test_normalize_actor_defaults_to_anonymous():
    assert normalize_actor(None) == ANONYMOUS_ACTOR
    assert normalize_actor("") == ANONYMOUS_ACTOR
    assert normalize_actor("   ") == ANONYMOUS_ACTOR


def test_normalize_actor_strips_whitespace():
    assert normalize_actor("  alice  ") == "alice"


def test_anonymous_actor_constant():
    """The constant is part of the public surface — clients can rely on it."""
    assert ANONYMOUS_ACTOR == "anonymous"


# ─────────────── wiki_update — actor + idempotency ───────────────


def test_update_response_includes_provenance_keys(temp_vault: Path):
    slug = f"queries/f1_{uuid.uuid4().hex[:8]}"
    _stage_page(temp_vault, slug)
    ctx = VaultContext(vault=temp_vault, mode=WRITE)

    result = wiki_update(
        slug=slug, content="body\n", actor="alice", ctx=ctx,
    )
    assert result["ok"] is True
    assert result["actor"] == "alice"
    assert result["idempotency_key"] is None
    assert "timestamp" in result and isinstance(result["timestamp"], str)


def test_update_default_actor_is_anonymous(temp_vault: Path):
    slug = f"queries/f1_{uuid.uuid4().hex[:8]}"
    _stage_page(temp_vault, slug)
    ctx = VaultContext(vault=temp_vault, mode=WRITE)

    result = wiki_update(slug=slug, content="body\n", ctx=ctx)
    assert result["actor"] == "anonymous"


def test_update_frontmatter_records_actor(temp_vault: Path):
    slug = f"queries/f1_{uuid.uuid4().hex[:8]}"
    abs_path = _stage_page(temp_vault, slug)
    ctx = VaultContext(vault=temp_vault, mode=WRITE)

    wiki_update(slug=slug, content="body\n", actor="bob", ctx=ctx)
    post = frontmatter.loads(abs_path.read_text(encoding="utf-8"))
    assert post.metadata.get("actor") == "bob"
    # updated still gets bumped per M3 contract
    assert "updated" in post.metadata


def test_update_appends_log_entry_with_actor(temp_vault: Path):
    slug = f"queries/f1_{uuid.uuid4().hex[:8]}"
    _stage_page(temp_vault, slug)
    ctx = VaultContext(vault=temp_vault, mode=WRITE)

    wiki_update(slug=slug, content="body\n", actor="carol", ctx=ctx)
    log = _read_log(temp_vault)
    assert "##" in log and "update" in log and "carol" in log


def test_update_log_entry_includes_idempotency_key(temp_vault: Path):
    slug = f"queries/f1_{uuid.uuid4().hex[:8]}"
    _stage_page(temp_vault, slug)
    ctx = VaultContext(vault=temp_vault, mode=WRITE)

    key = f"k-{uuid.uuid4().hex[:8]}"
    wiki_update(
        slug=slug, content="body\n",
        actor="dave", idempotency_key=key, ctx=ctx,
    )
    log = _read_log(temp_vault)
    assert key in log


def test_update_idempotent_replay_does_not_rewrite_file(temp_vault: Path):
    """Same key + same params → no second file write, no second log entry."""
    slug = f"queries/f1_{uuid.uuid4().hex[:8]}"
    abs_path = _stage_page(temp_vault, slug)
    ctx = VaultContext(vault=temp_vault, mode=WRITE)
    key = f"k-{uuid.uuid4().hex[:8]}"

    r1 = wiki_update(
        slug=slug, content="body\n",
        actor="erin", idempotency_key=key, ctx=ctx,
    )
    mtime_before = abs_path.stat().st_mtime_ns
    log_before = _read_log(temp_vault)

    # Sleep enough to make mtime change detectable on most filesystems.
    import time
    time.sleep(0.01)

    r2 = wiki_update(
        slug=slug, content="body\n",
        actor="erin", idempotency_key=key, ctx=ctx,
    )

    assert r1["ok"] and r2["ok"]
    assert r2["_idempotent_replay"] is True
    assert r2["actor"] == "erin"  # re-attached from current call
    assert r2["idempotency_key"] == key
    assert abs_path.stat().st_mtime_ns == mtime_before, "file must not be rewritten"
    assert _read_log(temp_vault) == log_before, "log must not get a second entry"


def test_update_idempotency_conflict_fails_closed(temp_vault: Path):
    """Same key + different params → ok=False, no file write, no log entry."""
    slug = f"queries/f1_{uuid.uuid4().hex[:8]}"
    abs_path = _stage_page(temp_vault, slug)
    ctx = VaultContext(vault=temp_vault, mode=WRITE)
    key = f"k-{uuid.uuid4().hex[:8]}"

    wiki_update(slug=slug, content="original\n", actor="frank", idempotency_key=key, ctx=ctx)
    original_body = abs_path.read_text(encoding="utf-8")
    log_before = _read_log(temp_vault)

    conflict = wiki_update(
        slug=slug, content="TAMPERED\n",
        actor="grace", idempotency_key=key, ctx=ctx,
    )
    assert conflict["ok"] is False
    assert conflict.get("_idempotency_conflict") is True
    assert conflict["actor"] == "grace"
    # The file body must not have been overwritten
    assert abs_path.read_text(encoding="utf-8") == original_body
    # And the log must be untouched
    assert _read_log(temp_vault) == log_before


def test_update_idempotency_store_persisted(temp_vault: Path):
    """The idempotency record is written to <vault>/.mcp/idempotency.json."""
    slug = f"queries/f1_{uuid.uuid4().hex[:8]}"
    _stage_page(temp_vault, slug)
    ctx = VaultContext(vault=temp_vault, mode=WRITE)
    key = f"k-{uuid.uuid4().hex[:8]}"

    wiki_update(
        slug=slug, content="body\n",
        actor="henry", idempotency_key=key, ctx=ctx,
    )
    store = _idem_store(temp_vault)
    assert key in store
    entry = store[key]
    assert entry["tool"] == "wiki_update"
    assert "fingerprint" in entry
    assert "timestamp" in entry
    assert "response" in entry


def test_update_backward_compatible_no_kwargs(temp_vault: Path):
    """Calling without actor/idempotency_key still works (AGENTS.md §8)."""
    slug = f"queries/f1_{uuid.uuid4().hex[:8]}"
    _stage_page(temp_vault, slug)
    ctx = VaultContext(vault=temp_vault, mode=WRITE)

    result = wiki_update(slug=slug, content="body\n", ctx=ctx)
    assert result["ok"] is True
    # Pre-F1 response keys are still present
    assert "message" in result
    assert "path" in result
    # New keys are present too
    assert result["actor"] == ANONYMOUS_ACTOR
    assert result["idempotency_key"] is None


# ─────────────── wiki_ingest — actor + idempotency ───────────────


def test_ingest_response_includes_provenance_keys(temp_vault: Path):
    src = temp_vault / f"src_{uuid.uuid4().hex[:8]}.md"
    src.write_text("# raw\n", encoding="utf-8")
    ctx = VaultContext(vault=temp_vault, mode=WRITE)

    result = wiki_ingest(
        source=str(src), project="proj", actor="iris", ctx=ctx,
    )
    assert result["ok"] is True
    assert result["actor"] == "iris"
    assert result["idempotency_key"] is None
    assert "timestamp" in result

    # Cleanup
    dest = temp_vault / "raw" / "proj" / src.name
    if dest.exists():
        dest.unlink()


def test_ingest_idempotent_replay(temp_vault: Path):
    src = temp_vault / f"src_{uuid.uuid4().hex[:8]}.md"
    src.write_text("# raw\n", encoding="utf-8")
    ctx = VaultContext(vault=temp_vault, mode=WRITE)
    key = f"k-{uuid.uuid4().hex[:8]}"

    r1 = wiki_ingest(source=str(src), project="proj",
                     actor="judy", idempotency_key=key, ctx=ctx)
    r2 = wiki_ingest(source=str(src), project="proj",
                     actor="judy", idempotency_key=key, ctx=ctx)
    assert r1["pages_created"] == 1
    assert r2["pages_created"] == 1
    assert r2["_idempotent_replay"] is True

    # Cleanup
    dest = temp_vault / "raw" / "proj" / src.name
    if dest.exists():
        dest.unlink()


def test_ingest_log_entry(temp_vault: Path):
    src = temp_vault / f"src_{uuid.uuid4().hex[:8]}.md"
    src.write_text("# raw\n", encoding="utf-8")
    ctx = VaultContext(vault=temp_vault, mode=WRITE)

    wiki_ingest(source=str(src), project="proj", actor="kim", ctx=ctx)
    log = _read_log(temp_vault)
    assert "ingest" in log and "kim" in log

    dest = temp_vault / "raw" / "proj" / src.name
    if dest.exists():
        dest.unlink()


# ─────────────── wiki_delete — actor + idempotency ───────────────


def test_delete_response_includes_provenance_keys(temp_vault: Path):
    slug = f"queries/f1_del_{uuid.uuid4().hex[:8]}"
    _stage_page(temp_vault, slug)
    ctx = VaultContext(vault=temp_vault, mode=ADMIN)

    result = wiki_delete(slug=slug, actor="liam", ctx=ctx)
    assert result["ok"] is True
    assert result["actor"] == "liam"
    assert result["idempotency_key"] is None
    assert "timestamp" in result

    # Restore from archive so the temp vault stays clean
    archive = temp_vault / result["archived"]
    archive.rename(temp_vault / f"{slug}.md")


def test_delete_idempotent_replay(temp_vault: Path):
    slug = f"queries/f1_del_{uuid.uuid4().hex[:8]}"
    _stage_page(temp_vault, slug)
    ctx = VaultContext(vault=temp_vault, mode=ADMIN)
    key = f"k-{uuid.uuid4().hex[:8]}"

    r1 = wiki_delete(slug=slug, actor="mia", idempotency_key=key, ctx=ctx)
    archive = temp_vault / r1["archived"]
    # Restore so we can confirm replay does NOT re-archive
    archive.rename(temp_vault / f"{slug}.md")

    r2 = wiki_delete(slug=slug, actor="mia", idempotency_key=key, ctx=ctx)
    assert r2["ok"] is True
    assert r2["_idempotent_replay"] is True
    assert r2["archived"] == r1["archived"]

    # Cleanup
    archive = temp_vault / r2["archived"]
    if archive.exists():
        archive.unlink()


def test_delete_log_entry(temp_vault: Path):
    slug = f"queries/f1_del_{uuid.uuid4().hex[:8]}"
    _stage_page(temp_vault, slug)
    ctx = VaultContext(vault=temp_vault, mode=ADMIN)

    result = wiki_delete(slug=slug, actor="nick", ctx=ctx)
    log = _read_log(temp_vault)
    assert "archive" in log and "nick" in log

    archive = temp_vault / result["archived"]
    if archive.exists():
        archive.unlink()


# ─────────────── wiki_rename — actor + idempotency ───────────────


def test_rename_response_includes_provenance_keys(temp_vault: Path):
    old_slug = f"queries/f1_old_{uuid.uuid4().hex[:8]}"
    new_slug = f"queries/f1_new_{uuid.uuid4().hex[:8]}"
    _stage_page(temp_vault, old_slug)
    ctx = VaultContext(vault=temp_vault, mode=ADMIN)

    result = wiki_rename(
        old_slug=old_slug, new_slug=new_slug,
        actor="olive", ctx=ctx,
    )
    assert result["ok"] is True
    assert result["actor"] == "olive"
    assert result["idempotency_key"] is None
    assert "timestamp" in result

    # Cleanup
    (temp_vault / f"{new_slug}.md").unlink()


def test_rename_frontmatter_records_actor(temp_vault: Path):
    old_slug = f"queries/f1_old_{uuid.uuid4().hex[:8]}"
    new_slug = f"queries/f1_new_{uuid.uuid4().hex[:8]}"
    _stage_page(temp_vault, old_slug)
    ctx = VaultContext(vault=temp_vault, mode=ADMIN)

    wiki_rename(
        old_slug=old_slug, new_slug=new_slug,
        actor="paul", ctx=ctx,
    )
    new_path = temp_vault / f"{new_slug}.md"
    post = frontmatter.loads(new_path.read_text(encoding="utf-8"))
    assert post.metadata.get("actor") == "paul"

    new_path.unlink()


def test_rename_idempotent_replay(temp_vault: Path):
    old_slug = f"queries/f1_old_{uuid.uuid4().hex[:8]}"
    new_slug = f"queries/f1_new_{uuid.uuid4().hex[:8]}"
    _stage_page(temp_vault, old_slug)
    ctx = VaultContext(vault=temp_vault, mode=ADMIN)
    key = f"k-{uuid.uuid4().hex[:8]}"

    r1 = wiki_rename(
        old_slug=old_slug, new_slug=new_slug,
        actor="quinn", idempotency_key=key, ctx=ctx,
    )
    # After successful rename, old_slug no longer exists — but the cached
    # response should still let us replay.
    r2 = wiki_rename(
        old_slug=old_slug, new_slug=new_slug,
        actor="quinn", idempotency_key=key, ctx=ctx,
    )
    assert r1["ok"] and r2["ok"]
    assert r2["_idempotent_replay"] is True
    assert r2["rewritten_files"] == r1["rewritten_files"]

    # Cleanup
    (temp_vault / f"{new_slug}.md").unlink()


def test_rename_idempotency_conflict(temp_vault: Path):
    """Reusing a rename key with a different target must fail closed."""
    old_a = f"queries/f1_a_{uuid.uuid4().hex[:8]}"
    old_b = f"queries/f1_b_{uuid.uuid4().hex[:8]}"
    new_a1 = f"queries/f1_x1_{uuid.uuid4().hex[:8]}"
    new_a2 = f"queries/f1_x2_{uuid.uuid4().hex[:8]}"
    _stage_page(temp_vault, old_a, "a")
    _stage_page(temp_vault, old_b, "b")
    ctx = VaultContext(vault=temp_vault, mode=ADMIN)
    key = f"k-{uuid.uuid4().hex[:8]}"

    wiki_rename(
        old_slug=old_a, new_slug=new_a1,
        actor="ruth", idempotency_key=key, ctx=ctx,
    )
    conflict = wiki_rename(
        old_slug=old_b, new_slug=new_a2,
        actor="ruth", idempotency_key=key, ctx=ctx,
    )
    assert conflict["ok"] is False
    assert conflict.get("_idempotency_conflict") is True
    # Old b page must still exist (rename refused)
    assert (temp_vault / f"{old_b}.md").exists()

    # Cleanup
    (temp_vault / f"{new_a1}.md").unlink()
    (temp_vault / f"{old_b}.md").unlink()


def test_rename_log_entry(temp_vault: Path):
    old_slug = f"queries/f1_old_{uuid.uuid4().hex[:8]}"
    new_slug = f"queries/f1_new_{uuid.uuid4().hex[:8]}"
    _stage_page(temp_vault, old_slug)
    ctx = VaultContext(vault=temp_vault, mode=ADMIN)

    wiki_rename(
        old_slug=old_slug, new_slug=new_slug,
        actor="sam", ctx=ctx,
    )
    log = _read_log(temp_vault)
    assert "rename" in log and "sam" in log

    (temp_vault / f"{new_slug}.md").unlink()


# ─────────────── cross-tool invariants ───────────────


def test_fingerprint_is_order_independent():
    """params_fingerprint sorts keys — order shouldn't change the hash."""
    a = {"slug": "x", "content": "y", "project": "p"}
    b = {"project": "p", "content": "y", "slug": "x"}
    assert params_fingerprint(a) == params_fingerprint(b)


def test_fingerprint_detects_content_change():
    """A different content must produce a different fingerprint."""
    a = {"slug": "x", "content": "alpha"}
    b = {"slug": "x", "content": "beta"}
    assert params_fingerprint(a) != params_fingerprint(b)


def test_idempotency_store_is_isolated_per_vault(tmp_path: Path):
    """Two vaults must NOT share an idempotency record (per-vault store)."""
    vault_a = tmp_path / "vault_a"
    vault_b = tmp_path / "vault_b"
    for v in (vault_a, vault_b):
        v.mkdir(parents=True)
        (v / "raw").mkdir()
        (v / "_archive").mkdir()
        (v / "queries").mkdir()
        (v / "log.md").write_text("# log\n", encoding="utf-8")

    slug = f"queries/f1_iso_{uuid.uuid4().hex[:8]}"
    (vault_a / f"{slug}.md").write_text("---\ntitle: A\n---\n\nA\n", encoding="utf-8")
    (vault_b / f"{slug}.md").write_text("---\ntitle: B\n---\n\nB\n", encoding="utf-8")

    key = f"k-{uuid.uuid4().hex[:8]}"
    ctx_a = VaultContext(vault=vault_a, mode=WRITE)
    ctx_b = VaultContext(vault=vault_b, mode=WRITE)

    r_a = wiki_update(slug=slug, content="A\n", actor="alice",
                      idempotency_key=key, ctx=ctx_a)
    r_b = wiki_update(slug=slug, content="B\n", actor="bob",
                      idempotency_key=key, ctx=ctx_b)

    assert r_a["ok"] and r_b["ok"]
    # Each vault has its own store entry — same key, different fingerprint.
    store_a = _idem_store(vault_a)
    store_b = _idem_store(vault_b)
    assert store_a[key]["fingerprint"] != store_b[key]["fingerprint"]
