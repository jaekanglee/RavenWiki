"""raven.curator.db — curation_history.db 6 테이블 테스트.

핵심 invariant:
- runs.last_run_sha는 status='ok'일 때만 advance
- partial/error: sha는 stale 유지, last_status + consecutive_err만 갱신
"""
from __future__ import annotations

import time

import pytest

from raven.curator import db


@pytest.fixture
def fresh_db(tmp_path):
    """in-memory SQLite로 빠른 테스트."""
    db_path = tmp_path / "test_curator.db"
    conn = db.connect(db_path)
    db.init_schema(conn)
    yield conn
    conn.close()


# ───────────── schema init ─────────────

def test_init_schema_creates_tables(fresh_db):
    cur = fresh_db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )
    tables = [r[0] for r in cur.fetchall()]
    for expected in ("runs", "events", "file_changes", "reviews", "sync_reports", "idempotency"):
        assert expected in tables, f"missing table: {expected}"


def test_init_schema_user_version(fresh_db):
    cur = fresh_db.execute("PRAGMA user_version")
    assert cur.fetchone()[0] == db.SCHEMA_VERSION


# ───────────── runs ─────────────

def test_upsert_run_first_run(fresh_db):
    ts = int(time.time())
    db.upsert_run(fresh_db, "harumoa", "sha123", "ok", ts)
    run = db.get_run(fresh_db, "harumoa")
    assert run is not None
    assert run["last_run_sha"] == "sha123"
    assert run["last_status"] == "ok"
    assert run["consecutive_err"] == 0


def test_upsert_run_ok_advances_sha(fresh_db):
    """ok status → last_run_sha advance (v3 invariant)."""
    ts1 = int(time.time())
    db.upsert_run(fresh_db, "harumoa", "sha_v1", "ok", ts1)
    ts2 = ts1 + 100
    db.upsert_run(fresh_db, "harumoa", "sha_v2", "ok", ts2)
    run = db.get_run(fresh_db, "harumoa")
    assert run is not None
    assert run["last_run_sha"] == "sha_v2"


def test_upsert_run_error_preserves_sha(fresh_db):
    """error status → last_run_sha 보존 (재실행 시 동일 set 재처리)."""
    ts1 = int(time.time())
    db.upsert_run(fresh_db, "harumoa", "sha_v1", "ok", ts1)
    ts2 = ts1 + 100
    db.upsert_run(fresh_db, "harumoa", "sha_v1_would_be_advanced", "error", ts2)
    run = db.get_run(fresh_db, "harumoa")
    assert run is not None
    assert run["last_run_sha"] == "sha_v1", "sha should NOT advance on error"
    assert run["last_status"] == "error"


def test_upsert_run_partial_increments_error_count(fresh_db):
    ts1 = int(time.time())
    db.upsert_run(fresh_db, "harumoa", "sha_v1", "ok", ts1)
    ts2 = ts1 + 100
    db.upsert_run(fresh_db, "harumoa", None, "partial", ts2)
    run = db.get_run(fresh_db, "harumoa")
    assert run is not None
    assert run["consecutive_err"] == 1


# ───────────── idempotency ─────────────

def test_idempotency_miss_returns_none(fresh_db):
    assert db.idempotency_check(fresh_db, "wiki|merge|x|abc") is None


def test_idempotency_hit(fresh_db):
    ts = int(time.time())
    eid = db.insert_event(
        fresh_db, "harumoa", "manual", None, None, "ok", "hash1", None, ts
    )
    db.idempotency_store(fresh_db, "wiki|merge|x|abc", eid, ts)
    assert db.idempotency_check(fresh_db, "wiki|merge|x|abc") == eid


# ───────────── events + file_changes ─────────────

def test_event_then_file_change(fresh_db):
    ts = int(time.time())
    eid = db.insert_event(
        fresh_db, "harumoa", "cron", "base", "head", "ok", "ph", "note", ts
    )
    assert eid > 0
    cid = db.insert_file_change(fresh_db, eid, "content/harumoa/why.md", "modified", 1024, "fh")
    assert cid > 0
    row = fresh_db.execute(
        "SELECT path, change_type, curated FROM file_changes WHERE change_id = ?", (cid,)
    ).fetchone()
    assert row[0] == "content/harumoa/why.md"
    assert row[1] == "modified"
    assert row[2] == 0  # not yet curated


def test_mark_curated(fresh_db):
    ts = int(time.time())
    eid = db.insert_event(
        fresh_db, "harumoa", "cron", "base", "head", "ok", "ph", None, ts
    )
    cid = db.insert_file_change(fresh_db, eid, "x.md", "added", 0, "h")
    db.mark_curated(fresh_db, cid, ts + 1)
    row = fresh_db.execute(
        "SELECT curated, curated_at FROM file_changes WHERE change_id = ?", (cid,)
    ).fetchone()
    assert row[0] == 1


# ───────────── reviews ─────────────

def test_review_insert(fresh_db):
    ts = int(time.time())
    eid = db.insert_event(
        fresh_db, "harumoa", "manual", None, None, "ok", None, None, ts
    )
    cid = db.insert_file_change(fresh_db, eid, "x.md", "modified", 100, "h")
    rid = db.insert_review(fresh_db, cid, "reject", "duplicate content", "human:tester", ts + 1)
    assert rid > 0
    row = fresh_db.execute(
        "SELECT decision, reason, reviewer FROM reviews WHERE review_id = ?", (rid,)
    ).fetchone()
    assert row == ("reject", "duplicate content", "human:tester")


# ───────────── sync_reports ─────────────

def test_sync_report(fresh_db):
    ts = int(time.time())
    rid = db.insert_sync_report(
        fresh_db, "cron", True, "warn",
        '{"new":["finance"],"missing":[]}', "", ts,
    )
    assert rid > 0
    row = fresh_db.execute(
        "SELECT trigger, dry_run, policy FROM sync_reports WHERE report_id = ?", (rid,)
    ).fetchone()
    assert row == ("cron", 1, "warn")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
