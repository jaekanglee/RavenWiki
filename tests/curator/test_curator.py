"""raven.curator.curator — execute() 본체 테스트.

검증:
- 정상 케이스 (vault + git + yaml → ok event 기록)
- sha invariant (error 시 sha 보존)
- first_run_strategy=skip_silent → skip
- 비활성 collection → skip
- yaml 검증 실패 → error
- collection not found → error
"""
from __future__ import annotations

import subprocess
import time
from pathlib import Path

import pytest

from raven.curator import curator, db, schema


@pytest.fixture
def vault_with_git(tmp_path: Path):
    """vault + git init + collections.yaml."""
    vault = tmp_path / "vault"
    vault.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=str(vault), check=True)
    subprocess.run(["git", "config", "user.email", "test@local"], cwd=str(vault), check=True)
    subprocess.run(["git", "config", "user.name", "tester"], cwd=str(vault), check=True)

    # collections.yaml
    meta = vault / "_meta"
    meta.mkdir()
    (meta / "collections.yaml").write_text(
        """schema_version: 1
collections:
  - id: harumoa
    paths: [content/harumoa]
    first_run_strategy: full_scan
"""
    )
    # content/harumoa
    (vault / "content" / "harumoa").mkdir(parents=True)
    (vault / "content" / "harumoa" / "first.md").write_text("# first\n")

    # initial commit
    subprocess.run(["git", "add", "-A"], cwd=str(vault), check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=str(vault), check=True)
    return vault


def test_execute_full_scan_first_run(vault_with_git, tmp_path):
    """first_run_strategy=full_scan + 첫 실행 → 모든 파일 recorded."""
    db_path = tmp_path / "curator.db"
    yaml_path = vault_with_git / "_meta" / "collections.yaml"

    result = curator.execute(
        collection_id="harumoa",
        vault_root=vault_with_git,
        collections_yaml_path=yaml_path,
        db_path=db_path,
        dry_run=False,
    )

    assert result.status == "ok"
    assert result.event_id is not None
    assert len(result.changes) >= 1
    assert any(c.path == "content/harumoa/first.md" for c in result.changes)

    # runs.last_run_sha advance
    conn = db.connect(db_path)
    run = db.get_run(conn, "harumoa")
    assert run is not None
    assert run["last_run_sha"] is not None
    assert run["last_status"] == "ok"

    # file_changes 기록됨
    n_changes = conn.execute("SELECT COUNT(*) FROM file_changes").fetchone()[0]
    assert n_changes >= 1
    conn.close()


def test_execute_no_changes_returns_ok(vault_with_git, tmp_path):
    """두 번째 실행 (변경 없음) → ok 빈 event."""
    db_path = tmp_path / "curator.db"
    yaml_path = vault_with_git / "_meta" / "collections.yaml"

    # 1st: full_scan
    r1 = curator.execute(
        "harumoa", vault_with_git, yaml_path, db_path=db_path, dry_run=False
    )
    assert r1.status == "ok"
    sha1 = (db.connect(db_path).execute(
        "SELECT last_run_sha FROM runs WHERE collection_id='harumoa'"
    ).fetchone() or [None])[0]

    # 2nd: no changes
    r2 = curator.execute(
        "harumoa", vault_with_git, yaml_path, db_path=db_path, dry_run=False
    )
    assert r2.status == "ok"
    assert r2.changes == []  # no changes since 1st
    assert "no changes" in r2.note


def test_execute_skip_silent_first_run(vault_with_git, tmp_path):
    """first_run_strategy=skip_silent + 첫 실행 → skip."""
    db_path = tmp_path / "curator.db"
    yaml_path = vault_with_git / "_meta" / "collections.yaml"
    yaml_path.write_text(
        """schema_version: 1
collections:
  - id: homeauto
    paths: [content/homeauto]
    first_run_strategy: skip_silent
"""
    )
    (vault_with_git / "content" / "homeauto").mkdir(parents=True)

    result = curator.execute(
        "homeauto", vault_with_git, yaml_path, db_path=db_path
    )
    assert result.status == "skipped"
    assert "skip_silent" in result.note


def test_execute_unknown_collection(vault_with_git, tmp_path):
    db_path = tmp_path / "curator.db"
    yaml_path = vault_with_git / "_meta" / "collections.yaml"

    result = curator.execute(
        "nonexistent", vault_with_git, yaml_path, db_path=db_path
    )
    assert result.status == "error"
    assert "not found" in result.note


def test_execute_archived_collection(vault_with_git, tmp_path):
    """archived collection → skip."""
    db_path = tmp_path / "curator.db"
    yaml_path = vault_with_git / "_meta" / "collections.yaml"
    yaml_path.write_text(
        """schema_version: 1
collections:
  - id: retired
    paths: [content/old]
    archived: true
    archived_at: '2026-06-01'
"""
    )
    result = curator.execute(
        "retired", vault_with_git, yaml_path, db_path=db_path
    )
    assert result.status == "skipped"
    assert "archived" in result.note


def test_execute_invalid_yaml(vault_with_git, tmp_path):
    """yaml 검증 실패 → error."""
    db_path = tmp_path / "curator.db"
    yaml_path = vault_with_git / "_meta" / "collections.yaml"
    yaml_path.write_text("schema_version: 1\ncollections:\n  - {}\n")  # missing paths

    result = curator.execute(
        "harumoa", vault_with_git, yaml_path, db_path=db_path
    )
    assert result.status == "error"
    assert "검증 실패" in result.note or "invalid" in result.note


def test_execute_dry_run_doesnt_write(vault_with_git, tmp_path):
    """dry-run은 DB write 안 함."""
    db_path = tmp_path / "curator.db"
    yaml_path = vault_with_git / "_meta" / "collections.yaml"

    result = curator.execute(
        "harumoa", vault_with_git, yaml_path, db_path=db_path, dry_run=True
    )
    assert result.status == "ok"

    conn = db.connect(db_path)
    n_events = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    assert n_events == 0  # dry-run은 기록 안 함
    n_runs = conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
    assert n_runs == 0
    conn.close()


def test_execute_sha_invariant_on_error(vault_with_git, tmp_path, monkeypatch):
    """error 발생 시 sha advance 안 함 (v3 invariant)."""
    db_path = tmp_path / "curator.db"
    yaml_path = vault_with_git / "_meta" / "collections.yaml"

    # 1st ok (full_scan)
    r1 = curator.execute(
        "harumoa", vault_with_git, yaml_path, db_path=db_path, dry_run=False
    )
    assert r1.status == "ok"
    conn = db.connect(db_path)
    sha_after_ok = db.get_run(conn, "harumoa")["last_run_sha"]
    conn.close()

    # vault에 변경 1건 추가 (두 번째 curator가 detect하게)
    (vault_with_git / "content" / "harumoa" / "second.md").write_text("# second\n")
    subprocess.run(["git", "add", "-A"], cwd=str(vault_with_git), check=True)
    subprocess.run(["git", "commit", "-q", "-m", "add second"], cwd=str(vault_with_git), check=True)

    # 2nd: idempotency_store에서 fail 시뮬레이션 → sha advance 안 됨
    import raven.curator.curator as curator_mod
    original_store = curator_mod.db.idempotency_store

    def fail_store(*a, **kw):
        raise RuntimeError("simulated failure")

    monkeypatch.setattr(curator_mod.db, "idempotency_store", fail_store)

    r2 = curator.execute(
        "harumoa", vault_with_git, yaml_path, db_path=db_path, dry_run=False
    )
    # sha advance 안 됨
    conn = db.connect(db_path)
    sha_after_err = db.get_run(conn, "harumoa")["last_run_sha"]
    conn.close()
    assert sha_after_err == sha_after_ok, "sha must NOT advance on error"

    # 복구 (다음 테스트가 영향 안 받게)
    monkeypatch.undo()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
