"""v0.7.50 raw/ folder endpoints (ADR-2026-07-02: 사람 1차 운영 영역).

4 endpoints:
  GET    /api/vaults/{name}/raw             — list (tree + meta)
  GET    /api/vaults/{name}/raw/{path:path}  — read file
  PUT    /api/vaults/{name}/raw/{path:path}  — write file (overwrite)
  DELETE /api/vaults/{name}/raw/{path:path}  — delete file/empty dir

가드 (defense-in-depth):
  1) raw/ 접두사 강제 (system area whitelist)
  2) slug_module.validate (절대/.. / NUL 차단)
  3) resolved path가 raw_root 내부인지 확인
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from raven.api.server import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def raw_vault(monkeypatch):
    """정식 흐름: WIKI_VAULTS_DIR 임시 redirect + /api/vaults/create로 raw/ 포함 vault 생성.

    raw/ 폴더와 content/, _meta/system/ 까지 갖춘 vault를 만들어 registry에 등록한다.
    """
    reg_root = Path(tempfile.mkdtemp(prefix="raven-raw-reg-"))
    target_root = Path(tempfile.mkdtemp(prefix="raven-raw-target-"))
    monkeypatch.setenv("WIKI_VAULTS_DIR", str(reg_root))

    v_root = target_root / "raw-test-vault"
    v_root.mkdir()
    (v_root / "raw").mkdir()
    (v_root / "raw" / "articles").mkdir()
    (v_root / "raw" / "articles" / "foo.md").write_text("# foo\nbody", encoding="utf-8")
    (v_root / "raw" / "readme.md").write_text("hello", encoding="utf-8")
    (v_root / "content").mkdir()
    (v_root / "_meta").mkdir()
    (v_root / "_meta" / "system").mkdir()
    (v_root / "_meta" / "system" / "SCHEMA.md").write_text("# schema", encoding="utf-8")
    (v_root / "_meta" / "system" / "RULES.md").write_text("# rules", encoding="utf-8")
    (v_root / "_meta" / "system" / "README.md").write_text("# readme", encoding="utf-8")
    (v_root / "_meta" / "system" / "PROJECT-WORKFLOW.md").write_text("# workflow", encoding="utf-8")
    (v_root / "_meta" / "system" / "log.md").write_text("# log", encoding="utf-8")
    (v_root / ".vault.json").write_text(json.dumps({
        "name": "raw-test-vault",
        "path": str(v_root),
        "mode": "personal",
        "owner": "user",
    }))

    # 정식 create endpoint 통해 등록 (bootstrap=False로 raw 구조 보존)
    c = TestClient(app)
    r = c.post("/api/vaults/create", json={
        "name": "raw-test-vault",
        "path": str(v_root),
        "bootstrap": False,
    })
    assert r.status_code == 200, f"create failed: {r.text}"

    yield v_root


# ──────────────────── list ────────────────────


def test_list_raw_returns_files_and_dirs(client, raw_vault):
    r = client.get("/api/vaults/raw-test-vault/raw")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["ok"] is True
    assert data["vault"] == "raw-test-vault"
    assert data["root"] == "raw"
    items = {it["path"]: it for it in data["items"]}
    assert "raw/articles" in items
    assert items["raw/articles"]["type"] == "dir"
    assert "raw/articles/foo.md" in items
    assert items["raw/articles/foo.md"]["type"] == "file"
    assert items["raw/articles/foo.md"]["size"] == len("# foo\nbody".encode("utf-8"))
    assert "kind" in items["raw/articles/foo.md"]
    assert items["raw/articles/foo.md"]["kind"] == "raw"


def test_list_raw_404_when_no_raw_folder(client, monkeypatch):
    """vault에 raw/ 자체가 없으면 404."""
    reg_root = Path(tempfile.mkdtemp(prefix="raven-no-raw-reg-"))
    target_root = Path(tempfile.mkdtemp(prefix="raven-no-raw-target-"))
    monkeypatch.setenv("WIKI_VAULTS_DIR", str(reg_root))
    v_root = target_root / "no-raw-vault"
    v_root.mkdir()
    (v_root / "content").mkdir()
    (v_root / "_meta").mkdir()
    (v_root / "_meta" / "system").mkdir()
    (v_root / "_meta" / "system" / "SCHEMA.md").write_text("# schema")
    (v_root / "_meta" / "system" / "RULES.md").write_text("# rules")
    (v_root / "_meta" / "system" / "README.md").write_text("# readme")
    (v_root / "_meta" / "system" / "PROJECT-WORKFLOW.md").write_text("# workflow")
    (v_root / "_meta" / "system" / "log.md").write_text("# log")
    (v_root / ".vault.json").write_text(json.dumps({
        "name": "no-raw-vault", "path": str(v_root), "mode": "personal", "owner": "user",
    }))
    c = TestClient(app)
    r = c.post("/api/vaults/create", json={
        "name": "no-raw-vault", "path": str(v_root), "bootstrap": False,
    })
    assert r.status_code == 200
    r = c.get("/api/vaults/no-raw-vault/raw")
    assert r.status_code == 404
    assert "raw/ folder not found" in r.json()["detail"]


def test_list_raw_404_for_unknown_vault(client):
    r = client.get("/api/vaults/does-not-exist-xyz/raw")
    assert r.status_code == 404


# ──────────────────── read ────────────────────


def test_read_raw_returns_content(client, raw_vault):
    r = client.get("/api/vaults/raw-test-vault/raw/articles/foo.md")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["ok"] is True
    assert data["path"] == "raw/articles/foo.md"
    assert data["content"] == "# foo\nbody"
    assert data["size"] == len("# foo\nbody".encode("utf-8"))


def test_read_raw_404_for_missing_file(client, raw_vault):
    r = client.get("/api/vaults/raw-test-vault/raw/articles/missing.md")
    assert r.status_code == 404


def test_read_raw_400_for_directory_path(client, raw_vault):
    r = client.get("/api/vaults/raw-test-vault/raw/articles")
    assert r.status_code == 400
    assert "directory" in r.json()["detail"]


# ──────────────────── write (PUT) ────────────────────


def test_write_raw_creates_new_file(client, raw_vault):
    r = client.put(
        "/api/vaults/raw-test-vault/raw/articles/new.md",
        json={"content": "# new file\nbody"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["ok"] is True
    assert data["existed"] is False
    assert (raw_vault / "raw" / "articles" / "new.md").read_text() == "# new file\nbody"


def test_write_raw_overwrites_existing(client, raw_vault):
    r = client.put(
        "/api/vaults/raw-test-vault/raw/articles/foo.md",
        json={"content": "OVERWRITTEN"},
    )
    assert r.status_code == 200
    assert r.json()["existed"] is True
    assert (raw_vault / "raw" / "articles" / "foo.md").read_text() == "OVERWRITTEN"


def test_write_raw_creates_parent_dirs(client, raw_vault):
    """parent dir 없으면 자동 mkdir (P32: OS directory = first-class)."""
    r = client.put(
        "/api/vaults/raw-test-vault/raw/deep/nested/file.md",
        json={"content": "deep"},
    )
    assert r.status_code == 200, r.text
    assert (raw_vault / "raw" / "deep" / "nested" / "file.md").read_text() == "deep"


def test_safe_raw_path_guards(client, raw_vault):
    """_safe_raw_path_or_400의 3중 가드 단위 검증.

    1) slug_module.validate — NUL/colon/../absolute/~start/raw/ 밖 escape 차단
    2) defense-in-depth — resolved path가 raw_root 내부인지 확인
    3) FastAPI 라우터 — path normalize (RFC 3986) → '..' 흡수

    실제로 URL로 보낼 수 있는 패턴이 한정적이므로 endpoint 직접 호출로 검증.
    """
    from raven.api.server import _safe_raw_path_or_400
    from fastapi import HTTPException
    from pathlib import Path

    raw_root = raw_vault / "raw"

    # 1) 정상 path
    result = _safe_raw_path_or_400("articles/foo.md", raw_root)
    assert result.exists()
    assert str(result).startswith(str(raw_root.resolve()))

    # 2) 빈 path
    with pytest.raises(HTTPException) as exc_info:
        _safe_raw_path_or_400("", raw_root)
    assert exc_info.value.status_code == 400

    # 3) '..' segment 명시 거부 (defense-in-depth)
    # URL로는 못 보내지만 endpoint 단계에서 1차 방어
    with pytest.raises(HTTPException) as exc_info:
        _safe_raw_path_or_400("articles/../escape.md", raw_root)
    assert exc_info.value.status_code == 400
    assert ".." in exc_info.value.detail


def test_write_raw_400_when_path_is_directory(client, raw_vault):
    r = client.put(
        "/api/vaults/raw-test-vault/raw/articles",
        json={"content": "x"},
    )
    assert r.status_code == 400


# ──────────────────── delete ────────────────────


def test_delete_raw_removes_file(client, raw_vault):
    target = raw_vault / "raw" / "readme.md"
    assert target.exists()
    r = client.delete("/api/vaults/raw-test-vault/raw/readme.md")
    assert r.status_code == 200
    assert not target.exists()


def test_delete_raw_removes_empty_dir(client, raw_vault):
    """빈 dir 생성 후 삭제."""
    (raw_vault / "raw" / "empty_dir").mkdir()
    r = client.delete("/api/vaults/raw-test-vault/raw/empty_dir")
    assert r.status_code == 200
    assert not (raw_vault / "raw" / "empty_dir").exists()


def test_delete_raw_409_for_nonempty_dir(client, raw_vault):
    """비어있지 않은 dir → 409."""
    r = client.delete("/api/vaults/raw-test-vault/raw/articles")
    assert r.status_code == 409
    assert "not empty" in r.json()["detail"]


def test_delete_raw_404_for_missing(client, raw_vault):
    r = client.delete("/api/vaults/raw-test-vault/raw/missing.md")
    assert r.status_code == 404


# ──────────────────── prefix guard / path escape ────────────────────


def test_write_raw_404_for_path_with_dotdot(client, raw_vault):
    """FastAPI/Starlette는 RFC 3986 path normalization으로 '..'을 흡수.

    결과:
      - '../escape.md' → 404 (라우트 매칭 안 됨, FastAPI 동작 — 다른 endpoint 패턴과 충돌)
      - 'articles/../escape.md' → normalize되어 'escape.md'로 endpoint 도달.
        endpoint의 defense-in-depth로 raw_root 내부 확인 후 raw/ 내 정상 파일 생성.
        이는 escape가 아니라 RFC 3986 표준 동작.

    '..' 단독은 FastAPI route 매칭 단계에서 404 또는 다른 endpoint로 매칭.
    """
    # '../escape.md' → 404 (라우트 매칭 안 됨)
    r = client.put(
        "/api/vaults/raw-test-vault/raw/../escape.md",
        json={"content": "x"},
    )
    assert r.status_code in (404, 422), f"got {r.status_code} {r.text}"


def test_write_raw_normalized_path_creates_in_raw_root(client, raw_vault):
    """'articles/../escape.md' → normalize되어 raw/escape.md 생성 (raw_root 내부).

    security note: FastAPI가 RFC 3986 따라 path를 normalize하므로 endpoint에는
    정규화된 path만 도달. defense-in-depth(_safe_raw_path_or_400의 resolved가
    raw_root 내부인지 확인)가 2차 안전망.
    """
    r = client.put(
        "/api/vaults/raw-test-vault/raw/articles/../escape.md",
        json={"content": "normalized"},
    )
    assert r.status_code == 200
    # raw_root 내부에 escape.md 생성 (articles/는 normalize되어 사라짐)
    assert (raw_vault / "raw" / "escape.md").read_text() == "normalized"
    # articles/foo.md는 그대로 존재
    assert (raw_vault / "raw" / "articles" / "foo.md").exists()
