from __future__ import annotations

import pytest
import os
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from raven.api.server import app
from raven.core.vault import Vault
from raven.core import db as db_module
from raven.core.draft import generate_draft, commit_draft

@pytest.fixture
def isolated_vault(tmp_path: Path, monkeypatch) -> Vault:
    reg_root = tmp_path / "registry"
    monkeypatch.setenv("WIKI_VAULTS_DIR", str(reg_root))
    vault = Vault.create("draft-test", tmp_path / "vault", bootstrap=False)
    # Ensure directories exist
    vault.content_root.mkdir(parents=True, exist_ok=True)
    vault.drafts_root.mkdir(parents=True, exist_ok=True)
    return vault


@pytest.fixture
def client():
    return TestClient(app)


def test_draft_fallback(isolated_vault: Vault) -> None:
    """API Key가 없을 때 generate_draft가 fallback 로직을 사용하여 임시 초안을 빌드하고 파일로 저장하는지 검증합니다."""
    res = generate_draft(
        isolated_vault,
        topic="My Fallback Topic",
        outline="1. Intro\n2. Body\n3. Outro",
        associated_pages=["some-page", "another-page"]
    )
    
    assert res["ok"] is True
    assert res["title"] == "My Fallback Topic"
    assert "drafts/my-fallback-topic" in res["slug"]
    assert res["used_llm"] is False

    draft_file = Path(res["path"])
    assert draft_file.exists()
    
    content = draft_file.read_text(encoding="utf-8")
    assert "title: My Fallback Topic" in content
    assert "type: concept" in content
    assert "[[some-page]]" in content
    assert "[[another-page]]" in content


def test_draft_with_mock_llm(isolated_vault: Vault, monkeypatch) -> None:
    """Gemini API 호출을 모킹하여 사용자 주제에 맞춰 Frontmatter 및 본문, 위키링크가 삽입된 초안이 생성되는지 검증합니다."""
    monkeypatch.setenv("GEMINI_API_KEY", "mock-key")

    mock_content = (
        "---\n"
        "title: Generated Topic\n"
        "type: concept\n"
        "tags: [ai, draft]\n"
        "created: 2026-07-10\n"
        "updated: 2026-07-10\n"
        "---\n\n"
        "This is rich body content.\n"
        "Check this out: [[some-page]].\n"
    )

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": mock_content
                        }
                    ]
                }
            }
        ]
    }

    with patch("httpx.post", return_value=mock_response) as mock_post:
        res = generate_draft(
            isolated_vault,
            topic="Generated Topic",
            outline="Just outline",
            associated_pages=["some-page"]
        )
        assert res["ok"] is True
        assert res["title"] == "Generated Topic"
        assert res["used_llm"] is True
        assert Path(res["path"]).exists()

        content = Path(res["path"]).read_text(encoding="utf-8")
        assert "title: Generated Topic" in content
        assert "[[some-page]]" in content
        mock_post.assert_called_once()


def test_draft_commit(isolated_vault: Vault) -> None:
    """초안이 생성된 후 commit_draft를 호출하면 content/ 하위로 파일이 이동하고 DB에 정상 반영되는지 검증합니다."""
    # 1. 초안 강제 생성
    draft_dir = isolated_vault.root / "drafts"
    draft_dir.mkdir(parents=True, exist_ok=True)
    draft_file = draft_dir / "my-new-topic.md"
    draft_file.write_text(
        "---\ntitle: My New Topic\ntype: concept\ntags: [draft]\n---\nBody text [[reference-page]]\n",
        encoding="utf-8"
    )

    # 2. Commit 수행
    res = commit_draft(isolated_vault, "drafts/my-new-topic")
    assert res["ok"] is True
    assert res["slug"] == "content/my-new-topic"
    
    # 3. 파일 이동 확인
    assert not draft_file.exists()
    committed_file = isolated_vault.content_root / "my-new-topic.md"
    assert committed_file.exists()

    # 4. DB 반영 확인 (rebuild 결과로 pages에 반영됨)
    db_module.build_db(isolated_vault, run_lint=False)
    conn = db_module.connect(isolated_vault)
    row = conn.execute("SELECT slug, title FROM pages WHERE slug = 'content/my-new-topic'").fetchone()
    conn.close()
    
    assert row is not None
    assert row[1] == "My New Topic"


def test_draft_api(client, isolated_vault: Vault, monkeypatch) -> None:
    """REST API /api/vaults/{name}/drafts/generate 및 commit 엔드포인트를 검증합니다."""
    monkeypatch.setenv("GEMINI_API_KEY", "") # Fallback 유발

    # 1. Generate API 호출
    gen_resp = client.post(
        f"/api/vaults/{isolated_vault.meta.name}/drafts/generate",
        json={
            "topic": "API Draft Topic",
            "outline": "Introduction",
            "associated_pages": ["another-doc"]
        }
    )
    assert gen_resp.status_code == 200
    gen_data = gen_resp.json()
    assert gen_data["ok"] is True
    assert gen_data["title"] == "API Draft Topic"
    draft_slug = gen_data["slug"]

    # 2. Commit API 호출
    commit_resp = client.post(
        f"/api/vaults/{isolated_vault.meta.name}/drafts/commit",
        json={
            "draft_slug": draft_slug
        }
    )
    assert commit_resp.status_code == 200
    commit_data = commit_resp.json()
    assert commit_data["ok"] is True
    assert "content/" in commit_data["slug"]

    # content 디렉토리에 실제 파일 생성 확인
    committed_path = Path(commit_data["path"])
    assert committed_path.exists()
    assert committed_path.name == "api-draft-topic.md"


def test_mcp_draft_registered() -> None:
    """MCP 진입점에서 wiki_generate_draft 및 wiki_commit_draft 도구가 등록되어 있는지 검증합니다."""
    from raven.mcp import cli as cli_module
    import inspect
    assert hasattr(cli_module, "register_tools")
    source = inspect.getsource(cli_module.register_tools)
    assert "wiki_generate_draft" in source
    assert "wiki_commit_draft" in source
