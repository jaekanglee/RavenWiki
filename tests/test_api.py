"""Tests for raven.api — REST endpoints after v0.3.1 migration.

Covers the 5 write endpoints (vaults/create, pages POST/PUT/DELETE) plus
slug validation, frontmatter unification, and archive mirror.
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Use TestClient from FastAPI (stdlib starlette)
from fastapi.testclient import TestClient

from raven.api.server import app
from raven.core.registry import VAULTS_ROOT, registry
from raven.core.vault import Vault


@pytest.fixture
def isolated_env(monkeypatch):
    """Redirect WIKI_VAULTS_DIR + provide a clean target dir."""
    reg_root = Path(tempfile.mkdtemp(prefix="raven-api-reg-"))
    target_root = Path(tempfile.mkdtemp(prefix="raven-api-target-"))
    monkeypatch.setenv("WIKI_VAULTS_DIR", str(reg_root))
    yield {"reg_root": reg_root, "target_root": target_root}
    shutil.rmtree(reg_root, ignore_errors=True)
    shutil.rmtree(target_root, ignore_errors=True)


@pytest.fixture
def client():
    return TestClient(app)


# ─── vault create ────────────────────────────────────────────


def test_api_vault_create_with_bootstrap(client, isolated_env):
    target = isolated_env["target_root"] / "v1"
    resp = client.post("/api/vaults/create", json={
        "name": "v1", "path": str(target), "mode": "personal", "bootstrap": True,
    })
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["ok"] is True
    assert data["vault"]["bootstrapped"] is True
    assert (target / "content").is_dir()
    assert (target / "_meta" / "SCHEMA.md").is_file()
    assert (target / "_meta" / "RULES.md").is_file()


def test_api_vault_create_no_bootstrap(client, isolated_env):
    target = isolated_env["target_root"] / "v2"
    resp = client.post("/api/vaults/create", json={
        "name": "v2", "path": str(target), "bootstrap": False,
    })
    assert resp.status_code == 200
    # v0.4: empty dirs exist, but templates not copied
    assert (target / "content").is_dir()
    assert (target / "_meta").is_dir()
    assert not (target / "_meta" / "SCHEMA.md").exists()


def test_api_vault_create_duplicate_name(client, isolated_env):
    target = isolated_env["target_root"] / "v3"
    client.post("/api/vaults/create", json={"name": "v3", "path": str(target)})
    resp = client.post("/api/vaults/create", json={"name": "v3", "path": str(target)})
    assert resp.status_code == 409


# ─── page create ─────────────────────────────────────────────


def test_api_page_create_auto_prefix(client, isolated_env):
    target = isolated_env["target_root"] / "vp"
    client.post("/api/vaults/create", json={"name": "vp", "path": str(target), "bootstrap": False})
    resp = client.post("/api/vaults/vp/pages", json={
        "slug": "hello", "title": "Hello", "type": "concept", "tags": ["a", "b"],
    })
    assert resp.status_code == 200, resp.text
    assert resp.json()["slug"] == "content/hello"
    assert (target / "content" / "hello.md").is_file()


def test_api_page_create_explicit_meta(client, isolated_env):
    target = isolated_env["target_root"] / "vp2"
    client.post("/api/vaults/create", json={"name": "vp2", "path": str(target), "bootstrap": False})
    resp = client.post("/api/vaults/vp2/pages", json={
        "slug": "_meta/welcome", "title": "W",
    })
    assert resp.status_code == 200
    assert (target / "_meta" / "welcome.md").is_file()


def test_api_page_create_rejects_parent_traversal(client, isolated_env):
    target = isolated_env["target_root"] / "vp3"
    client.post("/api/vaults/create", json={"name": "vp3", "path": str(target), "bootstrap": False})
    resp = client.post("/api/vaults/vp3/pages", json={
        "slug": "../../etc/passwd", "title": "X",
    })
    assert resp.status_code == 400
    assert "invalid slug" in resp.text.lower()


def test_api_page_create_rejects_absolute(client, isolated_env):
    target = isolated_env["target_root"] / "vp4"
    client.post("/api/vaults/create", json={"name": "vp4", "path": str(target), "bootstrap": False})
    resp = client.post("/api/vaults/vp4/pages", json={
        "slug": "/etc/passwd", "title": "X",
    })
    assert resp.status_code == 400


def test_api_page_create_duplicate(client, isolated_env):
    target = isolated_env["target_root"] / "vp5"
    client.post("/api/vaults/create", json={"name": "vp5", "path": str(target), "bootstrap": False})
    client.post("/api/vaults/vp5/pages", json={"slug": "dup", "title": "X"})
    resp = client.post("/api/vaults/vp5/pages", json={"slug": "dup", "title": "Y"})
    assert resp.status_code == 409


# ─── page update (created 보존 검증) ──────────────────────


def test_api_page_update_preserves_created(client, isolated_env):
    target = isolated_env["target_root"] / "vp6"
    client.post("/api/vaults/create", json={"name": "vp6", "path": str(target), "bootstrap": False})
    client.post("/api/vaults/vp6/pages", json={"slug": "u", "title": "Original"})

    # First update — should preserve created (set by create)
    resp = client.put("/api/vaults/vp6/pages/content/u", json={
        "content": "new body", "title": "Updated",
    })
    assert resp.status_code == 200
    created_after_update = resp.json()["created"]

    # Read back via get_page
    get_resp = client.get("/api/vaults/vp6/pages/content/u")
    fm = get_resp.json()["frontmatter"]
    today = __import__("datetime").date.today().isoformat()
    assert fm["created"] == created_after_update
    assert fm["updated"] == today
    assert fm["title"] == "Updated"
    assert "new body" in get_resp.json()["content"]


def test_api_page_update_rejects_bad_slug(client, isolated_env):
    target = isolated_env["target_root"] / "vp7"
    client.post("/api/vaults/create", json={"name": "vp7", "path": str(target), "bootstrap": False})
    # URL `..` is normalized by starlette before reaching the route → 404 (which is also safe).
    # We test a slug that survives URL encoding but is still bad: tilde expansion
    resp = client.put("/api/vaults/vp7/pages/~/.ssh-test", json={"content": "x"})
    assert resp.status_code == 400
    assert "invalid slug" in resp.text.lower()


# ─── page delete (mirror 경로) ────────────────────────────


def test_api_page_delete_archives_with_mirror(client, isolated_env):
    target = isolated_env["target_root"] / "vp8"
    client.post("/api/vaults/create", json={"name": "vp8", "path": str(target), "bootstrap": False})
    client.post("/api/vaults/vp8/pages", json={"slug": "content/sub/nested", "title": "N"})
    resp = client.delete("/api/vaults/vp8/pages/content/sub/nested")
    assert resp.status_code == 200
    # Original gone
    assert not (target / "content" / "sub" / "nested.md").exists()
    # Archived at mirror path
    archive_dir = target / "_archive" / "content" / "sub"
    assert archive_dir.is_dir()
    archived = list(archive_dir.glob("nested-*.md"))
    assert len(archived) == 1


def test_api_page_delete_rejects_bad_slug(client, isolated_env):
    target = isolated_env["target_root"] / "vp9"
    client.post("/api/vaults/create", json={"name": "vp9", "path": str(target), "bootstrap": False})
    # Tilde expansion in URL survives starlette routing
    resp = client.delete("/api/vaults/vp9/pages/~/.ssh-test")
    assert resp.status_code == 400
    assert "invalid slug" in resp.text.lower()


def test_api_page_delete_missing(client, isolated_env):
    target = isolated_env["target_root"] / "vp10"
    client.post("/api/vaults/create", json={"name": "vp10", "path": str(target), "bootstrap": False})
    resp = client.delete("/api/vaults/vp10/pages/content/missing")
    assert resp.status_code == 404


# ─── read endpoints 회귀 ─────────────────────────────────


def test_api_list_pages_still_works(client, isolated_env):
    target = isolated_env["target_root"] / "vp11"
    client.post("/api/vaults/create", json={"name": "vp11", "path": str(target), "bootstrap": False})
    client.post("/api/vaults/vp11/pages", json={"slug": "content/a", "title": "A"})
    client.post("/api/vaults/vp11/pages", json={"slug": "content/b", "title": "B"})
    resp = client.get("/api/vaults/vp11/pages")
    assert resp.status_code == 200
    pages = resp.json()["pages"]
    slugs = [p["slug"] for p in pages]
    assert "content/a" in slugs
    assert "content/b" in slugs


def test_api_vaults_list(client, isolated_env):
    target = isolated_env["target_root"] / "vl"
    client.post("/api/vaults/create", json={"name": "vl", "path": str(target), "bootstrap": False})
    resp = client.get("/api/vaults")
    assert resp.status_code == 200
    names = [v["name"] for v in resp.json()["vaults"]]
    assert "vl" in names


# ─── vault clone endpoint ───────────────────────────────────


def test_api_clone_vault_copies_content(client, isolated_env):
    src = isolated_env["target_root"] / "csrc"
    client.post("/api/vaults/create", json={"name": "csrc", "path": str(src), "bootstrap": False})
    (src / "content").mkdir(parents=True, exist_ok=True)  # bootstrap=False didn't create it
    (src / "content" / "hello.md").write_text("# Hi\n")
    dst = isolated_env["target_root"] / "cdst"
    resp = client.post("/api/vaults/clone", json={
        "src": "csrc", "name": "cdst", "path": str(dst),
    })
    assert resp.status_code == 200, resp.text
    assert (dst / "content" / "hello.md").is_file()


def test_api_clone_vault_duplicate_name_rejected(client, isolated_env):
    src = isolated_env["target_root"] / "csrc2"
    dst = isolated_env["target_root"] / "cdst2"
    client.post("/api/vaults/create", json={"name": "csrc2", "path": str(src), "bootstrap": False})
    client.post("/api/vaults/create", json={"name": "cdst2", "path": str(dst), "bootstrap": False})
    resp = client.post("/api/vaults/clone", json={"src": "csrc2", "name": "cdst2", "path": str(dst)})
    assert resp.status_code == 409


def test_api_clone_unknown_src_rejected(client, isolated_env):
    dst = isolated_env["target_root"] / "cdst3"
    resp = client.post("/api/vaults/clone", json={
        "src": "nonexistent", "name": "cdst3", "path": str(dst),
    })
    assert resp.status_code == 404


# ─── archive endpoints ──────────────────────────────────────


def test_api_archive_list_empty(client, isolated_env):
    target = isolated_env["target_root"] / "av1"
    client.post("/api/vaults/create", json={"name": "av1", "path": str(target), "bootstrap": False})
    resp = client.get("/api/vaults/av1/archive")
    assert resp.status_code == 200
    assert resp.json()["count"] == 0


def test_api_archive_clean_dry_run(client, isolated_env):
    import datetime as _dt
    target = isolated_env["target_root"] / "av2"
    client.post("/api/vaults/create", json={"name": "av2", "path": str(target), "bootstrap": False})
    ts = (_dt.datetime.now() - _dt.timedelta(days=100)).strftime("%Y%m%d-%H%M%S")
    (target / "_archive" / "content").mkdir(parents=True)
    (target / "_archive" / "content" / f"old-{ts}.md").write_text("# old\n")
    resp = client.post("/api/vaults/av2/archive/clean?older_than=30&apply=false")
    assert resp.status_code == 200
    data = resp.json()
    assert data["dry_run"] is True
    assert data["would_delete_count"] == 1
    # file still exists
    assert (target / "_archive" / "content" / f"old-{ts}.md").exists()


def test_api_archive_restore_basic(client, isolated_env):
    import datetime as _dt
    target = isolated_env["target_root"] / "av3"
    client.post("/api/vaults/create", json={"name": "av3", "path": str(target), "bootstrap": False})
    ts = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    (target / "_archive" / "content").mkdir(parents=True)
    (target / "_archive" / "content" / f"foo-{ts}.md").write_text("# foo\n")
    rel = f"_archive/content/foo-{ts}.md"
    resp = client.post(f"/api/vaults/av3/archive/restore?archive_path={rel}")
    assert resp.status_code == 200, resp.text
    assert (target / "content" / "foo.md").is_file()
