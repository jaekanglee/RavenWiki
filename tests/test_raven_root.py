"""tests/test_raven_root.py — v0.6.3+ Raven root convention.

These tests pin the v0.6.3 decision:
  - All Raven vaults live under `~/Raven/<name>/` by default
  - `WIKI_VAULTS_DIR` env var still overrides (legacy / multi-host)
  - The path is auto-determined from the vault name (user only types
    `name`; the wizard renders the resolved path as a read-only preview)
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from raven.core.registry import REGISTRY_PATH, VAULTS_ROOT, registry
from raven.core.vault import Vault


# ────────────────────────── fixtures ───────────────────────────────


@pytest.fixture
def isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect HOME to a temp dir, clear WIKI_VAULTS_DIR."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("WIKI_VAULTS_DIR", raising=False)
    return tmp_path


# ────────────────────────── tests ───────────────────────────────────


def test_vaults_root_default_is_ralph_home_raven(
    isolated_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """v0.6.3+: default VAULTS_ROOT = ~/Raven (not ~/vaults)."""
    monkeypatch.delenv("WIKI_VAULTS_DIR", raising=False)
    # Force a fresh resolution (registry caches per-process)
    expected = (Path(str(isolated_home)) / "Raven").resolve()
    assert VAULTS_ROOT() == expected


def test_vaults_root_env_override_still_works(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """WIKI_VAULTS_DIR=~/X still overrides the default (legacy support)."""
    override = tmp_path / "custom-vaults"
    monkeypatch.setenv("WIKI_VAULTS_DIR", str(override))
    assert VAULTS_ROOT() == override.resolve()


def test_create_vault_auto_creates_directory(
    isolated_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`Vault.create()` with a non-existent path → mkdir(parents=True).

    This is the wizard's "path will be created" guarantee.
    """
    monkeypatch.delenv("WIKI_VAULTS_DIR", raising=False)
    target = Path(str(isolated_home)) / "Raven" / "my-new-vault"
    assert not target.exists()

    v = Vault.create(name="my-new-vault", path=target, mode="personal", owner="user")

    assert target.is_dir()
    assert v.root == target.resolve()
    # Lite bootstrap files
    assert (target / "_meta" / "system" / "SCHEMA.md").is_file()
    assert (target / "_meta" / "system" / "RULES.md").is_file()
    assert (target / "_meta" / "system" / "AGENTS.md").is_file()
    assert (target / "log.md").is_file()
    # Registered
    reg = registry()
    assert reg.get("my-new-vault") is not None


def test_list_vaults_response_includes_vaults_root(
    isolated_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """v0.6.3+: GET /api/vaults returns `vaults_root` for the dashboard."""
    from fastapi.testclient import TestClient
    from raven.api.server import app

    monkeypatch.delenv("WIKI_VAULTS_DIR", raising=False)
    target = Path(str(isolated_home)) / "Raven" / "alpha"
    Vault.create(name="alpha", path=target, mode="personal", owner="user")

    client = TestClient(app)
    resp = client.get("/api/vaults")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert "vaults_root" in data
    assert data["vaults_root"].endswith("/Raven")
    assert any(v["name"] == "alpha" for v in data["vaults"])


def test_create_vault_under_raven_root_default(
    isolated_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """End-to-end: empty registry + WIKI_VAULTS_DIR unset → vault under ~/Raven."""
    from raven.core.vault import Vault as _Vault

    monkeypatch.delenv("WIKI_VAULTS_DIR", raising=False)
    # Sanity: registry empty
    assert list(registry().list()) == []

    v = _Vault.create(
        name="alpha",
        path=Path(str(isolated_home)) / "Raven" / "alpha",
        mode="personal",
        owner="user",
    )
    expected = (Path(str(isolated_home)) / "Raven" / "alpha").resolve()
    assert v.root == expected
    assert expected.is_dir()
    # Auto-registered
    assert registry().get("alpha") is not None


def test_registry_path_fallback_for_docker(
    isolated_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """v0.7.23+: registry fallback resolves paths relative to VAULTS_ROOT if data['path'] doesn't exist."""
    from raven.core.registry import VaultRegistry, VaultMeta
    import json

    # 1. Setup isolated WIKI_VAULTS_DIR
    vaults_root = isolated_home / "Raven"
    vaults_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("WIKI_VAULTS_DIR", str(vaults_root))

    # 2. Write a registry file with an invalid/non-existent host path
    reg_file = vaults_root / ".registry.json"
    reg_data = {
        "version": 1,
        "default": "dummy",
        "vaults": {
            "dummy": {
                "path": "/some/nonexistent/host/path/Raven/dummy",
                "mode": "personal",
                "owner": "user"
            }
        }
    }
    reg_file.write_text(json.dumps(reg_data))

    # 3. Create the dummy directory under WIKI_VAULTS_DIR (to simulate container mount)
    dummy_vault_dir = vaults_root / "dummy"
    dummy_vault_dir.mkdir(parents=True, exist_ok=True)

    # 4. Load registry
    reg = VaultRegistry()
    meta = reg.get("dummy")
    assert meta is not None

    # 5. Check if it fell back to the correct path under WIKI_VAULTS_DIR
    assert meta.path == dummy_vault_dir.resolve()
