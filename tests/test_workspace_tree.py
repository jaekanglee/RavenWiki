"""tests/test_workspace_tree.py — workspace OS 트리 (read-only) v0.7.61+

테스트 대상:
    - raven.api.workspace_tree.list_workspace_dir
    - raven.api.workspace_tree.read_workspace_file
    - GET /api/vaults/{name}/workspace/tree (FastAPI endpoint)
    - GET /api/vaults/{name}/workspace/file (FastAPI endpoint)

가드 검증:
    - traversal (../, 절대 경로) 거부
    - depth 제한
    - dotfile hidden 토글
    - 워크스페이스 미연동 → 400
    - 부재 경로 → 404
"""
from __future__ import annotations
import json
import shutil
import sys
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from raven.api.server import app as api_app
from raven.api.workspace_tree import (
    list_workspace_dir,
    read_workspace_file,
    MAX_DEPTH,
)
from raven.core.registry import registry
from raven.core.vault import Vault


# ─── fixtures ────────────────────────────────────────────────────────

@pytest.fixture
def workspace_dir():
    """워크스페이스 OS 디렉토리 픽스처.

    구조:
        ws/
          README.md           (4KB 정도)
          src/
            main.py
            raven/
              __init__.py
          .git/                (숨김 디렉토리)
            HEAD
          .venv/               (숨김, 무시되어야 함)
            bin/python
          docs/
            guide.md
    """
    root = Path(tempfile.mkdtemp(prefix="raven-ws-tree-")).resolve()
    (root / "README.md").write_text("# Workspace\n\nhello\n", encoding="utf-8")

    src = root / "src"
    src.mkdir()
    (src / "main.py").write_text("print('hi')\n", encoding="utf-8")
    raven_dir = src / "raven"
    raven_dir.mkdir()
    (raven_dir / "__init__.py").write_text("", encoding="utf-8")

    git_dir = root / ".git"
    git_dir.mkdir()
    (git_dir / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")

    venv = root / ".venv"
    venv.mkdir()
    (venv / "bin").mkdir()
    (venv / "bin" / "python").write_text("#!/usr/bin/env python\n", encoding="utf-8")

    docs = root / "docs"
    docs.mkdir()
    (docs / "guide.md").write_text("# Guide\n\nline1\nline2\n", encoding="utf-8")

    yield root
    shutil.rmtree(root, ignore_errors=True)


@pytest.fixture
def isolated_vault(workspace_dir, monkeypatch):
    """vault 1개 + workspace 연동 픽스처."""
    reg_root = Path(tempfile.mkdtemp(prefix="raven-wstree-reg-")).resolve()
    target_root = Path(tempfile.mkdtemp(prefix="raven-wstree-target-")).resolve()
    monkeypatch.setenv("WIKI_VAULTS_DIR", str(reg_root))

    vault_path = target_root / "v1"
    Vault.create("v1", vault_path, bootstrap=True, workspace_path=str(workspace_dir))

    yield {
        "reg_root": reg_root,
        "target_root": target_root,
        "workspace_root": workspace_dir,
        "vault_name": "v1",
    }
    shutil.rmtree(reg_root, ignore_errors=True)
    shutil.rmtree(target_root, ignore_errors=True)


@pytest.fixture
def client():
    return TestClient(api_app)


# ─── list_workspace_dir (pure) ───────────────────────────────────────

def test_list_root_returns_dirs_first(workspace_dir):
    """루트(숨김 OFF 기본): docs, src 디렉토리 + README.md 파일."""
    result = list_workspace_dir(workspace_root=workspace_dir, relative="")
    names = [n["name"] for n in result["nodes"]]
    # dirs first
    dir_names = [n["name"] for n in result["nodes"] if n["type"] == "dir"]
    file_names = [n["name"] for n in result["nodes"] if n["type"] == "file"]
    assert dir_names == ["docs", "src"]  # alpha, dotfile은 hidden=False에서 제외
    assert file_names == ["README.md"]
    assert result["total"] == 3
    assert result["depth"] == 3


def test_list_root_with_hidden_includes_dotdirs(workspace_dir):
    """hidden=True: .git, .venv 포함."""
    result = list_workspace_dir(workspace_root=workspace_dir, relative="", include_hidden=True)
    dir_names = sorted([n["name"] for n in result["nodes"] if n["type"] == "dir"])
    assert dir_names == [".git", ".venv", "docs", "src"]
    file_names = [n["name"] for n in result["nodes"] if n["type"] == "file"]
    assert "README.md" in file_names


def test_list_hidden_excludes_dotfiles(workspace_dir):
    """hidden=False(기본): .git, .venv 제외."""
    result = list_workspace_dir(workspace_root=workspace_dir, relative="", include_hidden=False)
    names = [n["name"] for n in result["nodes"]]
    assert ".git" not in names
    assert ".venv" not in names
    assert "src" in names
    assert "docs" in names
    assert "README.md" in names


def test_list_hidden_includes_dotfiles(workspace_dir):
    """hidden=True: .git, .venv 포함. is_hidden=True 마킹."""
    result = list_workspace_dir(workspace_root=workspace_dir, relative="", include_hidden=True)
    git = next((n for n in result["nodes"] if n["name"] == ".git"), None)
    assert git is not None
    assert git["is_hidden"] is True
    assert git["type"] == "dir"


def test_list_subdirectory(workspace_dir):
    """relative='src': src/main.py + src/raven."""
    result = list_workspace_dir(workspace_root=workspace_dir, relative="src")
    names = [n["name"] for n in result["nodes"]]
    assert "main.py" in names
    assert "raven" in names
    assert result["path"] == "src"


def test_list_traversal_rejected(workspace_dir):
    """../workspace 외부 → ValueError."""
    with pytest.raises(ValueError, match="escapes workspace root"):
        list_workspace_dir(workspace_root=workspace_dir, relative="../etc")


def test_list_absolute_path_rejected(workspace_dir):
    """절대 경로 → ValueError."""
    with pytest.raises(ValueError, match="escapes workspace root"):
        list_workspace_dir(workspace_root=workspace_dir, relative="/etc/passwd")


def test_list_nonexistent_dir(workspace_dir):
    """없는 디렉토리 → FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        list_workspace_dir(workspace_root=workspace_dir, relative="does/not/exist")


def test_list_file_instead_of_dir(workspace_dir):
    """파일을 path로 → NotADirectoryError."""
    with pytest.raises(NotADirectoryError):
        list_workspace_dir(workspace_root=workspace_dir, relative="README.md")


def test_list_depth_clamped(workspace_dir):
    """depth > MAX_DEPTH → MAX_DEPTH로 clamp. 1 → 1 (루트만, has_children True 자식 안 들어감)."""
    r1 = list_workspace_dir(workspace_root=workspace_dir, relative="", depth=1)
    assert r1["depth"] == 1
    # 모든 dir는 has_children=True (자식 실제 안 들어옴, 표시만)
    for n in r1["nodes"]:
        if n["type"] == "dir":
            assert n["has_children"] is False  # depth=1이면 더 못 들어감


def test_list_has_children_marker(workspace_dir):
    """depth=3 기본에서 src는 has_children=True (자식 main.py/raven 있음)."""
    result = list_workspace_dir(workspace_root=workspace_dir, relative="")
    src = next(n for n in result["nodes"] if n["name"] == "src")
    assert src["has_children"] is True


# ─── read_workspace_file (pure) ─────────────────────────────────────

def test_read_file_text(workspace_dir):
    """README.md 텍스트 읽기."""
    result = read_workspace_file(workspace_root=workspace_dir, relative="README.md")
    assert "Workspace" in result["content"]
    assert result["size"] > 0
    assert result["truncated"] is False


def test_read_file_traversal_rejected(workspace_dir):
    """../ 외부 → ValueError."""
    with pytest.raises(ValueError, match="escapes workspace root"):
        read_workspace_file(workspace_root=workspace_dir, relative="../secret")


def test_read_directory_rejected(workspace_dir):
    """path가 디렉토리 → IsADirectoryError."""
    with pytest.raises(IsADirectoryError):
        read_workspace_file(workspace_root=workspace_dir, relative="src")


def test_read_nonexistent(workspace_dir):
    with pytest.raises(FileNotFoundError):
        read_workspace_file(workspace_root=workspace_dir, relative="nope.txt")


def test_read_truncated_large_file(workspace_dir):
    """max_bytes 작게 → truncated=True."""
    big = workspace_dir / "big.md"
    big.write_text("x" * 10000, encoding="utf-8")
    result = read_workspace_file(workspace_root=workspace_dir, relative="big.md", max_bytes=100)
    assert result["truncated"] is True
    assert "truncated" in result["content"]


# ─── v0.7.61+ 모든 텍스트 파일 미리보기 — binary 감지 ──────────────

def test_read_text_file_is_text(workspace_dir):
    """.txt → is_binary=False, content 보존."""
    txt = workspace_dir / "notes.txt"
    txt.write_text("hello world\n", encoding="utf-8")
    result = read_workspace_file(workspace_root=workspace_dir, relative="notes.txt")
    assert result["is_binary"] is False
    assert "hello world" in result["content"]


def test_read_python_source_is_text(workspace_dir):
    """.py → is_binary=False (소스 코드)."""
    src = workspace_dir / "script.py"
    src.write_text("def f():\n    return 42\n", encoding="utf-8")
    result = read_workspace_file(workspace_root=workspace_dir, relative="script.py")
    assert result["is_binary"] is False
    assert "def f():" in result["content"]


def test_read_json_file_is_text(workspace_dir):
    """.json → is_binary=False."""
    j = workspace_dir / "config.json"
    j.write_text('{"key": "value", "n": 1}\n', encoding="utf-8")
    result = read_workspace_file(workspace_root=workspace_dir, relative="config.json")
    assert result["is_binary"] is False


def test_read_log_file_is_text(workspace_dir):
    """.log → is_binary=False."""
    log = workspace_dir / "app.log"
    log.write_text("INFO: started\nERROR: failed\n", encoding="utf-8")
    result = read_workspace_file(workspace_root=workspace_dir, relative="app.log")
    assert result["is_binary"] is False


def test_read_yaml_is_text(workspace_dir):
    """.yaml → is_binary=False (확장자 무관, 내용 기반)."""
    y = workspace_dir / "config.yaml"
    y.write_text("name: test\nport: 8080\n", encoding="utf-8")
    result = read_workspace_file(workspace_root=workspace_dir, relative="config.yaml")
    assert result["is_binary"] is False


def test_read_binary_png_detected(workspace_dir):
    """PNG 시그니처 (NUL 포함) → is_binary=True."""
    # PNG 시그니처: \x89PNG\r\n\x1a\n + dummy bytes
    png_sig = b"\x89PNG\r\n\x1a\n" + b"\x00\x01\x02\x03" * 100
    img = workspace_dir / "logo.png"
    img.write_bytes(png_sig)
    result = read_workspace_file(workspace_root=workspace_dir, relative="logo.png")
    assert result["is_binary"] is True


def test_read_binary_jpg_detected(workspace_dir):
    """JPG 시그니처 (NUL 다수) → is_binary=True."""
    jpg_sig = b"\xff\xd8\xff\xe0" + b"\x00" * 200 + b"\xff\xd9"
    img = workspace_dir / "photo.jpg"
    img.write_bytes(jpg_sig)
    result = read_workspace_file(workspace_root=workspace_dir, relative="photo.jpg")
    assert result["is_binary"] is True


def test_read_binary_high_nonprintable_detected(workspace_dir):
    """NUL 없지만 printable 비율 낮음 → is_binary=True.

    진짜 binary 패턴: ASCII 영역 (0x00-0x1F) control char + random byte.
    utf-8로 디코드 시 replacement char (U+FFFD) 들어가서 isprintable() False.
    """
    import os
    # 8KB 중 대부분이 low-control + non-ASCII byte
    noise = bytes([(i % 32) for i in range(8192)])  # 0x00-0x1F 반복 (control)
    # control char만 있으면 utf-8 디코드 시 replacement char 됨
    # printable() False (replacement char는 isprintable False)
    f = workspace_dir / "data.bin"
    f.write_bytes(noise)
    result = read_workspace_file(workspace_root=workspace_dir, relative="data.bin")
    assert result["is_binary"] is True, f"expected binary, got text. content[:100]={result['content'][:100]!r}"


def test_read_empty_file_is_text(workspace_dir):
    """빈 파일 → is_binary=False (default)."""
    empty = workspace_dir / "empty.txt"
    empty.write_text("", encoding="utf-8")
    result = read_workspace_file(workspace_root=workspace_dir, relative="empty.txt")
    assert result["is_binary"] is False
    assert result["content"] == ""


# ─── FastAPI endpoints ──────────────────────────────────────────────

def test_endpoint_tree_root(client, isolated_vault):
    """/api/vaults/{name}/workspace/tree — 정상 케이스."""
    resp = client.get(f"/api/vaults/{isolated_vault['vault_name']}/workspace/tree")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["workspace_path"] == str(isolated_vault["workspace_root"])
    assert body["path"] == ""
    names = [n["name"] for n in body["nodes"]]
    assert "src" in names
    assert "README.md" in names
    assert ".git" not in names  # hidden=False 기본


def test_endpoint_tree_hidden_param(client, isolated_vault):
    """?hidden=true로 dotfile 포함."""
    resp = client.get(
        f"/api/vaults/{isolated_vault['vault_name']}/workspace/tree?hidden=true"
    )
    assert resp.status_code == 200
    names = [n["name"] for n in resp.json()["nodes"]]
    assert ".git" in names


def test_endpoint_tree_traversal_rejected(client, isolated_vault):
    """path=../ → 403."""
    resp = client.get(
        f"/api/vaults/{isolated_vault['vault_name']}/workspace/tree",
        params={"path": "../etc"},
    )
    assert resp.status_code == 403
    assert "escapes" in resp.json()["detail"]


def test_endpoint_tree_no_workspace(client, monkeypatch):
    """워크스페이스 미연동 → 400."""
    reg_root = Path(tempfile.mkdtemp(prefix="raven-wstree-nows-")).resolve()
    target_root = Path(tempfile.mkdtemp(prefix="raven-wstree-nows-target-")).resolve()
    monkeypatch.setenv("WIKI_VAULTS_DIR", str(reg_root))
    Vault.create("nows", target_root / "nows", bootstrap=True)

    resp = client.get("/api/vaults/nows/workspace/tree")
    assert resp.status_code == 400
    assert "No workspace" in resp.json()["detail"]

    shutil.rmtree(reg_root, ignore_errors=True)
    shutil.rmtree(target_root, ignore_errors=True)


def test_endpoint_tree_vault_not_found(client):
    """없는 vault → 404."""
    resp = client.get("/api/vaults/does-not-exist/workspace/tree")
    assert resp.status_code == 404


def test_endpoint_tree_workspace_dir_missing(client, isolated_vault, monkeypatch):
    """워크스페이스 디렉토리가 외부에서 사라진 경우 → 404."""
    monkeypatch.setattr(
        "raven.api.server._vault_or_404",
        lambda name: _fake_vault_no_ws_path(name),  # noqa
    ) if False else None  # monkeypatch 안 쓰고 registry 직접 갱신

    # workspace_path를 존재하지 않는 경로로 갱신
    registry().update_workspace_path(
        isolated_vault["vault_name"],
        "/tmp/definitely-does-not-exist-xyz-9876",
    )

    resp = client.get(f"/api/vaults/{isolated_vault['vault_name']}/workspace/tree")
    assert resp.status_code == 404
    assert "does not exist" in resp.json()["detail"]


def _fake_vault_no_ws_path(name):  # pragma: no cover — helper unused
    pass


def test_endpoint_file_read(client, isolated_vault):
    """파일 read — content/size/truncated 응답."""
    resp = client.get(
        f"/api/vaults/{isolated_vault['vault_name']}/workspace/file",
        params={"path": "README.md"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["path"] == "README.md"
    assert "Workspace" in body["content"]
    assert body["truncated"] is False


def test_endpoint_file_traversal(client, isolated_vault):
    """/workspace/file?path=../ → 403."""
    resp = client.get(
        f"/api/vaults/{isolated_vault['vault_name']}/workspace/file",
        params={"path": "../secret"},
    )
    assert resp.status_code == 403


def test_endpoint_file_directory(client, isolated_vault):
    """path가 디렉토리 → 400."""
    resp = client.get(
        f"/api/vaults/{isolated_vault['vault_name']}/workspace/file",
        params={"path": "src"},
    )
    assert resp.status_code == 400


def test_endpoint_file_missing(client, isolated_vault):
    """없는 파일 → 404."""
    resp = client.get(
        f"/api/vaults/{isolated_vault['vault_name']}/workspace/file",
        params={"path": "nope.md"},
    )
    assert resp.status_code == 404