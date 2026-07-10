from __future__ import annotations

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from raven.api.server import app
from raven.core.vault import Vault
from raven.core import db as db_module
from raven.core.tagger import suggest_tags

@pytest.fixture
def isolated_vault(tmp_path: Path, monkeypatch) -> Vault:
    reg_root = tmp_path / "registry"
    monkeypatch.setenv("WIKI_VAULTS_DIR", str(reg_root))
    vault = Vault.create("tagger-test", tmp_path / "vault", bootstrap=False)
    content_dir = vault.root / "content"
    content_dir.mkdir(parents=True, exist_ok=True)
    return vault


@pytest.fixture
def client():
    return TestClient(app)


def test_tagger_fallback(isolated_vault: Vault) -> None:
    """API Key가 없을 때, suggest_tags가 기존 태그들을 활용한 키워드 매칭 fallback 결과를 반환하는지 검증합니다."""
    content_dir = isolated_vault.root / "content"
    (content_dir / "auth.md").write_text(
        "---\ntitle: Authentication Guide\ntype: concept\ntags: [auth, security]\n---\nJWT token authentication details\n", encoding="utf-8"
    )
    db_module.build_db(isolated_vault, run_lint=False)

    res = suggest_tags(isolated_vault, "This is about security and token auth.", title="Auth")
    assert res["ok"] is True
    assert "security" in res["tags"] or "auth" in res["tags"]
    assert res["used_llm"] is False


def test_tagger_with_mock_llm(isolated_vault: Vault, monkeypatch) -> None:
    """Gemini API가 활성화되어 있고 성공적인 응답을 반환할 때, suggest_tags가 올바르게 결과를 파싱하는지 검증합니다."""
    monkeypatch.setenv("GEMINI_API_KEY", "mock-key")
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": "[\"jwt\", \"auth\", \"security\"]"
                        }
                    ]
                }
            }
        ]
    }
    
    with patch("httpx.post", return_value=mock_response) as mock_post:
        res = suggest_tags(isolated_vault, "User auth system using JWT token", title="Authentication")
        assert res["ok"] is True
        assert res["tags"] == ["jwt", "auth", "security"]
        assert res["used_llm"] is True
        mock_post.assert_called_once()


def test_suggest_tags_api(client, isolated_vault: Vault) -> None:
    """REST API /api/vaults/{name}/suggest-tags 엔드포인트 호출을 검증합니다."""
    content_dir = isolated_vault.root / "content"
    (content_dir / "db.md").write_text(
        "---\ntitle: Database Design\ntype: concept\ntags: [database, sqlite]\n---\nSQLite database relations\n", encoding="utf-8"
    )
    db_module.build_db(isolated_vault, run_lint=False)

    resp = client.post(
        f"/api/vaults/{isolated_vault.meta.name}/suggest-tags",
        json={"content": "SQLite database setup and migration", "title": "DB Config"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert isinstance(data["tags"], list)


def test_mcp_suggest_tags_registered() -> None:
    """MCP 진입점에서 wiki_suggest_tags 도구가 등록되어 있는지 검증합니다."""
    from raven.mcp import cli as cli_module
    import inspect
    assert hasattr(cli_module, "register_tools")
    source = inspect.getsource(cli_module.register_tools)
    assert "wiki_suggest_tags" in source
