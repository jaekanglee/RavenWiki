"""tests/test_index_json.py — v0.6.5+ GET /api/index.json regression guards.

Why this test exists
--------------------
Before v0.6.5, the dev API server (`python -m raven.api`) returned 404 for
`/api/index.json`. The Dashboard HomePage's `fetch("/api/index.json")` then
silently fell back to an empty list — meaning the HomePage always showed
"no pages" in `make dev` until the user ran `raven export` first to build
the static `dashboard/public/api/index.json`.

This test pins the dev API behavior so the bug can't return.

v0.6.5+ also makes the dev API shape **match** the static export shape
exactly, so the dashboard is identical in both modes.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from raven.api.server import app
from raven.core.vault import Vault
from raven.core.registry import VaultMeta, registry


# ────────────────────────── fixtures ───────────────────────────────


@pytest.fixture
def vault_with_pages(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Vault:
    """Vault with 3 markdown pages, registered as default."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("WIKI_VAULTS_DIR", raising=False)
    (tmp_path / "Raven" / "alpha" / "content").mkdir(parents=True)
    (tmp_path / "Raven" / "alpha" / "_meta" / "system").mkdir(parents=True)

    # 3 pages with varying metadata
    (tmp_path / "Raven" / "alpha" / "content" / "hello.md").write_text(
        "---\ntitle: Hello\ntype: concept\ncreated: 2026-06-01\nupdated: 2026-06-27\n---\nbody\n",
        encoding="utf-8",
    )
    (tmp_path / "Raven" / "alpha" / "content" / "world.md").write_text(
        "---\ntitle: World\ntype: project\ncreated: 2026-06-02\nupdated: 2026-06-26\ntags: [demo, alpha]\n---\nbody\n",
        encoding="utf-8",
    )
    (tmp_path / "Raven" / "alpha" / "content" / "sub").mkdir(exist_ok=True)
    (tmp_path / "Raven" / "alpha" / "content" / "sub" / "page.md").write_text(
        "---\ntitle: Sub Page\ntype: query\nupdated: 2026-06-25\n---\nbody\n",
        encoding="utf-8",
    )

    v = Vault.create(
        name="alpha",
        path=tmp_path / "Raven" / "alpha",
        mode="personal",
        owner="user",
    )
    registry().set_default("alpha")
    return v


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


# ────────────────────────── tests ───────────────────────────────────


def test_index_json_returns_pages(
    vault_with_pages: Vault, client: TestClient
) -> None:
    """v0.6.5+: dev API serves /api/index.json with the same shape as the
    static `dashboard/public/api/index.json` produced by `raven export`.
    """
    resp = client.get("/api/index.json")
    assert resp.status_code == 200
    pages = resp.json()
    assert isinstance(pages, list)
    assert len(pages) == 3  # hello, world, sub/page

    # Sort: (type, slug) ascending → concept, project, query
    assert [p["type"] for p in pages] == ["concept", "project", "query"]
    # Slug drop '.md' is the export_static contract.
    assert pages[0]["slug"] == "content/hello"
    # Path uses '/' separator
    assert pages[0]["path"] == "content/hello.md"
    assert pages[1]["path"] == "content/world.md"
    assert pages[2]["path"] == "content/sub/page.md"


def test_index_json_page_shape_matches_export(
    vault_with_pages: Vault, client: TestClient
) -> None:
    """Each page dict has the same keys as export_static.py produces."""
    resp = client.get("/api/index.json")
    assert resp.status_code == 200
    page = resp.json()[0]
    expected_keys = {"slug", "title", "type", "path", "created", "updated", "tags"}
    assert set(page.keys()) == expected_keys, (
        f"page keys drifted from export_static shape: "
        f"got {set(page.keys())}, expected {expected_keys}"
    )


def test_index_json_filters_hidden_and_node_modules(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, client: TestClient
) -> None:
    """Files under .git / node_modules / dashboard must be excluded."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("WIKI_VAULTS_DIR", raising=False)
    (tmp_path / "Raven" / "beta" / "content").mkdir(parents=True)
    (tmp_path / "Raven" / "beta" / "content" / "real.md").write_text(
        "---\ntitle: Real\ntype: concept\n---\nbody\n",
        encoding="utf-8",
    )
    # These should NOT show up
    (tmp_path / "Raven" / "beta" / "content" / "node_modules").mkdir()
    (tmp_path / "Raven" / "beta" / "content" / "node_modules" / "hidden.md").write_text("x")
    (tmp_path / "Raven" / "beta" / "content" / "dashboard").mkdir()
    (tmp_path / "Raven" / "beta" / "content" / "dashboard" / "x.md").write_text("x")
    (tmp_path / "Raven" / "beta" / "content" / ".hidden.md").write_text("x")

    Vault.create(name="beta", path=tmp_path / "Raven" / "beta", mode="personal", owner="user")
    registry().set_default("beta")

    resp = client.get("/api/index.json")
    assert resp.status_code == 200
    pages = resp.json()
    slugs = [p["slug"] for p in pages]
    assert slugs == ["content/real"]


def test_index_json_404_when_no_vaults(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, client: TestClient
) -> None:
    """No vaults registered → 404 with a clear message."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("WIKI_VAULTS_DIR", raising=False)
    # Don't create any vault. The default fixture left the registry with
    # one vault though, so re-init the registry explicitly.
    reg = registry()
    reg._data = {"version": 1, "default": None, "vaults": {}}
    reg._save()

    resp = client.get("/api/index.json")
    assert resp.status_code == 404
    assert "no vaults" in resp.json()["detail"]


def test_index_json_uses_default_vault(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, client: TestClient
) -> None:
    """When multiple vaults are registered, GET /api/index.json uses the
    one marked as default — not the first registered one.
    """
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("WIKI_VAULTS_DIR", raising=False)
    # Two vaults: alpha (first), beta (default)
    (tmp_path / "Raven" / "alpha" / "content").mkdir(parents=True)
    (tmp_path / "Raven" / "alpha" / "content" / "from-alpha.md").write_text(
        "---\ntitle: From Alpha\ntype: concept\n---\nbody\n", encoding="utf-8"
    )
    (tmp_path / "Raven" / "beta" / "content").mkdir(parents=True)
    (tmp_path / "Raven" / "beta" / "content" / "from-beta.md").write_text(
        "---\ntitle: From Beta\ntype: concept\n---\nbody\n", encoding="utf-8"
    )
    Vault.create(name="alpha", path=tmp_path / "Raven" / "alpha", mode="personal", owner="user")
    Vault.create(name="beta", path=tmp_path / "Raven" / "beta", mode="personal", owner="user")
    registry().set_default("beta")

    resp = client.get("/api/index.json")
    assert resp.status_code == 200
    pages = resp.json()
    slugs = [p["slug"] for p in pages]
    assert slugs == ["content/from-beta"]
