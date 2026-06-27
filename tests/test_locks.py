"""test_locks.py — M5/F4 advisory lock helper unit tests.

Pure-helper tests for ``mcp.tools.{acquire,check,release,extend}_lock``.
No write tools involved — that's ``test_mcp_concurrency.py``'s job.
Every test uses a fresh ``tmp_path`` so they don't see each other's state.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from raven.mcp.tools import (
    ANONYMOUS_ACTOR,
    DEFAULT_LOCK_TTL_SECONDS,
    acquire_lock,
    check_lock,
    extend_lock,
    release_lock,
    _load_locks_store,
)

# ─────────────── acquire_lock ───────────────


def test_acquire_lock_returns_holder(temp_vault: Path):
    r = acquire_lock(temp_vault, "foo", "alice")
    assert r["ok"] is True
    assert r["lock"]["actor"] == "alice"
    assert r["lock"]["ttl_seconds"] == DEFAULT_LOCK_TTL_SECONDS
    assert "expires_at" in r["lock"]
    assert "since" in r["lock"]


def test_acquire_lock_persists_to_disk(temp_vault: Path):
    acquire_lock(temp_vault, "foo", "alice")
    path = temp_vault / ".mcp" / "locks.json"
    assert path.exists(), "locks.json must be written"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert "foo" in data
    assert data["foo"]["actor"] == "alice"


def test_acquire_lock_second_actor_conflicts(temp_vault: Path):
    acquire_lock(temp_vault, "foo", "alice")
    r = acquire_lock(temp_vault, "foo", "bob")
    assert r["ok"] is False
    assert r.get("_advisory_conflict") is True
    assert r["lock"]["actor"] == "alice"


def test_acquire_lock_same_actor_refreshes_ttl(temp_vault: Path):
    """Re-acquiring your own lock is the canonical 'extend' workflow."""
    r1 = acquire_lock(temp_vault, "foo", "alice", ttl_seconds=60)
    time.sleep(0.02)
    r2 = acquire_lock(temp_vault, "foo", "alice", ttl_seconds=900)
    assert r1["ok"] is True and r2["ok"] is True
    assert r2["lock"]["ttl_seconds"] == 900


def test_acquire_lock_custom_ttl(temp_vault: Path):
    r = acquire_lock(temp_vault, "foo", "alice", ttl_seconds=42)
    assert r["lock"]["ttl_seconds"] == 42


def test_acquire_lock_normalizes_actor(temp_vault: Path):
    """Whitespace-only actor falls back to ANONYMOUS_ACTOR (F1 contract)."""
    r = acquire_lock(temp_vault, "foo", "   ")
    assert r["lock"]["actor"] == ANONYMOUS_ACTOR


# ─────────────── check_lock ───────────────


def test_check_lock_none_when_empty(temp_vault: Path):
    assert check_lock(temp_vault, "absent") is None


def test_check_lock_returns_active_claim(temp_vault: Path):
    acquire_lock(temp_vault, "foo", "alice")
    holder = check_lock(temp_vault, "foo")
    assert holder is not None
    assert holder["actor"] == "alice"
    # F4 spec: every holder carries the explicit advisory label.
    assert holder["_advisory_conflict"] is True


def test_check_lock_gc_expired(temp_vault: Path):
    """Expired claims must NOT be returned and must be cleaned up."""
    r = acquire_lock(temp_vault, "foo", "alice", ttl_seconds=1)
    assert r["ok"] is True
    time.sleep(1.2)
    holder = check_lock(temp_vault, "foo")
    assert holder is None
    # The store should have been GC'd.
    path = temp_vault / ".mcp" / "locks.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert "foo" not in data


def test_check_lock_does_not_gc_active(temp_vault: Path):
    acquire_lock(temp_vault, "foo", "alice", ttl_seconds=300)
    holder = check_lock(temp_vault, "foo")
    assert holder is not None
    # Still in the store.
    path = temp_vault / ".mcp" / "locks.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert "foo" in data


# ─────────────── release_lock ───────────────


def test_release_lock_by_holder(temp_vault: Path):
    acquire_lock(temp_vault, "foo", "alice")
    assert release_lock(temp_vault, "foo", "alice") is True
    assert check_lock(temp_vault, "foo") is None


def test_release_lock_by_non_holder_returns_false(temp_vault: Path):
    acquire_lock(temp_vault, "foo", "alice")
    # Bob cannot drop Alice's claim.
    assert release_lock(temp_vault, "foo", "bob") is False
    # Lock survives.
    assert check_lock(temp_vault, "foo") is not None


def test_release_lock_no_claim_returns_false(temp_vault: Path):
    assert release_lock(temp_vault, "absent", "alice") is False


# ─────────────── extend_lock ───────────────


def test_extend_lock_by_holder(temp_vault: Path):
    acquire_lock(temp_vault, "foo", "alice", ttl_seconds=60)
    r = extend_lock(temp_vault, "foo", "alice", ttl_seconds=600)
    assert r["ok"] is True
    assert r["lock"]["ttl_seconds"] == 600


def test_extend_lock_by_non_holder_conflicts(temp_vault: Path):
    acquire_lock(temp_vault, "foo", "alice")
    r = extend_lock(temp_vault, "foo", "bob")
    assert r["ok"] is False
    assert r.get("_advisory_conflict") is True
    assert r["lock"]["actor"] == "alice"


def test_extend_lock_no_active_returns_conflict(temp_vault: Path):
    r = extend_lock(temp_vault, "absent", "alice")
    assert r["ok"] is False
    assert r.get("_advisory_conflict") is True


def test_extend_lock_expired_returns_conflict(temp_vault: Path):
    acquire_lock(temp_vault, "foo", "alice", ttl_seconds=1)
    time.sleep(1.2)
    r = extend_lock(temp_vault, "foo", "alice")
    assert r["ok"] is False
    assert r.get("_advisory_conflict") is True
    # Expired claim is GC'd by the next check_lock / acquire_lock.


# ─────────────── store invariants ───────────────


def test_corrupted_store_is_treated_as_empty(temp_vault: Path, capsys):
    """A broken locks.json must never block a write."""
    (temp_vault / ".mcp").mkdir(parents=True, exist_ok=True)
    (temp_vault / ".mcp" / "locks.json").write_text("not json{{", encoding="utf-8")
    assert check_lock(temp_vault, "foo") is None
    # And we can recover — a fresh acquire writes a valid file.
    r = acquire_lock(temp_vault, "foo", "alice")
    assert r["ok"] is True


def test_independent_slugs(temp_vault: Path):
    """Locking one slug must not affect another."""
    acquire_lock(temp_vault, "foo", "alice")
    r = acquire_lock(temp_vault, "bar", "bob")
    assert r["ok"] is True
    foo_holder = check_lock(temp_vault, "foo")
    bar_holder = check_lock(temp_vault, "bar")
    assert foo_holder is not None and bar_holder is not None
    assert foo_holder["actor"] == "alice"
    assert bar_holder["actor"] == "bob"


# ─────────────── fixture ───────────────


@pytest.fixture
def temp_vault(tmp_path: Path) -> Path:
    """Minimal vault dir — just enough for the .mcp/ write path."""
    (tmp_path / ".mcp").mkdir(parents=True, exist_ok=True)
    return tmp_path
