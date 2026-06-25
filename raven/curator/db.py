"""raven.curator.db — curation_history.db 6 테이블 + 마이그레이션.

v3 합의안 6 테이블:
1. runs        — collection별 last_run_sha (멱등성 게이트)
2. events      — 실행 단위 immutable audit log
3. file_changes — 변경 파일 단위 (curated flag)
4. reviews     — 사람 결정 (decision + reason)
5. sync_reports — sync dry-run 리포트
6. idempotency -- cache_key (collection_id + payload_hash)

위치 기본값: `~/.local/share/raven/curator.db` (사용자 결정 Q2)
- vault 외부 = raven 시스템 운영 데이터
- vault 손상돼도 curator history는 살아있음

마이그레이션: PRAGMA user_version 기반 (1 → 2 → ...).
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Optional


SCHEMA_VERSION = 1

DEFAULT_DB_PATH = Path.home() / ".local" / "share" / "raven" / "curator.db"


SCHEMA_SQL = """
-- 1. collection별 last_run_sha (멱등성 게이트)
CREATE TABLE IF NOT EXISTS runs (
  collection_id   TEXT PRIMARY KEY,
  last_run_sha    TEXT,
  last_run_at     INTEGER NOT NULL,
  last_status     TEXT,                     -- ok | partial | error
  consecutive_err INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_runs_status ON runs(last_status);

-- 2. 실행 단위 immutable audit log
CREATE TABLE IF NOT EXISTS events (
  event_id        INTEGER PRIMARY KEY AUTOINCREMENT,
  ts              INTEGER NOT NULL,
  collection_id   TEXT NOT NULL,
  trigger         TEXT,                     -- cron | manual | sync
  base_sha        TEXT,
  result_sha      TEXT,
  status          TEXT,                     -- ok | partial | error | skipped
  payload_hash    TEXT,
  note            TEXT
);
CREATE INDEX IF NOT EXISTS idx_events_collection ON events(collection_id, ts DESC);
CREATE INDEX IF NOT EXISTS idx_events_status ON events(status);

-- 3. 변경된 파일 단위 기록
CREATE TABLE IF NOT EXISTS file_changes (
  change_id       INTEGER PRIMARY KEY AUTOINCREMENT,
  event_id        INTEGER NOT NULL,
  path            TEXT NOT NULL,
  change_type     TEXT,                     -- added | modified | deleted
  size_bytes      INTEGER,
  payload_hash    TEXT,
  curated         INTEGER DEFAULT 0,
  curated_at      INTEGER,
  UNIQUE(event_id, path),
  FOREIGN KEY(event_id) REFERENCES events(event_id)
);
CREATE INDEX IF NOT EXISTS idx_file_changes_path ON file_changes(path);
CREATE INDEX IF NOT EXISTS idx_file_changes_curated ON file_changes(curated, path);

-- 4. 사람 결정
CREATE TABLE IF NOT EXISTS reviews (
  review_id       INTEGER PRIMARY KEY AUTOINCREMENT,
  change_id       INTEGER NOT NULL,
  ts              INTEGER NOT NULL,
  decision        TEXT,                     -- accept | reject | defer
  reason          TEXT,
  reviewer        TEXT,
  FOREIGN KEY(change_id) REFERENCES file_changes(change_id)
);
CREATE INDEX IF NOT EXISTS idx_reviews_collection ON reviews(change_id);
-- 필요 시: CREATE INDEX idx_reviews_coll_status ON reviews(change_id, decision);

-- 5. sync dry-run 리포트
CREATE TABLE IF NOT EXISTS sync_reports (
  report_id       INTEGER PRIMARY KEY AUTOINCREMENT,
  ts              INTEGER NOT NULL,
  trigger         TEXT,                     -- cron | manual
  dry_run         INTEGER DEFAULT 1,
  policy          TEXT,                     -- warn | conflict
  findings_json   TEXT,
  would_archive   TEXT
);

-- 6. 멱등성 cache (payload_hash 중복 처리 방지)
CREATE TABLE IF NOT EXISTS idempotency (
  cache_key       TEXT PRIMARY KEY,
  event_id        INTEGER NOT NULL,
  cached_at       INTEGER NOT NULL,
  FOREIGN KEY(event_id) REFERENCES events(event_id)
);
"""


def connect(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """DB 연결. 기본 위치: ~/.local/share/raven/curator.db."""
    if db_path is None:
        db_path = DEFAULT_DB_PATH
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), isolation_level=None)  # autocommit; 트랜잭션은 BEGIN/END 명시
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    """schema_version 확인 + 마이그레이션 적용."""
    cur = conn.execute("PRAGMA user_version")
    current = cur.fetchone()[0]
    if current == 0:
        # fresh init
        conn.executescript(SCHEMA_SQL)
        conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
    elif current < SCHEMA_VERSION:
        # 미래의 마이그레이션: if current == 1 and target == 2: ...
        # v3에선 v1 → v2 마이그레이션 없음. 추후 확장.
        raise NotImplementedError(
            f"migration from user_version={current} to {SCHEMA_VERSION} not implemented"
        )
    elif current > SCHEMA_VERSION:
        raise RuntimeError(
            f"db schema version {current} > code schema version {SCHEMA_VERSION}; "
            "upgrade raven or use older db"
        )


@contextmanager
def transaction(conn: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    """트랜잭션 컨텍스트. BEGIN IMMEDIATE로 동시성 잠금."""
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield conn
    except Exception:
        conn.execute("ROLLBACK")
        raise
    else:
        conn.execute("COMMIT")


# ────────────────────────── runs helpers ──────────────────────────

def upsert_run(
    conn: sqlite3.Connection,
    collection_id: str,
    last_run_sha: Optional[str],
    status: str,
    ts: int,
) -> None:
    """runs 갱신. consecutive_err 자동 계산.

    Args:
        last_run_sha: None이면 first run. status='ok'/'partial'/'error'/'skipped'.
    """
    if status == "ok":
        # 성공 시에만 last_run_sha advance (v3 합의 invariant)
        conn.execute(
            """
            INSERT INTO runs (collection_id, last_run_sha, last_run_at, last_status, consecutive_err)
            VALUES (?, ?, ?, 'ok', 0)
            ON CONFLICT(collection_id) DO UPDATE SET
                last_run_sha = excluded.last_run_sha,
                last_run_at = excluded.last_run_at,
                last_status = 'ok',
                consecutive_err = 0
            """,
            (collection_id, last_run_sha, ts),
        )
    else:
        # partial/error: sha는 stale 유지, last_status + consecutive_err 만 갱신
        conn.execute(
            """
            INSERT INTO runs (collection_id, last_run_sha, last_run_at, last_status, consecutive_err)
            VALUES (?, NULL, ?, ?, 1)
            ON CONFLICT(collection_id) DO UPDATE SET
                last_run_at = excluded.last_run_at,
                last_status = excluded.last_status,
                consecutive_err = runs.consecutive_err + 1
            """,
            (collection_id, ts, status),
        )


def get_run(conn: sqlite3.Connection, collection_id: str) -> Optional[dict]:
    row = conn.execute(
        "SELECT collection_id, last_run_sha, last_run_at, last_status, consecutive_err "
        "FROM runs WHERE collection_id = ?",
        (collection_id,),
    ).fetchone()
    if row is None:
        return None
    return {
        "collection_id": row[0],
        "last_run_sha": row[1],
        "last_run_at": row[2],
        "last_status": row[3],
        "consecutive_err": row[4],
    }


# ────────────────────────── idempotency ──────────────────────────

def idempotency_check(conn: sqlite3.Connection, cache_key: str) -> Optional[int]:
    """캐시 hit 시 event_id 반환, miss 시 None."""
    row = conn.execute(
        "SELECT event_id FROM idempotency WHERE cache_key = ?", (cache_key,)
    ).fetchone()
    return row[0] if row else None


def idempotency_store(
    conn: sqlite3.Connection, cache_key: str, event_id: int, ts: int
) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO idempotency (cache_key, event_id, cached_at) VALUES (?, ?, ?)",
        (cache_key, event_id, ts),
    )


# ────────────────────────── events / file_changes ──────────────────────────

def insert_event(
    conn: sqlite3.Connection,
    collection_id: str,
    trigger: str,
    base_sha: Optional[str],
    result_sha: Optional[str],
    status: str,
    payload_hash: Optional[str],
    note: Optional[str],
    ts: int,
) -> int:
    cur = conn.execute(
        """
        INSERT INTO events (ts, collection_id, trigger, base_sha, result_sha, status, payload_hash, note)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (ts, collection_id, trigger, base_sha, result_sha, status, payload_hash, note),
    )
    return int(cur.lastrowid or 0)


def insert_file_change(
    conn: sqlite3.Connection,
    event_id: int,
    path: str,
    change_type: str,
    size_bytes: Optional[int],
    payload_hash: Optional[str],
) -> int:
    cur = conn.execute(
        """
        INSERT OR IGNORE INTO file_changes
            (event_id, path, change_type, size_bytes, payload_hash)
        VALUES (?, ?, ?, ?, ?)
        """,
        (event_id, path, change_type, size_bytes, payload_hash),
    )
    return int(cur.lastrowid or 0)  # 0 if IGNORE 충돌


def mark_curated(conn: sqlite3.Connection, change_id: int, ts: int) -> None:
    conn.execute(
        "UPDATE file_changes SET curated = 1, curated_at = ? WHERE change_id = ?",
        (ts, change_id),
    )


# ────────────────────────── reviews ──────────────────────────

def insert_review(
    conn: sqlite3.Connection,
    change_id: int,
    decision: str,
    reason: str,
    reviewer: str,
    ts: int,
) -> int:
    cur = conn.execute(
        """
        INSERT INTO reviews (change_id, ts, decision, reason, reviewer)
        VALUES (?, ?, ?, ?, ?)
        """,
        (change_id, ts, decision, reason, reviewer),
    )
    return int(cur.lastrowid or 0)


def reject_pattern_for_collection(
    conn: sqlite3.Connection, collection_id: str
) -> list[tuple[str, int]]:
    """collection별 reject 패턴 집계 (v3 §5 reviews.collection_id 인덱스)."""
    rows = conn.execute(
        """
        SELECT r.decision, COUNT(*) as n
        FROM reviews r
        JOIN file_changes fc ON r.change_id = fc.change_id
        JOIN events e ON fc.event_id = e.event_id
        WHERE e.collection_id = ? AND r.decision = 'reject'
        GROUP BY r.decision
        """,
        (collection_id,),
    ).fetchall()
    return [(r[0], r[1]) for r in rows]


# ────────────────────────── sync_reports ──────────────────────────

def insert_sync_report(
    conn: sqlite3.Connection,
    trigger: str,
    dry_run: bool,
    policy: str,
    findings_json: str,
    would_archive: str,
    ts: int,
) -> int:
    cur = conn.execute(
        """
        INSERT INTO sync_reports (ts, trigger, dry_run, policy, findings_json, would_archive)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (ts, trigger, int(dry_run), policy, findings_json, would_archive),
    )
    return int(cur.lastrowid or 0)
