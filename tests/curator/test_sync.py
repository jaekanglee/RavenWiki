"""raven.curator.sync — sync 흐름 테스트."""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from raven.curator import sync as curator_sync


@pytest.fixture
def vault_with_yaml(tmp_path: Path):
    """vault + _meta/collections.yaml + git."""
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "_meta").mkdir()
    (vault / "content").mkdir()
    (vault / "content" / "harumoa").mkdir()
    (vault / "content" / "homeauto").mkdir()
    (vault / "_meta" / "collections.yaml").write_text(
        """schema_version: 1
collections:
  - id: harumoa
    paths: [content/harumoa]
    first_run_strategy: skip_silent
  - id: homeauto
    paths: [content/homeauto]
"""
    )
    return vault


def test_sync_no_diff(vault_with_yaml, tmp_path):
    """FS = yaml → ok, no findings."""
    db_path = tmp_path / "curator.db"
    yaml_path = vault_with_yaml / "_meta" / "collections.yaml"

    report = curator_sync.sync(
        vault_root=vault_with_yaml,
        collections_yaml_path=yaml_path,
        db_path=db_path,
    )
    assert report.errors == []
    assert report.would_archive == []
    assert all(f.kind == "ok" for f in report.findings)


def test_sync_missing_in_fs(vault_with_yaml, tmp_path):
    """yaml O, FS X → missing finding."""
    db_path = tmp_path / "curator.db"
    yaml_path = vault_with_yaml / "_meta" / "collections.yaml"
    # homeauto 폴더 삭제
    import shutil
    shutil.rmtree(vault_with_yaml / "content" / "homeauto")

    report = curator_sync.sync(
        vault_root=vault_with_yaml,
        collections_yaml_path=yaml_path,
        db_path=db_path,
    )
    missing = [f for f in report.findings if f.kind == "missing"]
    assert len(missing) == 1
    assert missing[0].collection_id == "homeauto"


def test_sync_candidate_in_fs(vault_with_yaml, tmp_path):
    """FS O, yaml X → candidate finding."""
    db_path = tmp_path / "curator.db"
    yaml_path = vault_with_yaml / "_meta" / "collections.yaml"
    # 새 폴더 추가
    (vault_with_yaml / "content" / "finance").mkdir()

    report = curator_sync.sync(
        vault_root=vault_with_yaml,
        collections_yaml_path=yaml_path,
        db_path=db_path,
    )
    candidates = [f for f in report.findings if f.kind == "candidate"]
    assert len(candidates) == 1
    assert "finance" in candidates[0].path


def test_sync_grace_archive(vault_with_yaml, tmp_path):
    """missing + grace ≥ N → would_archive."""
    db_path = tmp_path / "curator.db"
    yaml_path = vault_with_yaml / "_meta" / "collections.yaml"
    # yaml을 archived: true + archived_at: 30일 전으로
    yaml_path.write_text(
        """schema_version: 1
collections:
  - id: harumoa
    paths: [content/harumoa]
  - id: old
    paths: [content/old]
    archived: true
    archived_at: '2026-06-01'
"""
    )
    import datetime as dt
    # grace 7일이면 6/1 + 7일 = 6/8 부터 archive 후보
    # today가 2026-06-26이라 6/1 → 25일 경과 > 7 grace
    # → archive 후보

    report = curator_sync.sync(
        vault_root=vault_with_yaml,
        collections_yaml_path=yaml_path,
        grace_days=7,
        db_path=db_path,
    )
    # 6/26 - 6/1 = 25일 > 7
    assert "old" in report.would_archive


def test_sync_apply_archive(vault_with_yaml, tmp_path):
    """apply=True → yaml에 archived=true 기록."""
    db_path = tmp_path / "curator.db"
    yaml_path = vault_with_yaml / "_meta" / "collections.yaml"
    yaml_path.write_text(
        """schema_version: 1
collections:
  - id: harumoa
    paths: [content/harumoa]
  - id: old
    paths: [content/old]
    archived: true
    archived_at: '2026-06-01'
"""
    )

    report = curator_sync.sync(
        vault_root=vault_with_yaml,
        collections_yaml_path=yaml_path,
        apply_archive=True,
        db_path=db_path,
    )
    # yaml 다시 읽고 archived 검증
    from raven.curator.schema import load_and_validate
    y2 = load_and_validate(yaml_path)
    old = next(c for c in y2.collections if c.id == "old")
    # archived_at이 오늘로 갱신됨 (이미 있었으면 유지)
    assert old.archived is True
    assert old.archived_at is not None


def test_sync_policy_conflict(vault_with_yaml, tmp_path):
    """policy=conflict → MISSING이 error로 승격."""
    db_path = tmp_path / "curator.db"
    yaml_path = vault_with_yaml / "_meta" / "collections.yaml"
    yaml_path.write_text(
        """schema_version: 1
collections:
  - id: harumoa
    paths: [content/harumoa]
  - id: old
    paths: [content/old]
    archived: true
    archived_at: '2026-06-01'
"""
    )

    report = curator_sync.sync(
        vault_root=vault_with_yaml,
        collections_yaml_path=yaml_path,
        policy="conflict",
        grace_days=7,
        db_path=db_path,
    )
    # grace 7일 + 25일 경과 = hard stop
    assert len(report.errors) >= 1
    assert "old" in str(report.errors)


def test_sync_writes_sync_reports(vault_with_yaml, tmp_path):
    """sync 실행 시 sync_reports 테이블에 기록."""
    db_path = tmp_path / "curator.db"
    yaml_path = vault_with_yaml / "_meta" / "collections.yaml"

    curator_sync.sync(
        vault_root=vault_with_yaml,
        collections_yaml_path=yaml_path,
        db_path=db_path,
    )
    # DB에서 sync_reports 검증
    from raven.curator import db
    conn = db.connect(db_path)
    n = conn.execute("SELECT COUNT(*) FROM sync_reports").fetchone()[0]
    assert n == 1
    conn.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
