"""test_search_excludes_autoindex.py — 검색에서 자동 생성 카탈로그 제외 (평가 P1#8).

build가 만드는 content/index.md, content/_index/{type}.md는 vault 내 모든
페이지의 제목·요약을 복제하므로 어떤 검색어든 실제 노트보다 높은 점수로
1위를 차지했음. 카탈로그는 탐색용(tree/graph)이지 검색 대상이 아니다.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from raven.core.vault import Vault
from raven.core import db as db_module


@pytest.fixture
def built_vault(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Vault:
    monkeypatch.setenv("WIKI_VAULTS_DIR", str(tmp_path))
    v = Vault.create("searchv", tmp_path / "searchv")
    (v.root / "content" / "노이즈원칙.md").write_text(
        "---\ntitle: 노이즈원칙\ntype: concept\ntags: [pkm]\n"
        "created: 2026-07-04\nupdated: 2026-07-04\n---\n\n노이즈원칙 본문.\n",
        encoding="utf-8",
    )
    db_module.build_db(v, run_lint=False)  # index.md + _index/* 생성됨
    return v


def test_api_search_excludes_index_pages(built_vault: Vault):
    from fastapi.testclient import TestClient
    from raven.api.server import app

    c = TestClient(app)
    r = c.get("/api/vaults/searchv/search", params={"q": "노이즈원칙"})
    assert r.status_code == 200
    results = r.json()["results"]
    slugs = [x["slug"] for x in results]
    assert "content/노이즈원칙" in slugs
    assert not any(s == "content/index" or s.startswith("content/_index/") for s in slugs), slugs


def test_mcp_fts_search_excludes_index_pages(built_vault: Vault):
    from raven.mcp.db import search_fts

    results = search_fts("노이즈원칙", top_k=10, vault=built_vault.root)
    slugs = [x["slug"] for x in results]
    assert "content/노이즈원칙" in slugs
    assert not any(s == "content/index" or s.startswith("content/_index/") for s in slugs), slugs
