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
    vault = Vault.create("draft-test", tmp_path / "vault")
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
    """MCP 진입점 소스에 wiki_generate_draft 및 wiki_commit_draft 도구가 등록되어 있는지 검증합니다."""
    from pathlib import Path
    cli_src = (Path(__file__).parent.parent / "raven" / "mcp" / "cli.py").read_text(encoding="utf-8")
    assert "wiki_generate_draft" in cli_src
    assert "wiki_commit_draft" in cli_src


# ──────────────────────────────────────────────
# Template feature removal regression guard
# ──────────────────────────────────────────────

def test_draft_fallback_has_no_template_feature_artifacts(isolated_vault: Vault) -> None:
    """초안 생성은 vault별 템플릿 파일·Dashboard 템플릿 화면 없이 기본 구조를 사용한다."""
    repo_root = Path(__file__).parent.parent

    res = generate_draft(
        isolated_vault,
        topic="Fallback Draft Topic",
        outline="1. Intro",
    )

    assert res["ok"] is True
    assert Path(res["path"]).exists()
    assert not (isolated_vault.root / "_templates").exists()

    draft_source = (repo_root / "raven" / "core" / "draft.py").read_text(encoding="utf-8")
    api_source = (repo_root / "raven" / "api" / "server.py").read_text(encoding="utf-8")
    app_source = (repo_root / "dashboard" / "src" / "App.tsx").read_text(encoding="utf-8")
    layout_source = (repo_root / "dashboard" / "src" / "components" / "Layout.tsx").read_text(encoding="utf-8")

    assert "_templates" not in draft_source
    assert '"/api/vaults/{name}/templates"' not in api_source
    assert "TemplateEditorPage" not in app_source
    assert 'to: "/settings/templates"' not in layout_source
    assert not (repo_root / "dashboard" / "src" / "routes" / "TemplateEditorPage.tsx").exists()


def test_commit_conflict_without_overwrite(isolated_vault: Vault) -> None:
    """content/ 에 동일 slug 파일이 이미 존재하면 overwrite=False(기본)일 때 conflict=True를 반환합니다."""
    # 기존 content 파일 배치
    content_dir = isolated_vault.content_root
    content_dir.mkdir(parents=True, exist_ok=True)
    (content_dir / "conflict-topic.md").write_text(
        "---\ntitle: Existing Page\ntype: concept\n---\n기존 내용",
        encoding="utf-8",
    )

    # draft 파일 배치
    drafts_dir = isolated_vault.root / "drafts"
    drafts_dir.mkdir(parents=True, exist_ok=True)
    (drafts_dir / "conflict-topic.md").write_text(
        "---\ntitle: Conflict Topic\ntype: concept\n---\n새 초안 내용",
        encoding="utf-8",
    )

    res = commit_draft(isolated_vault, "drafts/conflict-topic", overwrite=False)

    assert res["ok"] is False
    assert res.get("conflict") is True
    assert "existing_content" in res
    assert "draft_content" in res
    # 기존 파일은 그대로여야 한다
    assert (content_dir / "conflict-topic.md").exists()
    # draft 파일도 아직 남아있어야 한다
    assert (drafts_dir / "conflict-topic.md").exists()


def test_commit_conflict_resolved_with_overwrite(isolated_vault: Vault) -> None:
    """overwrite=True를 전달하면 충돌 없이 기존 파일을 대체하고 발행합니다."""
    content_dir = isolated_vault.content_root
    content_dir.mkdir(parents=True, exist_ok=True)
    (content_dir / "overwrite-topic.md").write_text(
        "---\ntitle: Old Page\ntype: concept\n---\n예전 내용",
        encoding="utf-8",
    )

    drafts_dir = isolated_vault.root / "drafts"
    drafts_dir.mkdir(parents=True, exist_ok=True)
    (drafts_dir / "overwrite-topic.md").write_text(
        "---\ntitle: Overwrite Topic\ntype: concept\n---\n새 내용으로 대체",
        encoding="utf-8",
    )

    res = commit_draft(isolated_vault, "drafts/overwrite-topic", overwrite=True)

    assert res["ok"] is True
    assert res["slug"] == "content/overwrite-topic"
    committed_text = (content_dir / "overwrite-topic.md").read_text(encoding="utf-8")
    assert "새 내용으로 대체" in committed_text
    # 드래프트 파일은 사라져야 한다
    assert not (drafts_dir / "overwrite-topic.md").exists()


def test_commit_conflict_api_returns_409(client, isolated_vault: Vault) -> None:
    """API에서 충돌 시 HTTP 409와 conflict 플래그가 포함된 JSON을 반환합니다."""
    content_dir = isolated_vault.content_root
    content_dir.mkdir(parents=True, exist_ok=True)
    (content_dir / "api-conflict.md").write_text(
        "---\ntitle: API Conflict\ntype: concept\n---\n기존",
        encoding="utf-8",
    )

    drafts_dir = isolated_vault.root / "drafts"
    drafts_dir.mkdir(parents=True, exist_ok=True)
    (drafts_dir / "api-conflict.md").write_text(
        "---\ntitle: API Conflict\ntype: concept\n---\n신규",
        encoding="utf-8",
    )

    resp = client.post(
        f"/api/vaults/{isolated_vault.meta.name}/drafts/commit",
        json={"draft_slug": "drafts/api-conflict", "overwrite": False},
    )
    assert resp.status_code == 409
    data = resp.json()
    assert data["conflict"] is True
    assert "existing_content" in data
    assert "draft_content" in data


def test_mcp_generate_draft_has_no_template_param() -> None:
    """MCP 초안 생성 도구는 vault별 템플릿 파라미터를 노출하지 않는다."""
    from pathlib import Path
    cli_src = (Path(__file__).parent.parent / "raven" / "mcp" / "cli.py").read_text(encoding="utf-8")
    assert "draft_type" not in cli_src


def test_mcp_commit_draft_overwrite_param() -> None:
    """MCP wiki_commit_draft 소스에 overwrite 파라미터가 선언되어 있습니다."""
    from pathlib import Path
    cli_src = (Path(__file__).parent.parent / "raven" / "mcp" / "cli.py").read_text(encoding="utf-8")
    assert "overwrite" in cli_src

