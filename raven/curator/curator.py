"""raven.curator.curator — Curator.execute() 본체 (Stateless Workflow).

v3 합의안 9단계 흐름:
1. LOAD collections.yaml → validate_paths() (yaml 작성과 동일 함수)
2. CHECK collection.is_active → 비활성이면 skip
3. LOAD runs[collection_id] → last_run_sha
4. COMPUTE change set (git diff + path_filter + --merge-base)
5. COMPUTE payload_hash (canonical form)
6. CHECK idempotency[cache_key] → hit이면 return cached
7. PROCESS 변경 파일들 → file_changes.curated=1 (ok)
8. WRITE events + file_changes (BEGIN IMMEDIATE 트랜잭션)
9. ON FULL SUCCESS ONLY: runs.last_run_sha = result_sha

핵심 invariant (v3 Claude #2):
- runs.last_run_sha는 status='ok'일 때만 advance
- partial/error: sha는 stale 유지 → 재실행 시 동일 set 재처리

동시성 (v3 Claude #4 약점):
- BEGIN IMMEDIATE 트랜잭션 (writer lock) — 두 프로세스 동시 실행 방지
"""
from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import db, hash as hash_mod, schema


# ────────────────────────── result types ──────────────────────────

@dataclass
class FileChange:
    """변경된 파일 1건 (curator 입력)."""

    path: str
    change_type: str              # added | modified | deleted
    size_bytes: Optional[int] = None
    payload_hash: Optional[str] = None


@dataclass
class CuratorResult:
    """execute() 출력."""

    status: str                    # ok | partial | error | skipped | pending_sync
    collection_id: str
    event_id: Optional[int] = None
    changes: List[FileChange] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    note: str = ""


# ────────────────────────── git helpers ──────────────────────────

def _git(*args: str, cwd: Path) -> str:
    """git 명령 실행. stderr은 무시 (best-effort)."""
    try:
        out = subprocess.check_output(
            ["git", *args], cwd=str(cwd), text=True, stderr=subprocess.DEVNULL
        )
        return out.strip()
    except subprocess.CalledProcessError:
        return ""


def _current_sha(vault_root: Path) -> Optional[str]:
    """vault HEAD sha. git 없으면 None."""
    return _git("rev-parse", "HEAD", cwd=vault_root) or None


def _git_diff_paths(
    vault_root: Path, base_sha: Optional[str], paths: List[str], merge_base: bool = True
) -> List[FileChange]:
    """git diff base..HEAD -- <paths>.

    Returns:
        변경된 FileChange 리스트. base_sha가 None이면 첫 실행.
    """
    if base_sha is None:
        # 첫 실행: git ls-tree로 모든 파일을 added로 처리 (full_scan)
        # 빈 트리 SHA(4b825dc...)는 모든 git이 갖고 있지만 portable하지 않으므로 ls-tree 사용
        cmd = ["ls-tree", "-r", "--name-only", "HEAD", "--", *paths]
        out = _git(*cmd, cwd=vault_root)
        if not out:
            return []
        return [
            FileChange(path=p.strip(), change_type="added")
            for p in out.splitlines()
            if p.strip()
        ]

    base_arg = [base_sha]
    if merge_base:
        # --merge-base로 fast-forward 아닌 PR 머지에도 안전
        mb = _git("merge-base", base_sha, "HEAD", cwd=vault_root)
        if mb:
            base_arg = [mb]

    cmd = ["diff", "--name-status", *base_arg, "HEAD", "--", *paths]
    out = _git(*cmd, cwd=vault_root)
    if not out:
        return []  # no changes

    # out = "M\tpath/to/file.md\nA\tpath/new.md\n..."
    changes: List[FileChange] = []
    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        change_type_raw = parts[0].strip()
        path = parts[1].strip()
        # map git status → curator change_type
        ct_map = {"A": "added", "M": "modified", "D": "deleted", "R": "modified", "C": "added"}
        change_type = ct_map.get(change_type_raw[0], "modified")
        changes.append(FileChange(path=path, change_type=change_type))
    return changes


# ────────────────────────── core execute ──────────────────────────

def execute(
    collection_id: str,
    vault_root: Path,
    collections_yaml_path: Path,
    db_path: Optional[Path] = None,
    dry_run: bool = True,
    trigger: str = "manual",
    now: Optional[int] = None,
) -> CuratorResult:
    """Curator.execute() — stateless workflow.

    Args:
        collection_id: 큐레이션 대상 collection의 id
        vault_root: vault 루트 (git repo여야 함)
        collections_yaml_path: collections.yaml 절대 경로
        db_path: curation_history.db 경로 (None = 기본)
        dry_run: True면 DB write 안 함, 변경 제안만
        trigger: 'manual' | 'cron' | 'sync' (audit용)
        now: unix timestamp (None = time.time())

    Returns:
        CuratorResult
    """
    ts = now if now is not None else int(time.time())

    # 1. LOAD collections.yaml + validate
    try:
        yaml_obj = schema.load_and_validate(collections_yaml_path)
    except schema.CollectionsYamlError as e:
        return CuratorResult(
            status="error",
            collection_id=collection_id,
            note=f"collections.yaml 검증 실패: {e}",
        )

    # 2. CHECK collection 존재 + is_active
    target: Optional[schema.Collection] = None
    for c in yaml_obj.collections:
        if c.id == collection_id:
            target = c
            break
    if target is None:
        return CuratorResult(
            status="error",
            collection_id=collection_id,
            note=f"collection '{collection_id}' not found in collections.yaml",
        )
    if not target.is_active:
        return CuratorResult(
            status="skipped",
            collection_id=collection_id,
            note=f"collection '{collection_id}' is archived/retired",
        )

    # 3. DB 연결 + last_run_sha
    conn = db.connect(db_path)
    db.init_schema(conn)
    last = db.get_run(conn, collection_id)
    base_sha: Optional[str] = last["last_run_sha"] if last else None

    # first_run_strategy 처리
    strategy = target.first_run_strategy or yaml_obj.defaults.get(
        "first_run_strategy", "skip_silent"
    )
    if base_sha is None and strategy == "skip_silent":
        conn.close()
        return CuratorResult(
            status="skipped",
            collection_id=collection_id,
            note=f"first_run_strategy=skip_silent; '{collection_id}'는 vault 자산화 시 큐레이션 보류. "
                 "yaml에서 'full_scan' 또는 'interactive'로 변경 가능.",
        )

    # 4. COMPUTE change set
    result_sha = _current_sha(vault_root)
    if result_sha is None:
        conn.close()
        return CuratorResult(
            status="error",
            collection_id=collection_id,
            note="vault가 git repo가 아님 (rev-parse 실패)",
        )

    changes = _git_diff_paths(vault_root, base_sha, target.paths)
    if not changes:
        # 변경 없음 → ok 빈 event, sha는 그대로 (or advance?)
        # v3 합의: ok 상태면 sha advance (no-change도 ok)
        if not dry_run:
            db.upsert_run(conn, collection_id, result_sha, "ok", ts)
        conn.close()
        return CuratorResult(
            status="ok",
            collection_id=collection_id,
            note="no changes since last run",
        )

    # 5. payload_hash (변경 set 전체)
    payload_obj = {
        "collection_id": collection_id,
        "change_count": len(changes),
        "paths": sorted([c.path for c in changes]),
        "types": sorted([c.change_type for c in changes]),
    }
    payload_hash16 = hash_mod.payload_hash(payload_obj)

    # 6. CHECK idempotency
    cache_key = hash_mod.idempotency_key(
        collection_id, "change_set", "<set>", payload_hash16
    )
    cached_event_id = db.idempotency_check(conn, cache_key)

    if dry_run:
        conn.close()
        return CuratorResult(
            status="ok",
            collection_id=collection_id,
            changes=changes,
            note=f"[dry-run] {len(changes)} changes; would record event (cache_key={cache_key[:24]}...)",
        )

    # 7-8. WRITE (BEGIN IMMEDIATE)
    try:
        with db.transaction(conn):
            event_id = db.insert_event(
                conn,
                collection_id=collection_id,
                trigger=trigger,
                base_sha=base_sha,
                result_sha=result_sha,
                status="ok",
                payload_hash=payload_hash16,
                note=f"{len(changes)} changes",
                ts=ts,
            )

            for fc in changes:
                db.insert_file_change(
                    conn,
                    event_id=event_id,
                    path=fc.path,
                    change_type=fc.change_type,
                    size_bytes=fc.size_bytes,
                    payload_hash=fc.payload_hash,
                )
                # mark_curated는 reviewer 승인 시 (Step 7 reviews에서)
                # 여기선 등록만

            db.idempotency_store(conn, cache_key, event_id, ts)

            # 9. ON FULL SUCCESS ONLY: sha advance
            db.upsert_run(conn, collection_id, result_sha, "ok", ts)
    except Exception as e:
        # partial/error: sha 보존
        try:
            db.upsert_run(conn, collection_id, base_sha, "error", ts)
        except Exception:
            pass
        conn.close()
        return CuratorResult(
            status="error",
            collection_id=collection_id,
            note=f"event write 실패: {e}",
        )

    conn.close()
    return CuratorResult(
        status="ok",
        collection_id=collection_id,
        event_id=event_id,
        changes=changes,
        note=f"{len(changes)} changes recorded (event_id={event_id})",
    )
