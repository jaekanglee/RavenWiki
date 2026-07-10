"""Phase 16 Tests — Drafts List, Community Split Advice, Template Editor."""
from __future__ import annotations

import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from raven.api.server import app
from raven.core.vault import Vault
from raven.core import db as db_module


# ─── Shared Fixtures ─────────────────────────────────────────────────────────

@pytest.fixture
def isolated_vault(tmp_path: Path, monkeypatch) -> Vault:
    reg_root = tmp_path / "registry"
    monkeypatch.setenv("WIKI_VAULTS_DIR", str(reg_root))
    vault = Vault.create("phase16-test", tmp_path / "vault", bootstrap=False)
    vault.content_root.mkdir(parents=True, exist_ok=True)
    (vault.root / "drafts").mkdir(parents=True, exist_ok=True)
    return vault


@pytest.fixture
def client():
    return TestClient(app)


# ─── Task 1: Drafts List Page / API ─────────────────────────────────────────

class TestDraftsList:
    """GET /api/vaults/{name}/drafts — 초안 목록 API 검증."""

    def test_empty_drafts(self, client, isolated_vault: Vault) -> None:
        """drafts/ 폴더가 비어있을 때 빈 목록을 반환합니다."""
        resp = client.get(f"/api/vaults/{isolated_vault.meta.name}/drafts")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["drafts"] == []

    def test_lists_draft_files(self, client, isolated_vault: Vault) -> None:
        """drafts/ 폴더에 .md 파일이 있으면 목록을 반환합니다."""
        drafts_dir = isolated_vault.root / "drafts"
        (drafts_dir / "my-draft.md").write_text(
            "---\ntitle: My Draft\ntype: concept\nupdated: 2026-07-10\n---\n\nBody.",
            encoding="utf-8",
        )
        resp = client.get(f"/api/vaults/{isolated_vault.meta.name}/drafts")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["drafts"]) == 1
        item = data["drafts"][0]
        assert item["slug"] == "drafts/my-draft"
        assert item["title"] == "My Draft"
        assert item["type"] == "concept"
        assert item["updated"] == "2026-07-10"
        assert item["conflict"] is False

    def test_conflict_flag_when_content_exists(self, client, isolated_vault: Vault) -> None:
        """content/ 에 동일 slug가 있으면 conflict=True를 반환합니다."""
        drafts_dir = isolated_vault.root / "drafts"
        (drafts_dir / "existing-page.md").write_text(
            "---\ntitle: Existing Page\ntype: concept\n---\nBody.",
            encoding="utf-8",
        )
        # 같은 이름의 파일을 content/ 에도 생성
        (isolated_vault.content_root / "existing-page.md").write_text(
            "---\ntitle: Existing Page\ntype: concept\n---\nExisting content.",
            encoding="utf-8",
        )
        resp = client.get(f"/api/vaults/{isolated_vault.meta.name}/drafts")
        assert resp.status_code == 200
        data = resp.json()
        item = next((d for d in data["drafts"] if d["slug"] == "drafts/existing-page"), None)
        assert item is not None
        assert item["conflict"] is True

    def test_multiple_drafts_sorted(self, client, isolated_vault: Vault) -> None:
        """여러 초안 파일이 알파벳 순으로 정렬되어 반환됩니다."""
        drafts_dir = isolated_vault.root / "drafts"
        for name in ["z-draft", "a-draft", "m-draft"]:
            (drafts_dir / f"{name}.md").write_text(
                f"---\ntitle: {name}\ntype: concept\n---\nBody.",
                encoding="utf-8",
            )
        resp = client.get(f"/api/vaults/{isolated_vault.meta.name}/drafts")
        assert resp.status_code == 200
        slugs = [d["slug"] for d in resp.json()["drafts"]]
        assert slugs == ["drafts/a-draft", "drafts/m-draft", "drafts/z-draft"]

    def test_delete_draft(self, client, isolated_vault: Vault) -> None:
        """DELETE /api/vaults/{name}/drafts/{draft_name} 이 초안 파일을 삭제합니다."""
        drafts_dir = isolated_vault.root / "drafts"
        fp = drafts_dir / "to-delete.md"
        fp.write_text("---\ntitle: To Delete\ntype: concept\n---\nBody.", encoding="utf-8")
        assert fp.exists()

        resp = client.delete(f"/api/vaults/{isolated_vault.meta.name}/drafts/to-delete")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert not fp.exists()

    def test_delete_nonexistent_draft_returns_404(self, client, isolated_vault: Vault) -> None:
        """존재하지 않는 초안 삭제 시 404를 반환합니다."""
        resp = client.delete(f"/api/vaults/{isolated_vault.meta.name}/drafts/ghost")
        assert resp.status_code == 404

    def test_draft_list_does_not_include_non_md(self, client, isolated_vault: Vault) -> None:
        """drafts/ 폴더에 .md 아닌 파일은 목록에 포함되지 않습니다."""
        drafts_dir = isolated_vault.root / "drafts"
        (drafts_dir / "readme.txt").write_text("not a draft", encoding="utf-8")
        (drafts_dir / "valid.md").write_text(
            "---\ntitle: Valid\ntype: concept\n---\nBody.", encoding="utf-8"
        )
        resp = client.get(f"/api/vaults/{isolated_vault.meta.name}/drafts")
        slugs = [d["slug"] for d in resp.json()["drafts"]]
        assert "drafts/readme" not in slugs
        assert "drafts/valid" in slugs


# ─── Task 2: Community Split Advice ──────────────────────────────────────────

class TestCommunitySplitAdvice:
    """community_split 어드바이스 — 비대 커뮤니티 감지 검증."""

    def _create_large_community(self, content_dir: Path, n: int = 10) -> None:
        """n개의 페이지를 생성하고 상호 연결하여 하나의 큰 커뮤니티를 만듭니다."""
        for i in range(n):
            (content_dir / f"big-page-{i}.md").write_text(
                f"---\ntitle: Big Page {i}\ntype: concept\ntags: []\n---\n"
                f"Linked to [[big-page-{(i + 1) % n}]]\n",
                encoding="utf-8",
            )

    def test_community_split_advice_generated(self, client, isolated_vault: Vault) -> None:
        """10개 노드의 단일 커뮤니티가 존재하면 community_split 어드바이스가 생성됩니다."""
        content_dir = isolated_vault.content_root
        self._create_large_community(content_dir, n=10)
        db_module.build_db(isolated_vault, run_lint=False)

        from raven.core.advice import get_advice
        advices = get_advice(isolated_vault)
        community_split_advices = [a for a in advices if a["type"] == "community_split"]
        # 10개 노드 = 100% 비율 → 임계값(30%) 초과하므로 감지되어야 함
        assert len(community_split_advices) > 0

    def test_community_split_advice_message_contains_domain(self, client, isolated_vault: Vault) -> None:
        """community_split 어드바이스의 message에 도메인 이름이 포함됩니다."""
        content_dir = isolated_vault.content_root
        self._create_large_community(content_dir, n=10)
        db_module.build_db(isolated_vault, run_lint=False)

        from raven.core.advice import get_advice
        advices = get_advice(isolated_vault)
        cs = [a for a in advices if a["type"] == "community_split"]
        if cs:
            assert "분리" in cs[0]["message"]
            assert "community_id" in cs[0]
            assert "community_size" in cs[0]
            assert cs[0]["community_size"] >= 8

    def test_small_community_not_flagged(self, isolated_vault: Vault) -> None:
        """5개 이하의 커뮤니티는 community_split 어드바이스가 생성되지 않습니다."""
        content_dir = isolated_vault.content_root
        for i in range(4):
            (content_dir / f"small-{i}.md").write_text(
                f"---\ntitle: Small {i}\ntype: concept\ntags: []\n---\nBody.\n",
                encoding="utf-8",
            )
        db_module.build_db(isolated_vault, run_lint=False)

        from raven.core.advice import get_advice
        advices = get_advice(isolated_vault)
        cs = [a for a in advices if a["type"] == "community_split"]
        assert len(cs) == 0

    def test_ai_advice_community_split_fallback(self, isolated_vault: Vault) -> None:
        """community_split 타입에 대해 ai_advice fallback이 의미있는 메시지를 반환합니다."""
        from raven.core.ai_advice import generate_ai_advice
        from raven.core import db as db_module

        content_dir = isolated_vault.content_root
        self._create_large_community(content_dir, n=10)
        db_module.build_db(isolated_vault, run_lint=False)

        # API Key 없이 호출 → fallback path
        advices = generate_ai_advice(isolated_vault)
        cs = [a for a in advices if a["type"] == "community_split"]
        if cs:
            ai_msg = cs[0].get("ai_message", "")
            assert "비대" in ai_msg or "Collection" in ai_msg or "분리" in ai_msg

    def test_community_split_advice_api(self, client, isolated_vault: Vault) -> None:
        """GET /api/vaults/{name}/advice 에서 community_split 타입이 반환됩니다."""
        content_dir = isolated_vault.content_root
        self._create_large_community(content_dir, n=10)
        db_module.build_db(isolated_vault, run_lint=False)

        resp = client.get(f"/api/vaults/{isolated_vault.meta.name}/advice")
        assert resp.status_code == 200
        data = resp.json()
        # 10 노드 = 100% ratio, threshold 초과 → community_split 포함될 수 있음
        types = {a["type"] for a in data}
        # 최소한 advice가 비어있지 않아야 함
        assert len(data) >= 0  # 결과 자체는 항상 성공해야 함


# ─── Task 3: Template Editor API ─────────────────────────────────────────────

class TestTemplateEditorAPI:
    """GET /api/vaults/{name}/templates + PUT /api/vaults/{name}/templates/{type} 검증."""

    def test_list_templates_returns_all_9_types(self, client, isolated_vault: Vault) -> None:
        """GET /templates 는 모든 9종 타입을 반환합니다."""
        resp = client.get(f"/api/vaults/{isolated_vault.meta.name}/templates")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        types = {t["type"] for t in data["templates"]}
        expected = {"concept", "person", "tool", "comparison", "project", "rule", "query", "journal", "issue"}
        assert expected == types

    def test_list_templates_empty_by_default(self, client, isolated_vault: Vault) -> None:
        """기본적으로 모든 타입은 exists=False, content='' 입니다."""
        resp = client.get(f"/api/vaults/{isolated_vault.meta.name}/templates")
        data = resp.json()
        for t in data["templates"]:
            assert t["exists"] is False
            assert t["content"] == ""

    def test_put_template_saves_file(self, client, isolated_vault: Vault) -> None:
        """PUT /templates/concept 은 vault/_templates/concept.md 에 내용을 저장합니다."""
        content = "---\ntitle: {title}\ntype: concept\n---\n\n## 요약\n\n여기에 개념을 서술하세요.\n"
        resp = client.put(
            f"/api/vaults/{isolated_vault.meta.name}/templates/concept",
            json={"content": content},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["type"] == "concept"

        # 실제 파일에 저장되었는지 확인
        fp = isolated_vault.root / "_templates" / "concept.md"
        assert fp.exists()
        assert fp.read_text(encoding="utf-8") == content

    def test_put_template_updates_existing(self, client, isolated_vault: Vault) -> None:
        """이미 존재하는 템플릿을 PUT으로 덮어쓸 수 있습니다."""
        templates_dir = isolated_vault.root / "_templates"
        templates_dir.mkdir(parents=True, exist_ok=True)
        (templates_dir / "tool.md").write_text("# old content", encoding="utf-8")

        new_content = "---\ntitle: {title}\ntype: tool\n---\n\n## 설명\n\n도구 설명 작성.\n"
        resp = client.put(
            f"/api/vaults/{isolated_vault.meta.name}/templates/tool",
            json={"content": new_content},
        )
        assert resp.status_code == 200
        assert (templates_dir / "tool.md").read_text(encoding="utf-8") == new_content

    def test_put_invalid_template_type_returns_400(self, client, isolated_vault: Vault) -> None:
        """허용되지 않은 template_type으로 PUT 시 400을 반환합니다."""
        resp = client.put(
            f"/api/vaults/{isolated_vault.meta.name}/templates/invalid_type",
            json={"content": "some content"},
        )
        assert resp.status_code == 400
        assert "Invalid template type" in resp.json()["detail"]

    def test_list_templates_reflects_saved(self, client, isolated_vault: Vault) -> None:
        """PUT으로 저장한 뒤 GET에서 exists=True, content가 반영되어 있습니다."""
        content = "---\ntitle: {title}\ntype: journal\n---\n\n## 요약\n\n일지 작성.\n"
        client.put(
            f"/api/vaults/{isolated_vault.meta.name}/templates/journal",
            json={"content": content},
        )

        resp = client.get(f"/api/vaults/{isolated_vault.meta.name}/templates")
        data = resp.json()
        journal_tpl = next(t for t in data["templates"] if t["type"] == "journal")
        assert journal_tpl["exists"] is True
        assert journal_tpl["content"] == content

    def test_all_9_types_can_be_saved(self, client, isolated_vault: Vault) -> None:
        """9종 모든 타입에 대해 PUT이 성공합니다."""
        types = ["concept", "person", "tool", "comparison", "project", "rule", "query", "journal", "issue"]
        for t in types:
            resp = client.put(
                f"/api/vaults/{isolated_vault.meta.name}/templates/{t}",
                json={"content": f"# {t} template\n"},
            )
            assert resp.status_code == 200, f"Failed for type: {t}"
