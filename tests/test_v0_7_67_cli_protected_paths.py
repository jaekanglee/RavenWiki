"""v0.7.67 (평가 B#1/B#4) — CLI 보호 경로 정합성 + _note_create 계약 편입.

pre-v0.7.67:
  - `raven page new raw/x`는 성공했지만 API/MCP는 raw/를 항상 거부했다
    ("raw/는 불변" 정책이 CLI 한 표면에서만 뚫려 있었음).
  - `_note_create`는 contracts.write_page를 거치지 않는 5번째 쓰기 경로였고,
    `--project`가 harumoa/homeauto/resume/design-spec 4개로 하드코딩돼 있었다.
"""
from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

from raven.cli.__main__ import app

runner = CliRunner()


@pytest.fixture
def fresh_env(monkeypatch):
    vaults_root = Path(tempfile.mkdtemp(prefix="raven-cli-vaults-"))
    target_root = Path(tempfile.mkdtemp(prefix="raven-cli-target-"))
    monkeypatch.setenv("WIKI_VAULTS_DIR", str(vaults_root))
    yield {"vaults_root": vaults_root, "target_root": target_root}
    shutil.rmtree(vaults_root, ignore_errors=True)
    shutil.rmtree(target_root, ignore_errors=True)


def test_page_new_rejects_raw_prefix(fresh_env):
    target = fresh_env["target_root"] / "v1"
    runner.invoke(app, ["vault", "create", "v1", str(target)])
    result = runner.invoke(app, [
        "page", "new", "raw/x", "--title", "X", "--vault", "v1",
    ])
    assert result.exit_code != 0
    assert not (target / "raw" / "x.md").exists()


def test_page_new_rejects_content_raw_prefix(fresh_env):
    target = fresh_env["target_root"] / "v2"
    runner.invoke(app, ["vault", "create", "v2", str(target)])
    result = runner.invoke(app, [
        "page", "new", "content/raw/x", "--title", "X", "--vault", "v2",
    ])
    assert result.exit_code != 0
    assert not (target / "content" / "raw" / "x.md").exists()


def test_page_new_meta_prefix_still_allowed(fresh_env):
    """_meta/ 직접 쓰기는 기존 CLI 능력으로 유지된다 (raw/만 차단)."""
    target = fresh_env["target_root"] / "v3"
    runner.invoke(app, ["vault", "create", "v3", str(target)])
    result = runner.invoke(app, [
        "page", "new", "_meta/custom", "--title", "Custom", "--vault", "v3",
    ])
    assert result.exit_code == 0, result.stderr
    assert (target / "_meta" / "custom.md").is_file()


def test_note_create_accepts_free_form_project(fresh_env):
    """평가 B#4: project는 더 이상 4개 하드코딩 allowlist가 아니다."""
    target = fresh_env["target_root"] / "v4"
    runner.invoke(app, ["vault", "create", "v4", str(target)])
    result = runner.invoke(app, [
        "note", "decision",
        "--project", "any-project-name",
        "--slug", "why-x", "--title", "Why X", "--vault", "v4",
    ])
    assert result.exit_code == 0, result.stderr
    assert (target / "content" / "any-project-name" / "decisions" / "why-x.md").is_file()


def test_note_create_rejects_empty_project(fresh_env):
    target = fresh_env["target_root"] / "v5"
    runner.invoke(app, ["vault", "create", "v5", str(target)])
    result = runner.invoke(app, [
        "note", "decision",
        "--project", "  ",
        "--slug", "why-x", "--title", "Why X", "--vault", "v5",
    ])
    assert result.exit_code != 0


def test_note_create_uses_write_page_contract(fresh_env):
    """created/updated + tags가 write_page 계약대로 기록된다."""
    from raven.core.frontmatter import parse

    target = fresh_env["target_root"] / "v6"
    runner.invoke(app, ["vault", "create", "v6", str(target)])
    runner.invoke(app, [
        "note", "concept",
        "--project", "widgets", "--slug", "gizmo", "--title", "Gizmo", "--vault", "v6",
    ])
    fp = target / "content" / "widgets" / "concepts" / "gizmo.md"
    meta, _ = parse(fp.read_text(encoding="utf-8"))
    assert meta["type"] == "concept"
    assert set(meta["tags"]) == {"concept", "widgets"}
    assert "created" in meta and "updated" in meta
