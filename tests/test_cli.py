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

from raven.cli.__main__ import app
from raven.core.registry import registry


runner = CliRunner()


@pytest.fixture
def fresh_env(monkeypatch):
    """Isolated WIKI_VAULTS_DIR + clean target dir."""
    vaults_root = Path(tempfile.mkdtemp(prefix="raven-cli-vaults-"))
    target_root = Path(tempfile.mkdtemp(prefix="raven-cli-target-"))
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
    assert (target / "_meta" / "system" / "SCHEMA.md").is_file()
    assert (target / "_meta" / "system" / "RULES.md").is_file()


def test_cli_vault_create_no_bootstrap(fresh_env):
    target = fresh_env["target_root"] / "existing"
    target.mkdir()
    (target / "old-doc.md").write_text("# old\n")
    result = runner.invoke(app, [
        "vault", "create", "existing", str(target), "--no-bootstrap",
    ])
    assert result.exit_code == 0, result.stderr
    combined = (result.stdout or "") + (result.stderr or "")
    assert "no bootstrap" in combined
    # v0.4: empty dirs are created (so users have a writable starting point)
    assert (target / "content").is_dir()
    assert (target / "_meta").is_dir()
    assert not (target / "_meta" / "system" / "SCHEMA.md").exists()
    # but existing files are not touched
    assert (target / "old-doc.md").read_text() == "# old\n"


# ─── page new: auto prefix ──────────────────────────────────


def test_cli_page_new_auto_prefix(fresh_env):
    """raven page new foo → content/foo.md (auto prefix)."""
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
    """raven page new _meta/welcome → _meta/welcome.md (explicit prefix preserved)."""
    target = fresh_env["target_root"] / "v2"
    runner.invoke(app, ["vault", "create", "v2", str(target)])
    result = runner.invoke(app, [
        "page", "new", "_meta/welcome", "--title", "Welcome", "--vault", "v2",
    ])
    assert result.exit_code == 0, result.stderr
    assert (target / "_meta" / "welcome.md").is_file()


def test_cli_page_new_explicit_content_prefix(fresh_env):
    """raven page new content/foo → content/foo.md (explicit prefix preserved)."""
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
    # Lite sync_meta default copies user-facing bootstrap files.
    result = runner.invoke(app, ["meta", "sync", "--vault", "v12"])
    assert result.exit_code == 0, result.stderr
    assert (target / "_meta" / "system" / "SCHEMA.md").is_file()
    assert (target / "_meta" / "system" / "RULES.md").is_file()
    assert (target / "_meta" / "system" / "AGENTS.md").is_file()
    assert (target / "_meta" / "agents" / "PROJECT-WORKFLOW.md").is_file()
    # No internal agent/ subdir created (Lite policy)
    assert not (target / "_meta" / "agent").exists()
    # No OPERATIONS.md
    assert not (target / "_meta" / "system" / "OPERATIONS.md").exists()


def test_cli_meta_sync_does_not_overwrite_by_default(fresh_env):
    """Default sync_meta is Lite + no-force (does NOT overwrite)."""
    target = fresh_env["target_root"] / "v13"
    runner.invoke(app, ["vault", "create", "v13", str(target)])
    # customize RULES.md in new location
    rules_path = target / "_meta" / "system" / "RULES.md"
    rules_path.write_text("# CUSTOM OLD\n")
    result = runner.invoke(app, ["meta", "sync", "--vault", "v13"])
    assert result.exit_code == 0, result.stderr
    # NOT overwritten (Lite policy: user-edited protected)
    assert "# CUSTOM OLD" in rules_path.read_text()


def test_cli_meta_sync_json_out(fresh_env):
    target = fresh_env["target_root"] / "v13"
    runner.invoke(app, ["vault", "create", "v13", str(target), "--no-bootstrap"])
    result = runner.invoke(app, ["meta", "sync", "--vault", "v13", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    # Lite: user-facing files copied (no internal agent/, no OPERATIONS, no raven-policy)
    # v0.5.5+ silent-write fix: log.md already exists from Vault.create() → skipped, not copied
    assert "_meta/system/SCHEMA.md" in data["copied"]
    assert "_meta/system/RULES.md" in data["copied"]
    assert "_meta/system/AGENTS.md" in data["copied"]
    assert "_meta/agents/PROJECT-WORKFLOW.md" in data["copied"]
    assert "log.md" not in data["copied"]
    assert "log.md" in data["skipped"]
    assert "_meta/agent/README.md" not in data["copied"]
    assert "_meta/system/OPERATIONS.md" not in data["copied"]


def test_cli_meta_sync_full_with_force(fresh_env):
    """v0.7.6+: --full is now equivalent to --lite (Tier 1 internal sync ❌).

    v0.7.1+ Lite bootstrap 정책: 사용자 vault는 도구 표면만, Tier 1 leak 방지.
    full 옵션은 deprecated (lite와 동일하게 처리) — Tier 1 internal sync 거부.
    """
    target = fresh_env["target_root"] / "vfull"
    runner.invoke(app, ["vault", "create", "vfull", str(target), "--no-bootstrap"])
    result = runner.invoke(app, ["meta", "sync", "--full", "--force", "--vault", "vfull"])
    assert result.exit_code == 0, result.stderr
    # Lite 5종만 복사
    assert (target / "_meta" / "system" / "SCHEMA.md").is_file()
    assert (target / "_meta" / "system" / "RULES.md").is_file()
    assert (target / "_meta" / "system" / "AGENTS.md").is_file()
    assert (target / "_meta" / "agents" / "PROJECT-WORKFLOW.md").is_file()
    assert (target / "log.md").is_file()
    # Tier 1 internal ❌ (Tier 1 leak 방지)
    assert not (target / "_meta" / "system" / "OPERATIONS.md").exists()
    assert not (target / "_meta" / "agent" / "README.md").exists()
    assert not (target / "raven-policy.md").exists()


# ─── vault clone ────────────────────────────────────────────


def test_cli_vault_clone_copies_content_only_by_default(fresh_env):
    """Lite default (v2026-06-26): content/ copied, _meta/ NOT copied."""
    src = fresh_env["target_root"] / "src"
    runner.invoke(app, ["vault", "create", "src", str(src), "--bootstrap"])
    # Add some content
    (src / "content" / "hello.md").write_text("# Hello\n")
    (src / "content" / "sub").mkdir(exist_ok=True)
    (src / "content" / "sub" / "nested.md").write_text("# Nested\n")
    # Clone (no flag = Lite default)
    dst = fresh_env["target_root"] / "dst"
    result = runner.invoke(app, ["vault", "clone", "src", "dst", str(dst)])
    assert result.exit_code == 0, result.stdout + result.stderr
    assert "cloned" in result.stdout
    # content copied
    assert (dst / "content" / "hello.md").is_file()
    assert (dst / "content" / "sub" / "nested.md").is_file()
    # _meta/ NOT copied (Lite policy)
    assert not (dst / "_meta" / "system" / "SCHEMA.md").exists()
    # registered
    reg_list = runner.invoke(app, ["vault", "list", "--json"])
    names = [v["name"] for v in json.loads(reg_list.stdout)]
    assert "dst" in names


def test_cli_vault_clone_default_is_lite(fresh_env):
    """Lite default (v2026-06-26): _meta/ NOT copied unless --copy-meta."""
    src = fresh_env["target_root"] / "src2"
    runner.invoke(app, ["vault", "create", "src2", str(src), "--bootstrap"])
    dst = fresh_env["target_root"] / "dst2"
    # No flag — Lite default (no _meta copy)
    result = runner.invoke(app, ["vault", "clone", "src2", "dst2", str(dst)])
    assert result.exit_code == 0
    assert (dst / "content").is_dir()
    # _meta/ exists but empty (Lite: no copy)
    assert (dst / "_meta").is_dir()
    assert not (dst / "_meta" / "system" / "SCHEMA.md").exists()


def test_cli_vault_clone_explicit_copy_meta(fresh_env):
    """--copy-meta explicit flag copies _meta/ (with Tier 1 leak warning)."""
    src = fresh_env["target_root"] / "src2b"
    runner.invoke(app, ["vault", "create", "src2b", str(src), "--bootstrap"])
    dst = fresh_env["target_root"] / "dst2b"
    result = runner.invoke(
        app, ["vault", "clone", "src2b", "dst2b", str(dst), "--copy-meta"]
    )
    assert result.exit_code == 0
    # _meta/system/SCHEMA.md copied
    assert (dst / "_meta" / "system" / "SCHEMA.md").is_file()


def test_cli_vault_clone_data_only(fresh_env):
    """--data-only: content only, _meta/ empty (no copy)."""
    src = fresh_env["target_root"] / "src2c"
    runner.invoke(app, ["vault", "create", "src2c", str(src), "--bootstrap"])
    dst = fresh_env["target_root"] / "dst2c"
    result = runner.invoke(
        app, ["vault", "clone", "src2c", "dst2c", str(dst), "--data-only"]
    )
    assert result.exit_code == 0
    assert (dst / "content").is_dir()
    assert (dst / "_meta").is_dir()
    assert not (dst / "_meta" / "system" / "SCHEMA.md").exists()


def test_cli_vault_clone_duplicate_name_rejected(fresh_env):
    src = fresh_env["target_root"] / "src3"
    dst = fresh_env["target_root"] / "dst3"
    runner.invoke(app, ["vault", "create", "src3", str(src)])
    runner.invoke(app, ["vault", "create", "dst3", str(dst)])
    result = runner.invoke(app, ["vault", "clone", "src3", "dst3", str(dst)])
    assert result.exit_code == 1
    combined = (result.stdout or "") + (result.stderr or "")
    assert "already registered" in combined


def test_cli_vault_clone_unknown_src(fresh_env):
    result = runner.invoke(app, [
        "vault", "clone", "nonexistent", "new", str(fresh_env["target_root"] / "new")
    ])
    assert result.exit_code == 1
    combined = (result.stdout or "") + (result.stderr or "")
    assert "not found" in combined


def test_cli_vault_import_is_alias_for_clone(fresh_env):
    src = fresh_env["target_root"] / "imp"
    runner.invoke(app, ["vault", "create", "imp", str(src)])
    dst = fresh_env["target_root"] / "imp2"
    result = runner.invoke(app, ["vault", "import", "imp", "imp2", str(dst)])
    assert result.exit_code == 0, result.stdout
    assert "cloned" in result.stdout


# ─── archive sub-app ────────────────────────────────────────


def _make_archived_at(vault_root: Path, original_slug: str, ts: "datetime") -> Path:
    """Helper: create archived file with given slug + timestamp."""
    ts_str = ts.strftime("%Y%m%d-%H%M%S")
    parts = original_slug.split("/")
    stem = parts[-1]
    parent_dir = vault_root / "_archive" / "/".join(parts[:-1])
    parent_dir.mkdir(parents=True, exist_ok=True)
    fp = parent_dir / f"{stem}-{ts_str}.md"
    fp.write_text(f"# from {original_slug}\n", encoding="utf-8")
    return fp


def test_cli_archive_list_empty(fresh_env):
    target = fresh_env["target_root"] / "al1"
    runner.invoke(app, ["vault", "create", "al1", str(target)])
    result = runner.invoke(app, ["archive", "list", "--vault", "al1"])
    assert result.exit_code == 0
    assert "no archived files" in result.stdout


def test_cli_archive_list_shows_entries(fresh_env):
    from datetime import datetime, timedelta
    target = fresh_env["target_root"] / "al2"
    runner.invoke(app, ["vault", "create", "al2", str(target)])
    _make_archived_at(target, "content/foo", datetime.now() - timedelta(days=10))
    _make_archived_at(target, "content/bar", datetime.now() - timedelta(days=100))
    result = runner.invoke(app, ["archive", "list", "--vault", "al2"])
    assert result.exit_code == 0
    assert "2 archived" in result.stdout
    assert "content/foo" in result.stdout
    assert "content/bar" in result.stdout


def test_cli_archive_clean_dry_run(fresh_env):
    from datetime import datetime, timedelta
    target = fresh_env["target_root"] / "ac1"
    runner.invoke(app, ["vault", "create", "ac1", str(target)])
    fp = _make_archived_at(target, "content/old", datetime.now() - timedelta(days=100))
    result = runner.invoke(app, ["archive", "clean", "--older-than", "30", "--vault", "ac1"])
    assert result.exit_code == 0
    assert "DRY-RUN" in result.stdout
    # file still exists
    assert fp.exists()


def test_cli_archive_clean_apply_deletes(fresh_env):
    from datetime import datetime, timedelta
    target = fresh_env["target_root"] / "ac2"
    runner.invoke(app, ["vault", "create", "ac2", str(target)])
    fp = _make_archived_at(target, "content/old", datetime.now() - timedelta(days=100))
    result = runner.invoke(app, ["archive", "clean", "--older-than", "30", "--vault", "ac2", "--apply"])
    assert result.exit_code == 0
    assert "cleaned 1" in result.stdout
    assert not fp.exists()


def test_cli_archive_restore_basic(fresh_env):
    from datetime import datetime
    target = fresh_env["target_root"] / "ar1"
    runner.invoke(app, ["vault", "create", "ar1", str(target)])
    fp = _make_archived_at(target, "content/foo", datetime.now())
    rel = str(fp.relative_to(target))
    result = runner.invoke(app, ["archive", "restore", rel, "--vault", "ar1"])
    assert result.exit_code == 0, result.stdout + result.stderr
    assert "restored" in result.stdout
    assert (target / "content" / "foo.md").is_file()
    assert not fp.exists()


def test_cli_archive_restore_outside_archive_rejected(fresh_env):
    target = fresh_env["target_root"] / "ar2"
    runner.invoke(app, ["vault", "create", "ar2", str(target)])
    result = runner.invoke(app, ["archive", "restore", "content/foo.md", "--vault", "ar2"])
    assert result.exit_code == 1
    combined = (result.stdout or "") + (result.stderr or "")
    assert "not under _archive" in combined


def test_cli_archive_json_output(fresh_env):
    from datetime import datetime, timedelta
    target = fresh_env["target_root"] / "aj1"
    runner.invoke(app, ["vault", "create", "aj1", str(target)])
    _make_archived_at(target, "content/x", datetime.now() - timedelta(days=50))
    result = runner.invoke(app, ["archive", "list", "--vault", "aj1", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert len(data) == 1
    assert data[0]["original_slug"] == "content/x"
