from __future__ import annotations

import shutil
import sys
import tempfile
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from raven.cli.__main__ import app as cli_app
from raven.api.server import app as api_app
from raven.core.registry import registry, VaultMeta
from raven.core.vault import Vault

runner = CliRunner()


@pytest.fixture
def isolated_env(monkeypatch):
    reg_root = Path(tempfile.mkdtemp(prefix="raven-workspace-reg-")).resolve()
    target_root = Path(tempfile.mkdtemp(prefix="raven-workspace-target-")).resolve()
    workspace_root = Path(tempfile.mkdtemp(prefix="raven-workspace-ws-")).resolve()
    
    monkeypatch.setenv("WIKI_VAULTS_DIR", str(reg_root))
    
    yield {
        "reg_root": reg_root, 
        "target_root": target_root,
        "workspace_root": workspace_root
    }
    
    shutil.rmtree(reg_root, ignore_errors=True)
    shutil.rmtree(target_root, ignore_errors=True)
    shutil.rmtree(workspace_root, ignore_errors=True)


@pytest.fixture
def client():
    return TestClient(api_app)


# ─── registry / vault creation test ───────────────────────────────────

def test_vault_create_saves_workspace_path(isolated_env):
    path = isolated_env["target_root"] / "v1"
    ws = isolated_env["workspace_root"]
    
    v = Vault.create("v1", path, bootstrap=True, workspace_path=str(ws))
    assert v.meta.workspace_path == str(ws)
    
    # Read back from registry
    meta = registry().get("v1")
    assert meta.workspace_path == str(ws)
    
    # Read back from .vault.json
    import json
    vjson = path / ".vault.json"
    assert vjson.exists()
    vjson_data = json.loads(vjson.read_text(encoding="utf-8"))
    assert vjson_data.get("workspace_path") == str(ws)


def test_registry_update_workspace_path(isolated_env):
    path = isolated_env["target_root"] / "v2"
    ws = isolated_env["workspace_root"]
    
    v = Vault.create("v2", path, bootstrap=True)
    assert not v.meta.workspace_path
    
    # Associate
    ok = registry().update_workspace_path("v2", str(ws))
    assert ok is True
    assert registry().get("v2").workspace_path == str(ws)
    
    # Unlink
    ok = registry().update_workspace_path("v2", "")
    assert ok is True
    assert not registry().get("v2").workspace_path


# ─── CLI tests ────────────────────────────────────────────────────────

def test_cli_vault_workspace_associate_and_unlink(isolated_env):
    path = isolated_env["target_root"] / "v3"
    ws = isolated_env["workspace_root"]
    
    Vault.create("v3", path, bootstrap=True)
    
    # 1. Show empty
    result = runner.invoke(cli_app, ["vault", "workspace", "v3"])
    assert result.exit_code == 0
    assert "no workspace associated" in result.output
    
    # 2. Associate
    result = runner.invoke(cli_app, ["vault", "workspace", "v3", str(ws)])
    assert result.exit_code == 0
    assert "workspace associated" in result.output
    assert registry().get("v3").workspace_path == str(ws)
    
    # 3. Show associated
    result = runner.invoke(cli_app, ["vault", "workspace", "v3"])
    assert result.exit_code == 0
    assert str(ws) in result.output
    
    # 4. Unlink
    result = runner.invoke(cli_app, ["vault", "workspace", "v3", "--unlink"])
    assert result.exit_code == 0
    assert "unlinked workspace" in result.output
    assert not registry().get("v3").workspace_path


# ─── API tests ────────────────────────────────────────────────────────

def test_api_workspace_associate_and_git_endpoints(client, isolated_env):
    path = isolated_env["target_root"] / "v4"
    ws = isolated_env["workspace_root"]
    
    Vault.create("v4", path, bootstrap=True)
    
    # 1. Associate workspace via API
    resp = client.post("/api/vaults/v4/workspace", json={"workspace_path": str(ws)})
    assert resp.status_code == 200
    assert resp.json()["workspace_path"] == str(ws)
    assert registry().get("v4").workspace_path == str(ws)
    
    # 2. Verify git status endpoint - not a git repository yet
    resp = client.get("/api/vaults/v4/git/status")
    assert resp.status_code == 200
    assert resp.json()["has_workspace"] is True
    assert resp.json()["is_git"] is False
    
    # 3. Initialize Git in the workspace directory
    subprocess.run(["git", "init"], cwd=str(ws), check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=str(ws), check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=str(ws), check=True)
    
    # Create an initial commit
    dummy_file = ws / "readme.txt"
    dummy_file.write_text("hello", encoding="utf-8")
    subprocess.run(["git", "add", "readme.txt"], cwd=str(ws), check=True)
    subprocess.run(["git", "commit", "-m", "initial commit"], cwd=str(ws), check=True)
    
    # Modify a file and create an untracked file
    dummy_file.write_text("hello world", encoding="utf-8")
    untracked_file = ws / "untracked.txt"
    untracked_file.write_text("new file", encoding="utf-8")
    
    # 4. Verify git status endpoint - now it is a git repository with changes
    resp = client.get("/api/vaults/v4/git/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_git"] is True
    assert "branch" in data
    assert "commit" in data
    
    changes = data["changes"]
    files = {c["file"]: c["status"] for c in changes}
    assert "readme.txt" in files
    assert "untracked.txt" in files
    
    # 5. Verify git diff endpoint
    # Diff for modified file
    resp = client.get("/api/vaults/v4/git/diff?file=readme.txt")
    assert resp.status_code == 200
    assert "hello" in resp.json()["diff"]
    assert "world" in resp.json()["diff"]
    
    # Diff for untracked file
    resp = client.get("/api/vaults/v4/git/diff?file=untracked.txt")
    assert resp.status_code == 200
    assert "new file" in resp.json()["diff"]
