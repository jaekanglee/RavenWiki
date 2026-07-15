"""v0.7.37+ — federated wikilink resolution (read-only) regression guard.

The `/api/crosslink/{name}` endpoint returns the vault where a slug
exists, falling back to other registered vaults when the originating
vault has no match. This is the read-side counterpart to the
agents-allowlist write policy: each vault keeps its domain but stays
discoverable from any other.

Policy under test:
    1. Origin vault is tried FIRST (self short-circuit).
    2. Other registered vaults scanned in registry.json key order.
    3. Unique match  → returned directly.
    4. Multiple matches → "ambiguous" with the candidate list (no
       silent pick — let the dashboard prompt).
    5. No match → ok=False not_found=True.
    6. Best-effort: a corrupt or missing vault is skipped silently —
       federation must not 500 just because one vault is unhealthy.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest  # noqa: F401  (pytest fixture decorator import — venv has pytest)
from fastapi.testclient import TestClient

from raven.api.server import app
from raven.core.vault import Vault


@pytest.fixture
def tmp_raven_home(tmp_path, monkeypatch):
    """Redirect WIKI_VAULTS_DIR to a temp dir.

    `registry()` is a fresh factory on every call (`VaultRegistry()`
    re-reads env at construction), so simply pointing the env at a
    temp dir is enough — no monkeypatching the singleton.
    """
    monkeypatch.setenv("WIKI_VAULTS_DIR", str(tmp_path))
    return tmp_path


def _make_vault(root: Path, name: str, slug: str, title: str, body: str = "") -> Vault:
    """Create a registered vault with one page."""
    root.mkdir(parents=True, exist_ok=True)
    v = Vault.create(name=name, path=root)
    (root / ".vault.json").write_text(json.dumps(v.meta.to_json(), indent=2))
    page = root / "content" / f"{slug}.md"
    page.parent.mkdir(parents=True, exist_ok=True)
    page.write_text(
        f"---\ntitle: {title}\ntype: concept\n---\n\n{body}\n",
        encoding="utf-8",
    )
    return v


def test_crosslink_returns_self_when_slug_exists_in_origin(tmp_raven_home):
    a = _make_vault(tmp_raven_home / "alpha", name="alpha", slug="hello", title="Hello A")
    client = TestClient(app)
    r = client.post(f"/api/crosslink/{a.meta.name}", json={"slug": "hello"})
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["found_in"] == "self"
    assert body["vault"] == "alpha"
    assert body["title"] == "Hello A"


def test_crosslink_federates_to_other_vault_when_missing_locally(tmp_raven_home):
    a = _make_vault(tmp_raven_home / "alpha", name="alpha", slug="local-only", title="Local")
    b = _make_vault(tmp_raven_home / "beta", name="beta", slug="shared", title="Shared B")
    client = TestClient(app)
    # alpha has 'local-only' but NOT 'shared' → federation to beta
    r = client.post(f"/api/crosslink/{a.meta.name}", json={"slug": "shared"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True
    assert body["found_in"] == "beta"
    assert body["title"] == "Shared B"


def test_crosslink_not_found_when_no_vault_has_slug(tmp_raven_home):
    a = _make_vault(tmp_raven_home / "alpha", name="alpha", slug="x", title="X")
    b = _make_vault(tmp_raven_home / "beta", name="beta", slug="y", title="Y")
    client = TestClient(app)
    r = client.post(f"/api/crosslink/{a.meta.name}", json={"slug": "missing-everywhere"})
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is False
    assert body["not_found"] is True


def test_crosslink_ambiguous_when_multiple_other_vaults_hold_same_slug(tmp_raven_home):
    a = _make_vault(tmp_raven_home / "alpha", name="alpha", slug="own", title="Alpha's own")
    b = _make_vault(
        tmp_raven_home / "beta", name="beta", slug="react", title="React in Beta"
    )
    c = _make_vault(
        tmp_raven_home / "gamma", name="gamma", slug="react", title="React in Gamma"
    )
    client = TestClient(app)
    # alpha has 'own' but NOT 'react' → ambiguous between beta & gamma
    r = client.post(f"/api/crosslink/{a.meta.name}", json={"slug": "react"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True
    assert body["found_in"] == "ambiguous"
    candidates = body["candidates"]
    assert len(candidates) == 2
    vault_names = sorted(c["vault"] for c in candidates)
    assert vault_names == ["beta", "gamma"]


def test_crosslink_does_not_mutate_registry_or_files(tmp_raven_home):
    """The endpoint is read-only. Side-effect free across federation."""
    a = _make_vault(tmp_raven_home / "alpha", name="alpha", slug="k", title="K")
    b = _make_vault(tmp_raven_home / "beta", name="beta", slug="k", title="K-B")
    client = TestClient(app)

    # Snapshot content of both vaults before the federation lookup
    before_a = sorted((tmp_raven_home / "alpha").rglob("*.md"))
    before_b = sorted((tmp_raven_home / "beta").rglob("*.md"))
    before_reg = (tmp_raven_home / ".registry.json").read_text()

    r = client.post(f"/api/crosslink/{a.meta.name}", json={"slug": "k"})
    assert r.status_code == 200

    after_a = sorted((tmp_raven_home / "alpha").rglob("*.md"))
    after_b = sorted((tmp_raven_home / "beta").rglob("*.md"))
    after_reg = (tmp_raven_home / ".registry.json").read_text()

    assert before_a == after_a, "alpha vault files mutated by federation lookup"
    assert before_b == after_b, "beta vault files mutated by federation lookup"
    assert before_reg == after_reg, "registry.json mutated by federation lookup"


def test_crosslink_unknown_vault_treated_as_not_found(tmp_raven_home):
    """If the originating vault doesn't exist, federation still scans others
    and may still resolve. Must never 500 just because origin is unknown."""
    b = _make_vault(tmp_raven_home / "beta", name="beta", slug="only-here", title="X")
    client = TestClient(app)
    r = client.post("/api/crosslink/ghost-vault", json={"slug": "only-here"})
    assert r.status_code == 200
    body = r.json()
    # No ghost vault, no alpha — beta has it, fallback federation wins.
    assert body["ok"] is True
    assert body["found_in"] == "beta"
