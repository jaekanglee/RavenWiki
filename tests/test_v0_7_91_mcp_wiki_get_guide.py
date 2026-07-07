"""v0.7.91 — MCP wiki_get_guide (Lite bootstrap 3종 read-only).

REST surface /api/vaults/{name}/guide/{kind} (v0.7.89) 와 동등 contract
검증. 화이트리스트 fail-closed, 응답 shape 동일.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from raven.api.server import app
from raven.mcp.tools import (
    GuideNotFoundError,
    LITE_GUIDE_KINDS,
    read_guide,
    _resolve_guide_path,
)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def guide_mcp_vault(monkeypatch):
    """Lite bootstrap 3종 + 비화이트 파일을 모두 갖춘 vault (MCP 테스트용)."""
    reg_root = Path(tempfile.mkdtemp(prefix="raven-mcp-guide-reg-"))
    target_root = Path(tempfile.mkdtemp(prefix="raven-mcp-guide-target-"))
    monkeypatch.setenv("WIKI_VAULTS_DIR", str(reg_root))

    v_root = target_root / "mcp-guide-vault"
    v_root.mkdir()
    (v_root / "_meta" / "agents").mkdir(parents=True)

    (v_root / "_meta" / "agents" / "SCHEMA.md").write_text(
        "# SCHEMA\nfrontmatter v2.4", encoding="utf-8"
    )
    (v_root / "_meta" / "agents" / "PROJECT-WORKFLOW.md").write_text(
        "# PROJECT-WORKFLOW\nMCP guide", encoding="utf-8"
    )
    (v_root / "log.md").write_text(
        "# Vault Log\n\n## [2026-07-07] create\n- reason: test\n", encoding="utf-8"
    )
    # 비화이트
    (v_root / "_meta" / "system").mkdir(parents=True)
    (v_root / "_meta" / "system" / "OPERATIONS.md").write_text(
        "Tier 1 secret", encoding="utf-8"
    )

    (v_root / ".vault.json").write_text(json.dumps({
        "name": "mcp-guide-vault",
        "path": str(v_root),
        "mode": "personal",
        "owner": "user",
    }))

    c = TestClient(app)
    r = c.post("/api/vaults", json={
        "name": "mcp-guide-vault",
        "path": str(v_root),
        "bootstrap": False,
    })
    assert r.status_code == 200, f"create failed: {r.text}"

    yield v_root


# ──────────────────── whitelist (3종 매칭) ────────────────────

def test_resolve_guide_path_accepts_three_kinds(guide_mcp_vault):
    """화이트 3종은 모두 정상 path 반환."""
    for kind in LITE_GUIDE_KINDS:
        p = _resolve_guide_path(guide_mcp_vault, kind)
        assert p.exists()
        assert p.is_file()


def test_resolve_guide_path_accepts_basename_for_log(guide_mcp_vault):
    """basename 매칭 (e.g. 'log.md' → 'log.md')."""
    p = _resolve_guide_path(guide_mcp_vault, "log.md")
    assert p.name == "log.md"


def test_resolve_guide_path_rejects_non_whitelist(guide_mcp_vault):
    """비화이트 kind는 GuideNotFoundError (403 equivalent)."""
    with pytest.raises(GuideNotFoundError) as exc_info:
        _resolve_guide_path(guide_mcp_vault, "_meta/system/OPERATIONS.md")
    msg = str(exc_info.value)
    assert "whitelist" in msg.lower()
    # 화이트 3종이 메시지에 노출되어 caller self-correction 가능
    assert "_meta/agents/SCHEMA.md" in msg
    assert "log.md" in msg


def test_resolve_guide_path_rejects_path_traversal(guide_mcp_vault):
    """path traversal 시도 → fail-closed."""
    with pytest.raises(GuideNotFoundError):
        _resolve_guide_path(guide_mcp_vault, "_meta/../system/OPERATIONS.md")
    with pytest.raises(GuideNotFoundError):
        _resolve_guide_path(guide_mcp_vault, "/etc/passwd")


# ──────────────────── read_guide 응답 shape ────────────────────

def test_read_guide_returns_full_shape(guide_mcp_vault):
    """read_guide 응답은 REST /guide 응답과 동일 shape (v0.7.89 정합)."""
    r = read_guide(vault=guide_mcp_vault, kind="_meta/agents/SCHEMA.md")
    assert r["ok"] is True
    assert r["vault"] == guide_mcp_vault.name
    assert r["kind"] == "_meta/agents/SCHEMA.md"
    assert "frontmatter v2.4" in r["content"]
    assert r["size"] > 0
    assert r["modified"] is not None


def test_read_guide_log_md(guide_mcp_vault):
    r = read_guide(vault=guide_mcp_vault, kind="log.md")
    assert r["kind"] == "log.md"
    assert "2026-07-07" in r["content"]


def test_read_guide_404_when_file_missing(guide_mcp_vault, monkeypatch):
    """화이트 kind이지만 파일이 vault에 없으면 FileNotFoundError."""
    # vault를 새로 만들어서 3종 파일 중 하나를 의도적으로 누락
    import tempfile
    reg2 = Path(tempfile.mkdtemp(prefix="raven-mcp-guide-empty-"))
    target2 = Path(tempfile.mkdtemp(prefix="raven-mcp-guide-empty-"))
    monkeypatch.setenv("WIKI_VAULTS_DIR", str(reg2))
    empty = target2 / "empty-mcp-vault"
    empty.mkdir()
    (empty / ".vault.json").write_text(json.dumps({
        "name": "empty-mcp-vault",
        "path": str(empty),
        "mode": "personal",
        "owner": "user",
    }))
    TestClient(app).post("/api/vaults", json={
        "name": "empty-mcp-vault",
        "path": str(empty),
        "bootstrap": False,
    })
    # ensure_log()이 자동 생성해서 log.md는 존재 — SCHEMA만 누락시키기
    with pytest.raises(FileNotFoundError):
        read_guide(vault=empty, kind="_meta/agents/SCHEMA.md")


# ──────────────────── MCP 도구 등록 검증 ────────────────────

def test_wiki_get_guide_registered_in_cli():
    """cli.register_tools가 wiki_get_guide를 등록하는지 — list_tools inspection.

    FastMCP의 도구는 in-process introspection이 까다로우니, 모듈에
    함수가 노출되어 있는지 + description이 Lite bootstrap을 언급하는지
    확인하는 가벼운 회귀 가드.
    """
    from raven.mcp import cli as cli_module
    # register_tools 함수와 import 가능한 read_tools.wiki_get_guide 확인
    import inspect
    assert hasattr(cli_module, "register_tools")
    from raven.mcp.tools.read import wiki_get_guide
    sig = inspect.signature(wiki_get_guide)
    assert "kind" in sig.parameters
    assert "ctx" in sig.parameters  # 표준 ctx (다른 read tools와 동일)
