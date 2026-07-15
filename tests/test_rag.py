from __future__ import annotations

from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from raven.api.server import app
from raven.core.vault import Vault
from raven.core import db as db_module
from raven.core.rag import query_rag

@pytest.fixture
def isolated_vault(tmp_path: Path, monkeypatch) -> Vault:
    reg_root = tmp_path / "registry"
    monkeypatch.setenv("WIKI_VAULTS_DIR", str(reg_root))
    vault = Vault.create("rag-test", tmp_path / "vault")
    content_dir = vault.root / "content"
    content_dir.mkdir(parents=True, exist_ok=True)
    return vault


@pytest.fixture
def client():
    return TestClient(app)


def test_rag_query_core_fallback(isolated_vault: Vault) -> None:
    """API Key가 없을 때, query_rag가 하이브리드 검색 결과를 바탕으로 요약 및 추천하는 fallback 답변을 반환하는지 검증합니다."""
    content_dir = isolated_vault.root / "content"
    (content_dir / "auth.md").write_text(
        "---\ntitle: Authentication Guide\ntype: concept\ntags: [auth]\n---\nJWT token authentication details\n", encoding="utf-8"
    )
    db_module.build_db(isolated_vault, run_lint=False)

    res = query_rag(isolated_vault, "JWT")
    assert res["ok"] is True
    assert res["query"] == "JWT"
    assert "RAG Fallback" in res["answer"]
    assert len(res["citations"]) >= 1
    slugs = [c["slug"] for c in res["citations"]]
    assert "content/auth" in slugs
    # Find the citation for auth
    auth_cit = [c for c in res["citations"] if c["slug"] == "content/auth"][0]
    assert auth_cit["title"] == "Authentication Guide"
    assert "file://" in auth_cit["file_url"]
    assert res["used_llm"] is False


def test_rag_query_api(client, isolated_vault: Vault) -> None:
    """REST API를 통해 RAG 질의를 보냈을 때 정상적으로 200 응답과 JSON을 반환하는지 검증합니다."""
    content_dir = isolated_vault.root / "content"
    (content_dir / "db.md").write_text(
        "---\ntitle: Database Replication\ntype: concept\ntags: [db]\n---\nMySQL master-slave replication setup\n", encoding="utf-8"
    )
    db_module.build_db(isolated_vault, run_lint=False)

    resp = client.get(f"/api/vaults/{isolated_vault.meta.name}/rag/query?query=MySQL")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["query"] == "MySQL"
    assert "answer" in data
    assert len(data["citations"]) >= 1
    slugs = [c["slug"] for c in data["citations"]]
    assert "content/db" in slugs


def test_mcp_rag_query_registered() -> None:
    """MCP 진입점에서 wiki_rag_query 도구가 등록되어 있는지 검증합니다."""
    from raven.mcp import cli as cli_module
    import inspect
    assert hasattr(cli_module, "register_tools")
    source = inspect.getsource(cli_module.register_tools)
    assert "wiki_rag_query" in source
