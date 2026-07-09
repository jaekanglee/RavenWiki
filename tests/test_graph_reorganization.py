"""v0.7.147+: 단일 보관소 그래프 폴더 HUD 및 메타데이터 정보 보완 테스트."""

import os
import shutil
import tempfile
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from raven.api.server import app
from raven.core.graph import folder_group_for_slug

@pytest.fixture
def isolated_env(monkeypatch):
    """Redirect WIKI_VAULTS_DIR + provide a clean target dir."""
    reg_root = Path(tempfile.mkdtemp(prefix="raven-api-reg-"))
    target_root = Path(tempfile.mkdtemp(prefix="raven-api-target-"))
    monkeypatch.setenv("WIKI_VAULTS_DIR", str(reg_root))
    yield {"reg_root": reg_root, "target_root": target_root}
    shutil.rmtree(reg_root, ignore_errors=True)
    shutil.rmtree(target_root, ignore_errors=True)


@pytest.fixture
def client():
    return TestClient(app)


def test_folder_group_for_slug_mapping():
    # 4대 대분류 매핑 테스트
    assert folder_group_for_slug("_meta/agents/SCHEMA") == ("_meta", "시스템 및 설정 (_meta)")
    assert folder_group_for_slug("content/concept/purpose") == ("content", "본문 지식 (content)")
    assert folder_group_for_slug("raw/articles/karpathy") == ("raw", "참조 자료 (raw)")
    assert folder_group_for_slug("log") == ("root", "루트 폴더 (root)")
    assert folder_group_for_slug("") == ("root", "루트 폴더 (root)")
    
    # fallback 대분류 테스트
    assert folder_group_for_slug("custom/docs/info") == ("custom", "custom")


def test_api_vault_graph_metadata_contract_wiki_db(client, isolated_env):
    """wiki.db가 존재하는 canonical 경로에서 nodes에 folder_group/folder_label이 포함되는지 검증."""
    target = isolated_env["target_root"] / "gv_meta_db"
    client.post("/api/vaults", json={"name": "gv_meta_db", "path": str(target), "bootstrap": False})
    
    client.post("/api/vaults/gv_meta_db/pages", json={"slug": "content/concept/purpose", "title": "Purpose"})
    client.post("/api/vaults/gv_meta_db/pages", json={"slug": "content/rule/governance", "title": "Governance"})

    resp = client.get("/api/vaults/gv_meta_db/graph")
    assert resp.status_code == 200
    
    nodes = resp.json()["nodes"]
    assert len(nodes) >= 2
    
    nodes_map = {n["id"]: n for n in nodes}
    
    assert nodes_map["content/concept/purpose"]["folder_group"] == "content"
    assert nodes_map["content/concept/purpose"]["folder_label"] == "본문 지식 (content)"
    
    assert nodes_map["content/rule/governance"]["folder_group"] == "content"
    assert nodes_map["content/rule/governance"]["folder_label"] == "본문 지식 (content)"


def test_api_vault_graph_metadata_contract_rglob_fallback(client, isolated_env):
    """wiki.db가 강제 제거된 fallback 경로에서도 nodes에 folder_group/folder_label이 정상 반환되는지 검증."""
    target = isolated_env["target_root"] / "gv_meta_fallback"
    client.post("/api/vaults", json={"name": "gv_meta_fallback", "path": str(target), "bootstrap": False})
    
    client.post("/api/vaults/gv_meta_fallback/pages", json={"slug": "content/concept/purpose", "title": "Purpose"})
    client.post("/api/vaults/gv_meta_fallback/pages", json={"slug": "content/rule/governance", "title": "Governance"})

    # wiki.db 강제 삭제하여 fallback 분기로 유도
    db_path = target / "wiki.db"
    if db_path.exists():
        os.remove(str(db_path))

    resp = client.get("/api/vaults/gv_meta_fallback/graph")
    assert resp.status_code == 200
    
    nodes = resp.json()["nodes"]
    assert len(nodes) >= 2
    
    nodes_map = {n["id"]: n for n in nodes}
    
    assert nodes_map["content/concept/purpose"]["folder_group"] == "content"
    assert nodes_map["content/concept/purpose"]["folder_label"] == "본문 지식 (content)"
    
    assert nodes_map["content/rule/governance"]["folder_group"] == "content"
    assert nodes_map["content/rule/governance"]["folder_label"] == "본문 지식 (content)"


def test_api_vault_graph_broken_dependency_and_weights(client, isolated_env):
    """depends_on 관계가 rejected issue나 archived 문서로 향할 때 broken_dependency가 True로 지정되는지 검증."""
    target = isolated_env["target_root"] / "gv_broken_dep"
    client.post("/api/vaults", json={"name": "gv_broken_dep", "path": str(target), "bootstrap": False})
    
    content_dir = target / "content"
    content_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. doc-a depends_on doc-b (doc-b is issue status rejected)
    (content_dir / "doc-a.md").write_text(
        """---
title: Doc A
type: concept
relations:
  - type: depends_on
    target: doc-b
    evidence: ["code"]
    reason: Depends on doc-b.
---
""", encoding="utf-8"
    )
    (content_dir / "doc-b.md").write_text(
        """---
title: Doc B
type: issue
issue_status: rejected
---
""", encoding="utf-8"
    )

    # 2. doc-c depends_on doc-d (doc-d is archived)
    (content_dir / "doc-c.md").write_text(
        """---
title: Doc C
type: concept
relations:
  - type: depends_on
    target: doc-d
    evidence: ["code"]
    reason: Depends on doc-d.
---
""", encoding="utf-8"
    )
    (content_dir / "doc-d.md").write_text(
        """---
title: Doc D
type: concept
status: archived
---
""", encoding="utf-8"
    )

    # 3. doc-e uses doc-f (normal dependency - not depends_on, so not broken)
    (content_dir / "doc-e.md").write_text(
        """---
title: Doc E
type: concept
relations:
  - type: uses
    target: doc-f
    evidence: ["code"]
    reason: Uses doc-f.
---
""", encoding="utf-8"
    )
    (content_dir / "doc-f.md").write_text(
        """---
title: Doc F
type: concept
status: archived
---
""", encoding="utf-8"
    )

    # Build index to generate wiki.db
    build_resp = client.post("/api/vaults/gv_broken_dep/build")
    assert build_resp.status_code == 200

    resp = client.get("/api/vaults/gv_broken_dep/graph")
    assert resp.status_code == 200
    
    data = resp.json()
    nodes = data["nodes"]
    edges = data["edges"]
    
    nodes_map = {n["id"]: n for n in nodes}
    
    # doc-a와 doc-c는 broken_dependency가 True여야 함 (의존 주체)
    assert nodes_map["content/doc-a"]["broken_dependency"] is True
    assert nodes_map["content/doc-c"]["broken_dependency"] is True
    
    # doc-e는 depends_on이 아니므로 broken_dependency가 False여야 함
    assert nodes_map["content/doc-e"]["broken_dependency"] is False
    
    # 엣지 검증
    edges_map = {(e["source"], e["target"]): e for e in edges}
    
    # doc-a -> doc-b (depends_on to rejected issue) -> broken
    assert edges_map[("content/doc-a", "content/doc-b")]["broken_dependency"] is True
    
    # doc-c -> doc-d (depends_on to archived) -> broken
    assert edges_map[("content/doc-c", "content/doc-d")]["broken_dependency"] is True
    
    # doc-e -> doc-f (uses to archived) -> not broken (not depends_on)
    assert edges_map[("content/doc-e", "content/doc-f")]["broken_dependency"] is False

