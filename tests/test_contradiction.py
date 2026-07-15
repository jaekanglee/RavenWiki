from __future__ import annotations

import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from raven.api.server import app
from raven.core.vault import Vault
from raven.core import db as db_module
from raven.core.contradiction import check_contradictions

@pytest.fixture
def isolated_vault(tmp_path: Path, monkeypatch) -> Vault:
    reg_root = tmp_path / "registry"
    monkeypatch.setenv("WIKI_VAULTS_DIR", str(reg_root))
    vault = Vault.create("contradiction-test", tmp_path / "vault")
    content_dir = vault.root / "content"
    content_dir.mkdir(parents=True, exist_ok=True)
    return vault


@pytest.fixture
def client():
    return TestClient(app)


def test_contradiction_fallback(isolated_vault: Vault) -> None:
    """API Key가 없을 때, check_contradictions가 heuristic 탐지 로직으로 충돌을 포착하는지 검증합니다."""
    content_dir = isolated_vault.root / "content"
    (content_dir / "service_a.md").write_text(
        "---\n"
        "title: Service A\n"
        "type: concept\n"
        "tags: [service]\n"
        "relations:\n"
        "  - type: depends_on\n"
        "    target: content/service_b\n"
        "    evidence: depends on B\n"
        "    reason: logic\n"
        "---\n"
        "Service A runs on port 8080\n",
        encoding="utf-8"
    )
    (content_dir / "service_b.md").write_text(
        "---\n"
        "title: Service B\n"
        "type: concept\n"
        "tags: [service]\n"
        "---\n"
        "Service B runs on port 9090\n",
        encoding="utf-8"
    )
    db_module.build_db(isolated_vault, run_lint=False)

    res = check_contradictions(isolated_vault)
    assert res["ok"] is True
    assert len(res["contradictions"]) >= 1
    c = res["contradictions"][0]
    assert c["source_slug"] == "content/service_a"
    assert c["target_slug"] == "content/service_b"
    assert c["relation_type"] == "depends_on"
    assert "port" in c["description"].lower() or "포트" in c["description"]
    assert res["used_llm"] is False


def test_contradiction_with_mock_llm(isolated_vault: Vault, monkeypatch) -> None:
    """Gemini API가 활성화되어 있고 성공적인 응답을 반환할 때, 모순 정보를 올바르게 수립하는지 검증합니다."""
    monkeypatch.setenv("GEMINI_API_KEY", "mock-key")
    
    content_dir = isolated_vault.root / "content"
    (content_dir / "service_a.md").write_text(
        "---\n"
        "title: Service A\n"
        "type: concept\n"
        "tags: [service]\n"
        "relations:\n"
        "  - type: depends_on\n"
        "    target: content/service_b\n"
        "    evidence: depends on B\n"
        "    reason: logic\n"
        "---\n"
        "Service A uses JSON API\n",
        encoding="utf-8"
    )
    (content_dir / "service_b.md").write_text(
        "---\n"
        "title: Service B\n"
        "type: concept\n"
        "tags: [service]\n"
        "---\n"
        "Service B only supports XML protocol\n",
        encoding="utf-8"
    )
    db_module.build_db(isolated_vault, run_lint=False)

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": json.dumps([
                                {
                                    "source_slug": "content/service_a",
                                    "target_slug": "content/service_b",
                                    "relation_type": "depends_on",
                                    "description": "JSON vs XML 프로토콜 불일치 충돌",
                                    "proposed_action": "update_relation",
                                    "proposed_data": {
                                        "source_slug": "content/service_a",
                                        "target_slug": "content/service_b",
                                        "relation_type": "related",
                                        "evidence": "JSON vs XML",
                                        "reason": "Protocol mismatch"
                                    }
                                }
                            ])
                        }
                    ]
                }
            }
        ]
    }

    with patch("httpx.post", return_value=mock_response) as mock_post:
        res = check_contradictions(isolated_vault)
        assert res["ok"] is True
        assert len(res["contradictions"]) == 1
        c = res["contradictions"][0]
        assert c["source_slug"] == "content/service_a"
        assert c["description"] == "JSON vs XML 프로토콜 불일치 충돌"
        assert res["used_llm"] is True


def test_contradiction_api(client, isolated_vault: Vault) -> None:
    """REST API /api/vaults/{name}/lint/contradictions 및 /resolve 엔드포인트 호출을 검증합니다."""
    content_dir = isolated_vault.root / "content"
    (content_dir / "service_a.md").write_text(
        "---\n"
        "title: Service A\n"
        "type: concept\n"
        "tags: [service]\n"
        "relations:\n"
        "  - type: depends_on\n"
        "    target: content/service_b\n"
        "    evidence: depends on B\n"
        "    reason: logic\n"
        "---\n"
        "Service A runs on port 8080\n",
        encoding="utf-8"
    )
    (content_dir / "service_b.md").write_text(
        "---\n"
        "title: Service B\n"
        "type: concept\n"
        "tags: [service]\n"
        "---\n"
        "Service B runs on port 9090\n",
        encoding="utf-8"
    )
    db_module.build_db(isolated_vault, run_lint=False)

    # 1. GET contradictions
    resp = client.get(f"/api/vaults/{isolated_vault.meta.name}/lint/contradictions")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert isinstance(data["contradictions"], list)

    # 2. POST resolve
    resp = client.post(
        f"/api/vaults/{isolated_vault.meta.name}/lint/contradictions/resolve",
        json={
            "source_slug": "content/service_a",
            "target_slug": "content/service_b",
            "relation_type": "depends_on",
            "action": "update_relation",
            "evidence": "Resolved port mismatch",
            "reason": "Test resolve"
        }
    )
    assert resp.status_code == 200
    res_data = resp.json()
    assert res_data["ok"] is True


def test_mcp_contradictions_registered() -> None:
    """MCP 진입점에서 wiki_check_contradictions 도구가 등록되어 있는지 검증합니다."""
    from raven.mcp import cli as cli_module
    import inspect
    assert hasattr(cli_module, "register_tools")
    source = inspect.getsource(cli_module.register_tools)
    assert "wiki_check_contradictions" in source
