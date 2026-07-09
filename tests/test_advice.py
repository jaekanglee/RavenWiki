from __future__ import annotations

from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from raven.api.server import app
from raven.core.vault import Vault
from raven.core import db as db_module


@pytest.fixture
def isolated_vault(tmp_path: Path, monkeypatch):
    reg_root = tmp_path / "registry"
    monkeypatch.setenv("WIKI_VAULTS_DIR", str(reg_root))
    vault = Vault.create("advice-test", tmp_path / "vault", bootstrap=False)
    content_dir = vault.root / "content"
    content_dir.mkdir(parents=True, exist_ok=True)
    return vault


@pytest.fixture
def client():
    return TestClient(app)


def test_advice_diagnosis_logic(client, isolated_vault: Vault) -> None:
    content_dir = isolated_vault.root / "content"

    # 1. 고립 노드 (Orphan) 생성
    (content_dir / "orphan-page.md").write_text(
        "---\ntitle: Orphan Page\ntype: concept\ntags: []\n---\nOrphan\n", encoding="utf-8"
    )

    # 2. 브릿지 노드를 통해 연결되는 두 영역 생성
    # 영역 A (folder: backend)
    (content_dir / "backend").mkdir(exist_ok=True)
    (content_dir / "backend" / "auth.md").write_text(
        "---\ntitle: Auth Module\ntype: concept\ntags: []\n---\nAuth\n", encoding="utf-8"
    )

    # 영역 B (folder: frontend)
    (content_dir / "frontend").mkdir(exist_ok=True)
    (content_dir / "frontend" / "ui.md").write_text(
        "---\ntitle: UI Component\ntype: concept\ntags: []\n---\nUI\n", encoding="utf-8"
    )

    # 브릿지 노드 (이 노드가 backend/auth 와 frontend/ui 를 연결)
    (content_dir / "bridge-page.md").write_text(
        """---
title: Bridge Page
type: concept
relations:
  - type: uses
    target: content/backend/auth
  - type: depends_on
    target: content/frontend/ui
---
Bridge
""", encoding="utf-8"
    )

    # DB 빌드 (이를 통해 PageRank, Betweenness Centrality 등 계산)
    db_module.build_db(isolated_vault, run_lint=False)

    # API 호출 테스트
    resp = client.get(f"/api/vaults/{isolated_vault.meta.name}/advice")
    assert resp.status_code == 200, resp.text
    data = resp.json()

    # 우리가 의도한 진단(브릿지 노드 감지, 고립 노드 감지)이 리스트에 포함되어 있는지 확인
    assert len(data) >= 2

    # 브릿지 진단 확인
    bridge_advices = [x for x in data if x["type"] == "bridge"]
    assert len(bridge_advices) > 0
    assert "Bridge Page" in bridge_advices[0]["message"]
    assert "backend" in bridge_advices[0]["message"]
    assert "frontend" in bridge_advices[0]["message"]
    assert bridge_advices[0]["slug"] == "content/bridge-page"

    # 고립 노드 진단 확인
    orphan_advices = [x for x in data if x["type"] == "orphan"]
    assert len(orphan_advices) > 0
    assert "Orphan Page" in orphan_advices[0]["message"]
    assert orphan_advices[0]["slug"] == "content/orphan-page"


def test_mcp_wiki_get_advice_registered() -> None:
    """MCP 진입점에서 wiki_get_advice 및 wiki_get_ai_advice가 정상적으로 등록되었는지 검증합니다."""
    from raven.mcp import cli as cli_module
    assert hasattr(cli_module, "register_tools")
    import inspect
    source = inspect.getsource(cli_module.register_tools)
    assert "wiki_get_advice" in source
    assert "wiki_get_ai_advice" in source


def test_ai_advice_api_call(client, isolated_vault: Vault) -> None:
    content_dir = isolated_vault.root / "content"
    # 고립 노드 (Orphan) 생성
    (content_dir / "orphan-page.md").write_text(
        "---\ntitle: Orphan Page\ntype: concept\ntags: []\n---\nOrphan\n", encoding="utf-8"
    )
    # DB 빌드
    db_module.build_db(isolated_vault, run_lint=False)
    
    # API 호출
    resp = client.get(f"/api/vaults/{isolated_vault.meta.name}/ai-advice")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    
    # ai_message 필드가 포함되어 있는지 확인
    assert "ai_message" in data[0]
    assert "고립" in data[0]["ai_message"] or "Orphan Page" in data[0]["ai_message"]


def test_relation_add_api(client, isolated_vault: Vault) -> None:
    content_dir = isolated_vault.root / "content"
    # 두 페이지 생성
    (content_dir / "page-a.md").write_text(
        "---\ntitle: Page A\ntype: concept\ntags: []\n---\nPage A content\n", encoding="utf-8"
    )
    (content_dir / "page-b.md").write_text(
        "---\ntitle: Page B\ntype: concept\ntags: []\n---\nPage B content\n", encoding="utf-8"
    )
    db_module.build_db(isolated_vault, run_lint=False)

    # API 호출로 두 페이지 간의 관계 맺기
    payload = {
        "source_slug": "content/page-a",
        "target_slug": "content/page-b",
        "relation_type": "uses",
        "evidence": "API test evidence",
        "reason": "API test reason",
        "actor": "user"
    }
    resp = client.post(f"/api/vaults/{isolated_vault.meta.name}/relations", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True

    # 실제로 파일에 써졌는지 확인하기 위해 DB 리빌드 후 조회
    db_module.build_db(isolated_vault, run_lint=False)
    
    # page-a.md 읽어서 frontmatter에 들어갔는지 검사
    content = (content_dir / "page-a.md").read_text(encoding="utf-8")
    assert "target: content/page-b" in content
    assert "type: uses" in content
