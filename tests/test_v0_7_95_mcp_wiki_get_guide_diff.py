"""v0.7.95 — MCP wiki_get_guide_diff (Lite bootstrap 3종 diff).

REST /api/vaults/{name}/guide-diff/{kind} (v0.7.94) 와 1:1 contract.
화이트리스트 fail-closed, 응답 shape 동일. difflib 표준 (외부 의존성 0).
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
    read_guide_diff,
    _resolve_guide_template,
)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def diff_mcp_vault(monkeypatch):
    """Lite bootstrap 3종을 템플릿과 다르게 작성한 vault (MCP 테스트용)."""
    reg = Path(tempfile.mkdtemp(prefix="raven-mcp-diff-reg-"))
    target = Path(tempfile.mkdtemp(prefix="raven-mcp-diff-target-"))
    monkeypatch.setenv("WIKI_VAULTS_DIR", str(reg))

    v_root = target / "mcp-diff-vault"
    v_root.mkdir()
    (v_root / "_meta" / "agents").mkdir(parents=True)

    (v_root / "_meta" / "agents" / "SCHEMA.md").write_text(
        "# SCHEMA (vault-modified)\n\nvault edited line\n", encoding="utf-8"
    )
    (v_root / "_meta" / "agents" / "PROJECT-WORKFLOW.md").write_text(
        "# PROJECT-WORKFLOW (vault-modified)\n\nanother edited line\n", encoding="utf-8"
    )
    (v_root / "log.md").write_text(
        "# Vault Log (vault-modified)\n\n- vault init\n", encoding="utf-8"
    )
    # 비화이트
    (v_root / "_meta" / "system").mkdir(parents=True)
    (v_root / "_meta" / "system" / "SECRET.md").write_text("secret", encoding="utf-8")

    (v_root / ".vault.json").write_text(json.dumps({
        "name": "mcp-diff-vault",
        "path": str(v_root),
        "mode": "personal",
        "owner": "user",
    }))

    TestClient(app).post("/api/vaults", json={
        "name": "mcp-diff-vault",
        "path": str(v_root),
        "bootstrap": False,
    })

    yield v_root


# ──────────────────── 화이트 3종 ────────────────────

def test_resolve_guide_template_three_kinds():
    for kind in LITE_GUIDE_KINDS:
        rel, tpl = _resolve_guide_template(kind)
        assert rel == kind
        # template path 는 raven install layout (agent/ or log.md)
        assert tpl.startswith("agent/") or tpl == "log.md"


def test_resolve_guide_template_rejects_non_whitelist():
    with pytest.raises(GuideNotFoundError) as exc_info:
        _resolve_guide_template("_meta/system/SECRET.md")
    assert "whitelist" in str(exc_info.value).lower()


def test_resolve_guide_template_rejects_path_traversal():
    with pytest.raises(GuideNotFoundError):
        _resolve_guide_template("_meta/../system/SECRET.md")


# ──────────────────── read_guide_diff 응답 ────────────────────

def test_read_guide_diff_returns_modified(diff_mcp_vault):
    r = read_guide_diff(vault=diff_mcp_vault, kind="_meta/agents/SCHEMA.md")
    assert r["ok"] is True
    assert r["vault"] == "mcp-diff-vault"
    assert r["kind"] == "_meta/agents/SCHEMA.md"
    assert r["identical"] is False
    assert r["stats"]["added"] > 0 or r["stats"]["removed"] > 0
    assert isinstance(r["diff_lines"], list)
    assert len(r["diff_lines"]) > 0
    for line in r["diff_lines"]:
        assert "tag" in line
        assert "content" in line
        assert line["tag"] in ("+", "-", " ")


def test_read_guide_diff_log_md(diff_mcp_vault):
    r = read_guide_diff(vault=diff_mcp_vault, kind="log.md")
    assert r["identical"] is False
    # vault가 다른 내용이라 removed 또는 added 최소 1
    assert (r["stats"]["added"] + r["stats"]["removed"]) >= 1


def test_read_guide_diff_404_for_missing_file(diff_mcp_vault, monkeypatch):
    """화이트 kind이지만 파일이 vault에 없으면 FileNotFoundError."""
    import tempfile
    reg2 = Path(tempfile.mkdtemp(prefix="raven-mcp-diff-empty-"))
    target2 = Path(tempfile.mkdtemp(prefix="raven-mcp-diff-empty-"))
    monkeypatch.setenv("WIKI_VAULTS_DIR", str(reg2))
    empty = target2 / "empty-mcp-diff-vault"
    empty.mkdir()
    (empty / ".vault.json").write_text(json.dumps({
        "name": "empty-mcp-diff-vault",
        "path": str(empty),
        "mode": "personal",
        "owner": "user",
    }))
    TestClient(app).post("/api/vaults", json={
        "name": "empty-mcp-diff-vault",
        "path": str(empty),
        "bootstrap": False,
    })
    # ensure_log()이 log.md는 자동 생성 — SCHEMA는 누락
    with pytest.raises(FileNotFoundError):
        read_guide_diff(vault=empty, kind="_meta/agents/SCHEMA.md")


def test_read_guide_diff_truncates_at_200_lines(diff_mcp_vault):
    """PROJECT-WORKFLOW.md를 매우 다르게 작성 → truncation=True."""
    big = "\n".join([f"vault-line-{i}" for i in range(300)]) + "\n"
    (diff_mcp_vault / "_meta" / "agents" / "PROJECT-WORKFLOW.md").write_text(
        big, encoding="utf-8"
    )
    r = read_guide_diff(vault=diff_mcp_vault, kind="_meta/agents/PROJECT-WORKFLOW.md")
    assert r["identical"] is False
    assert r["truncated"] is True
    assert r["truncation_note"] is not None
    assert "200" in r["truncation_note"]
    assert len(r["diff_lines"]) <= 200


# ──────────────────── MCP cli 등록 확인 ────────────────────

def test_wiki_get_guide_diff_registered_in_cli():
    """cli.register_tools가 wiki_get_guide_diff를 등록하는지 — 가벼운 회귀."""
    from raven.mcp import cli as cli_module
    from raven.mcp.tools.read import wiki_get_guide_diff
    import inspect
    assert hasattr(cli_module, "register_tools")
    sig = inspect.signature(wiki_get_guide_diff)
    assert "kind" in sig.parameters
    assert "ctx" in sig.parameters
