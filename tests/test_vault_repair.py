"""Tests for repairing a vault whose registered path doesn't resolve.

Covers 3 layers of the same fix:
  1. VaultRegistry.update_path — registry-only pointer rewrite, never touches files
  2. `raven vault repair` CLI command
  3. `POST /api/vaults/{name}/repair` API endpoint, plus the friendly 409
     `_vault_or_404` now returns instead of a raw 500 when a vault's path
     is unreachable in the current runtime.
"""
from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from typer.testing import CliRunner
from fastapi.testclient import TestClient

from raven.cli.__main__ import app as cli_app
from raven.api.server import app as api_app
from raven.core.registry import registry, VaultMeta
from raven.core.vault import Vault


runner = CliRunner()


@pytest.fixture
def isolated_env(monkeypatch):
    reg_root = Path(tempfile.mkdtemp(prefix="raven-repair-reg-")).resolve()
    target_root = Path(tempfile.mkdtemp(prefix="raven-repair-target-")).resolve()
    monkeypatch.setenv("WIKI_VAULTS_DIR", str(reg_root))
    yield {"reg_root": reg_root, "target_root": target_root}
    shutil.rmtree(reg_root, ignore_errors=True)
    shutil.rmtree(target_root, ignore_errors=True)


def _register_with_broken_path(name: str, real_path: Path) -> Path:
    """Simulate the historical bug: registry entry points at a path that
    never resolves, while the vault's real files live elsewhere."""
    broken_path = real_path.parent / f"{name}-does-not-exist"
    registry().add(VaultMeta(name=name, path=broken_path))
    return broken_path


# ─── registry.update_path ───────────────────────────────────────────


def test_update_path_rewrites_registry_only(isolated_env):
    real_path = isolated_env["target_root"] / "v1"
    Vault.create("v1", real_path, bootstrap=True)
    broken = _register_with_broken_path("v1", real_path)
    assert registry().get("v1").path == broken

    ok = registry().update_path("v1", real_path)
    assert ok is True
    assert registry().get("v1").path == real_path
    # files untouched
    assert (real_path / "content").is_dir()


def test_update_path_returns_false_for_unknown_vault(isolated_env):
    assert registry().update_path("nope", Path("/tmp")) is False


# ─── CLI: raven vault repair ─────────────────────────────────────────


def test_cli_vault_repair_fixes_broken_path(isolated_env):
    real_path = isolated_env["target_root"] / "v2"
    Vault.create("v2", real_path, bootstrap=True)
    _register_with_broken_path("v2", real_path)

    result = runner.invoke(cli_app, ["vault", "repair", "v2", "--path", str(real_path)])
    assert result.exit_code == 0, result.output
    assert registry().get("v2").path == real_path


def test_cli_vault_repair_rejects_non_vault_dir(isolated_env):
    real_path = isolated_env["target_root"] / "v3"
    Vault.create("v3", real_path, bootstrap=True)
    _register_with_broken_path("v3", real_path)

    not_a_vault = isolated_env["target_root"] / "empty-dir"
    not_a_vault.mkdir()
    result = runner.invoke(cli_app, ["vault", "repair", "v3", "--path", str(not_a_vault)])
    assert result.exit_code != 0
    # registry untouched on rejection
    assert registry().get("v3").path != not_a_vault


# ─── API: repair endpoint + friendly 409 on broken load ─────────────


@pytest.fixture
def client():
    return TestClient(api_app)


def test_api_vault_load_returns_409_not_500_when_unreachable(client, isolated_env):
    real_path = isolated_env["target_root"] / "v4"
    Vault.create("v4", real_path, bootstrap=True)
    _register_with_broken_path("v4", real_path)

    resp = client.get("/api/vaults/v4/pages")
    assert resp.status_code == 409
    assert "repair" in resp.json()["detail"]


def test_api_repair_endpoint_fixes_broken_path(client, isolated_env):
    real_path = isolated_env["target_root"] / "v5"
    Vault.create("v5", real_path, bootstrap=True)
    _register_with_broken_path("v5", real_path)

    resp = client.post(f"/api/vaults/v5/repair", json={"path": str(real_path)})
    assert resp.status_code == 200, resp.text
    assert resp.json()["path"] == str(real_path)

    # vault now loads normally
    resp2 = client.get("/api/vaults/v5/pages")
    assert resp2.status_code == 200


def test_api_repair_endpoint_404_for_unknown_vault(client, isolated_env):
    resp = client.post("/api/vaults/does-not-exist/repair", json={"path": "/tmp"})
    assert resp.status_code == 404


def test_api_repair_endpoint_400_for_non_vault_path(client, isolated_env):
    real_path = isolated_env["target_root"] / "v6"
    Vault.create("v6", real_path, bootstrap=True)
    _register_with_broken_path("v6", real_path)

    not_a_vault = isolated_env["target_root"] / "empty-dir-2"
    not_a_vault.mkdir()
    resp = client.post("/api/vaults/v6/repair", json={"path": str(not_a_vault)})
    assert resp.status_code == 400
