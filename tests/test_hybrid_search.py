from __future__ import annotations

from pathlib import Path
import pytest
import sqlite3

from raven.core.vault import Vault
from raven.core import db as db_module
from raven.core.hybrid_search import LocalEmbeddingEngine, hybrid_search, load_vector_extension

@pytest.fixture
def isolated_vault(tmp_path: Path, monkeypatch) -> Vault:
    reg_root = tmp_path / "registry"
    monkeypatch.setenv("WIKI_VAULTS_DIR", str(reg_root))
    vault = Vault.create("hybrid-test", tmp_path / "vault", bootstrap=False)
    content_dir = vault.root / "content"
    content_dir.mkdir(parents=True, exist_ok=True)
    return vault


def test_embedding_engine_mock_fallback() -> None:
    """sentence-transformers가 설치되지 않았더라도 mock 임베딩이 768차원 단위 벡터를 반환하는지 검증합니다."""
    engine = LocalEmbeddingEngine()
    emb1 = engine.get_embedding("hello world")
    emb2 = engine.get_embedding("hello world")
    emb3 = engine.get_embedding("different query")
    
    assert len(emb1) == 768
    assert len(emb2) == 768
    assert len(emb3) == 768
    
    # 동일한 입력은 동일한 임베딩 값을 리턴하는지 (deterministic)
    assert emb1 == emb2
    # 다른 입력은 다른 임베딩 값을 리턴하는지 (확률적 다름 검증)
    assert emb1 != emb3
    
    # 정규화된 단위 벡터인지 확인 (오차 범위 내)
    norm = sum(x*x for x in emb1) ** 0.5
    assert abs(norm - 1.0) < 1e-5


def test_hybrid_search_fallback_flow(isolated_vault: Vault) -> None:
    """sqlite-vec가 로드되거나 로드되지 않더라도 hybrid_search API가 정상적으로 Fallback하여 결과를 반환하는지 검증합니다."""
    content_dir = isolated_vault.root / "content"
    
    # 2개 페이지 생성
    (content_dir / "doc-a.md").write_text(
        "---\ntitle: Authentication Guide\ntype: concept\ntags: [auth]\n---\nExplain JWT tokens and cookies\n", encoding="utf-8"
    )
    (content_dir / "doc-b.md").write_text(
        "---\ntitle: Database Setup\ntype: concept\ntags: [db]\n---\nMySQL and PostgreSQL database replication\n", encoding="utf-8"
    )
    
    db_module.build_db(isolated_vault, run_lint=False)
    
    # 1. hybrid_search 함수 호출 검증
    # "JWT"로 검색하면 doc-a.md가 매칭되어야 함
    results = hybrid_search(isolated_vault, "JWT", limit=5)
    
    # sqlite-vec extension 로드 성공 여부에 따라 method가 "hybrid" 또는 "bm25_fallback"이어야 함
    assert len(results) >= 1
    best_hit = results[0]
    assert best_hit["slug"] == "content/doc-a"
    assert "Authentication" in best_hit["title"]
    assert best_hit["method"] in ("hybrid", "bm25_fallback")
    assert "score" in best_hit
    assert "bm25_score" in best_hit
    assert "distance" in best_hit

    # 2. 매칭되지 않는 검색어 테스트 시 빈 목록이 오는지 확인
    no_results = hybrid_search(isolated_vault, "NonExistingSearchTermRandom", limit=5)
    assert len(no_results) == 0
