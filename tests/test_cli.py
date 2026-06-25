"""Tests for CLI commands (vault create, page new/delete, meta sync).

Uses typer.testing.CliRunner for in-process invocation.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from typer.testing import CliRunner

from wikisys.cli.__main__ import app
from wikisys.core.registry import registry


runner = CliRunner()


@pytest.fixture
def fresh_env(monkeypatch):
    """Isolated WIKI_VAULTS_DIR + clean target dir."""
    vaults_root = Path(tempfile.mkdtemp(prefix="wikisys-cli-vaults-"))
    target_root = Path(tempfile.mkdtemp(prefix="wikisys-cli-target-"))
    monkeypatch.setenv("WIKI_VAULTS_DIR", str(vaults_root))
    yield {"vaults_root": vaults_root, "target_root": target_root}
    shutil.rmtree(vaults_root, ignore_errors=True)
    shutil.rmtree(target_root, ignore_errors=True)


# ─── vault create ───────────────────────────────────────────


def test_cli_vault_create_bootstrap(fresh_env):
    target = fresh_env["target_root"] / "myvault"
    result = runner.invoke(app, [
        "vault", "create", "myvault", str(target),
    ])
    assert result.exit_code == 0, result.stderr
    assert "created" in result.stdout
    assert "bootstrapped" in result.stdout
    assert (target / "content").is_dir()
    assert (target / "_meta" / "SCHEMA.md").is_file()
    assert (target / "_meta" / "RULES.md").is_file()


def test_cli_vault_create_no_bootstrap(fresh_env):
    target = fresh_env["target_root"] / "existing"
    target.mkdir()
    (target / "old-doc.md").write_text("# old\n")
    result = runner.invoke(app, [
        "vault", "create", "existing", str(target), "--no-bootstrap",
    ])
    assert result.exit_code == 0, result.stderr
    assert "no bootstrap" in result.stdout
    assert not (target / "content").exists()
    assert (target / "old-doc.md").read_text() == "# old\n"


# ─── page new: auto prefix ──────────────────────────────────


def test_cli_page_new_auto_prefix(fresh_env):
    """wikisys page new foo → content/foo.md (auto prefix)."""
    # bootstrap a vault first
    target = fresh_env["target_root"] / "v1"
    runner.invoke(app, ["vault", "create", "v1", str(target)])
    # create page with short name
    result = runner.invoke(app, [
        "page", "new", "hello", "--title", "Hello", "--vault", "v1",
    ])
    assert result.exit_code == 0, result.stderr
    assert "content/hello" in result.stdout
    assert (target / "content" / "hello.md").is_file()


def test_cli_page_new_explicit_meta_prefix(fresh_env):
    """wikisys page new _meta/welcome → _meta/welcome.md (explicit prefix preserved)."""
    target = fresh_env["target_root"] / "v2"
    runner.invoke(app, ["vault", "create", "v2", str(target)])
    result = runner.invoke(app, [
        "page", "new", "_meta/welcome", "--title", "Welcome", "--vault", "v2",
    ])
    assert result.exit_code == 0, result.stderr
    assert (target / "_meta" / "welcome.md").is_file()


def test_cli_page_new_explicit_content_prefix(fresh_env):
    """wikisys page new content/foo → content/foo.md (explicit prefix preserved)."""
    target = fresh_env["target_root"] / "v3"
    runner.invoke(app, ["vault", "create", "v3", str(target)])
    result = runner.invoke(app, [
        "page", "new", "content/explicit", "--title", "X", "--vault", "v3",
    ])
    assert result.exit_code == 0, result.stderr
    assert (target / "content" / "explicit.md").is_file()


def test_cli_page_new_uses_frontmatter(fresh_env):
    """Created page has proper YAML frontmatter (title, type, created, updated)."""
    target = fresh_env["target_root"] / "v4"
    runner.invoke(app, ["vault", "create", "v4", str(target)])
    runner.invoke(app, [
        "page", "new", "foo", "--title", "Foo", "--type", "tool", "--tags", "core,ai",
        "--vault", "v4",
    ])
    text = (target / "content" / "foo.md").read_text()
    assert text.startswith("---\n")
    assert "title: Foo" in text
    assert "type: tool" in text
    assert "tags: [core, ai]" in text
    assert "created:" in text
    assert "updated:" in text


def test_cli_page_new_nested_slug(fresh_env):
    target = fresh_env["target_root"] / "v5"
    runner.invoke(app, ["vault", "create", "v5", str(target)])
    result = runner.invoke(app, [
        "page", "new", "content/sub/nested", "--title", "N", "--vault", "v5",
    ])
    assert result.exit_code == 0, result.stderr
    assert (target / "content" / "sub" / "nested.md").is_file()


# ─── page new: slug validation ──────────────────────────────


def test_cli_page_new_rejects_parent_traversal(fresh_env):
    target = fresh_env["target_root"] / "v6"
    runner.invoke(app, ["vault", "create", "v6", str(target)])
    result = runner.invoke(app, [
        "page", "new", "../../../tmp/pwn", "--title", "X", "--vault", "v6",
    ])
    # CliRunner mixes stdout/stderr differently — check both
    out = (result.stdout or "") + (result.stderr or "")
    assert result.exit_code != 0
    assert "invalid slug" in out


def test_cli_page_new_rejects_absolute_path(fresh_env):
    target = fresh_env["target_root"] / "v7"
    runner.invoke(app, ["vault", "create", "v7", str(target)])
    result = runner.invoke(app, [
        "page", "new", "/etc/passwd-test", "--title", "X", "--vault", "v7",
    ])
    out = (result.stdout or "") + (result.stderr or "")
    assert result.exit_code != 0
    assert "invalid slug" in out


def test_cli_page_new_rejects_tilde(fresh_env):
    target = fresh_env["target_root"] / "v8"
    runner.invoke(app, ["vault", "create", "v8", str(target)])
    result = runner.invoke(app, [
        "page", "new", "~/.ssh-test", "--title", "X", "--vault", "v8",
    ])
    out = (result.stdout or "") + (result.stderr or "")
    assert result.exit_code != 0
    assert "invalid slug" in out


def test_cli_page_new_rejects_existing(fresh_env):
    target = fresh_env["target_root"] / "v9"
    runner.invoke(app, ["vault", "create", "v9", str(target)])
    runner.invoke(app, [
        "page", "new", "dup", "--title", "X", "--vault", "v9",
    ])
    result = runner.invoke(app, [
        "page", "new", "dup", "--title", "Y", "--vault", "v9",
    ])
    out = (result.stdout or "") + (result.stderr or "")
    assert result.exit_code != 0
    assert "exists" in out


# ─── page delete: archive mirror ────────────────────────────


def test_cli_page_delete_archives_with_mirror_path(fresh_env):
    target = fresh_env["target_root"] / "v10"
    runner.invoke(app, ["vault", "create", "v10", str(target)])
    runner.invoke(app, [
        "page", "new", "content/a/b/c", "--title", "X", "--vault", "v10",
    ])
    assert (target / "content" / "a" / "b" / "c.md").is_file()

    result = runner.invoke(app, [
        "page", "delete", "content/a/b/c", "--force", "--vault", "v10",
    ])
    assert result.exit_code == 0, result.stderr
    # original gone
    assert not (target / "content" / "a" / "b" / "c.md").exists()
    # archive mirrors path
    archive_files = list((target / "_archive" / "content" / "a" / "b").glob("c-*.md"))
    assert len(archive_files) == 1
    assert "c-" in archive_files[0].name


def test_cli_page_delete_validates_slug(fresh_env):
    target = fresh_env["target_root"] / "v11"
    runner.invoke(app, ["vault", "create", "v11", str(target)])
    result = runner.invoke(app, [
        "page", "delete", "../../etc", "--force", "--vault", "v11",
    ])
    out = (result.stdout or "") + (result.stderr or "")
    assert result.exit_code != 0
    assert "invalid slug" in out


# ─── meta sync ──────────────────────────────────────────────


def test_cli_meta_sync_copies_when_missing(fresh_env):
    target = fresh_env["target_root"] / "v12"
    runner.invoke(app, ["vault", "create", "v12", str(target), "--no-bootstrap"])
    # _meta/ does not exist — sync_meta creates it
    result = runner.invoke(app, ["meta", "sync", "--vault", "v12"])
    assert result.exit_code == 0, result.stderr
    assert (target / "_meta" / "SCHEMA.md").is_file()
    assert (target / "_meta" / "RULES.md").is_file()


def test_cli_meta_sync_overwrites_existing(fresh_env):
    target = fresh_env["target_root"] / "v13"
    runner.invoke(app, ["vault", "create", "v13", str(target)])
    # customize RULES.md
    (target / "_meta" / "RULES.md").write_text("# CUSTOM OLD\n")
    result = runner.invoke(app, ["meta", "sync", "--vault", "v13"])
    assert result.exit_code == 0, result.stderr
    # overwritten
    assert "Vault Editing Rules" in (target / "_meta" / "RULES.md").read_text()


def test_cli_meta_sync_json_out(fresh_env):
    target = fresh_env["target_root"] / "v14"
    runner.invoke(app, ["vault", "create", "v14", str(target)])
    result = runner.invoke(app, ["meta", "sync", "--vault", "v14", "--json"])
    assert result.exit_code == 0, result.stderr
    data = json.loads(result.stdout)
    assert "copied" in data
    assert "SCHEMA.md" in data["copied"]
    assert "RULES.md" in data["copied"]
