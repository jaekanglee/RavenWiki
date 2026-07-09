"""raven.core.hybrid_search — FTS5 BM25 검색과 임베딩 벡터 검색을 결합한 하이브리드 검색 파이프라인."""
from __future__ import annotations

import struct
import sqlite3
import hashlib
from typing import Any, List, Dict, Optional
from pathlib import Path

from .vault import Vault
from . import db as db_module

class LocalEmbeddingEngine:
    """로컬 한국어 임베딩 추출 엔진 (ko-sroberta 또는 bge-m3-ko).
    sentence-transformers 라이브러리가 없는 경우 결정론적 Mock 임베딩으로 Fallback합니다.
    """
    def __init__(self, model_name: str = "jhgan/ko-sroberta-multitask"):
        self.model_name = model_name
        self.model = None
        self.initialized = False
        
    def _lazy_init(self) -> None:
        if self.initialized:
            return
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(self.model_name)
        except ImportError:
            import sys
            sys.stderr.write(
                f"⚠️  [LocalEmbeddingEngine] 'sentence-transformers' package not found.\n"
                f"Please run 'pip install sentence-transformers' to enable real vector search.\n"
                f"Using deterministic mock embeddings (768-dim) fallback.\n"
            )
        self.initialized = True
            
    def get_embedding(self, text: str) -> list[float]:
        self._lazy_init()
        if self.model:
            emb = self.model.encode(text)
            return emb.tolist()
        else:
            # Deterministic mock 768-dimension unit vector based on sha256 hash of the input text
            h = hashlib.sha256(text.encode("utf-8")).digest()
            mock_emb = []
            for i in range(768):
                val = ((h[i % len(h)] + i) % 256) / 256.0 - 0.5
                mock_emb.append(val)
            # Normalize to unit vector
            norm = sum(x*x for x in mock_emb) ** 0.5
            return [x / norm for x in mock_emb] if norm > 0.0 else mock_emb


def load_vector_extension(conn: sqlite3.Connection) -> bool:
    """sqlite-vec 확장을 데이터베이스 커넥션에 로드합니다."""
    try:
        conn.enable_load_extension(True)
        # 1. sqlite_vec 패키지가 설치되어 있으면 해당 패키지를 통해 load 시도
        try:
            import sqlite_vec
            sqlite_vec.load(conn)
            return True
        except ImportError:
            pass
            
        # 2. 시스템 native extension 로드 시도
        conn.load_extension("sqlite-vec")
        return True
    except Exception as e:
        import sys
        sys.stderr.write(f"⚠️  [load_vector_extension] Failed to load sqlite-vec: {e}\n")
        return False


def init_vector_db(conn: sqlite3.Connection) -> None:
    """sqlite-vec용 가상 테이블을 생성합니다. (768차원 bge-m3-ko/ko-sroberta 규격)"""
    if not load_vector_extension(conn):
        return
        
    conn.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS page_vec USING vec0(
            slug TEXT PRIMARY KEY,
            embedding FLOAT[768]
        );
    """)
    conn.commit()


def _backfill_embeddings(conn: sqlite3.Connection, vault: Vault) -> None:
    """기존 db의 모든 페이지를 인덱싱하여 page_vec 테이블에 임베딩을 채웁니다."""
    try:
        pages = conn.execute("SELECT slug, title, raw_content FROM pages").fetchall()
        if not pages:
            return
            
        engine = LocalEmbeddingEngine()
        for p in pages:
            slug = p["slug"]
            text_to_embed = f"{p['title']} {p['raw_content']}"
            vector = engine.get_embedding(text_to_embed)
            vector_bytes = struct.pack(f"{len(vector)}f", *vector)
            
            conn.execute(
                "INSERT OR REPLACE INTO page_vec (slug, embedding) VALUES (?, ?)",
                (slug, vector_bytes)
            )
        conn.commit()
    except Exception as e:
        import sys
        sys.stderr.write(f"⚠️  [_backfill_embeddings] Failed: {e}\n")


def hybrid_search(vault: Vault, query_text: str, limit: int = 10) -> list[dict[str, Any]]:
    """BM25 가중치(0.6)와 벡터 유사도 가중치(0.4)를 결합하는 하이브리드 검색을 수행합니다.
    확장 모듈 부재 시 FTS5 BM25 단독 검색 결과로 Fallback합니다.
    """
    if not vault.db_path.exists():
        return []
        
    conn = sqlite3.connect(vault.db_path)
    conn.row_factory = sqlite3.Row
    
    # 1. sqlite-vec 로드
    has_vec = load_vector_extension(conn)
    
    # 2. 테이블 존재 여부 확인 및 생성/백필
    if has_vec:
        try:
            conn.execute("SELECT 1 FROM page_vec LIMIT 1")
        except sqlite3.OperationalError:
            # 테이블이 없으면 생성 및 백필
            init_vector_db(conn)
            _backfill_embeddings(conn, vault)
            
    # 3. 확장 로드 실패 시 BM25 단독 검색 Fallback
    if not has_vec:
        try:
            cur = conn.execute("""
                SELECT p.slug, p.title, p.type, bm25(pf.pages_fts) AS bm25_score
                FROM pages_fts pf
                JOIN pages p ON p.slug = pf.slug
                WHERE pf.pages_fts MATCH ?
                ORDER BY bm25_score ASC
                LIMIT ?
            """, (query_text, limit))
            rows = cur.fetchall()
            conn.close()
            
            return [
                {
                    "slug": r["slug"],
                    "title": r["title"],
                    "type": r["type"],
                    "score": float(r["bm25_score"]),
                    "bm25_score": float(r["bm25_score"]),
                    "distance": 1.0,
                    "method": "bm25_fallback"
                }
                for r in rows
            ]
        except Exception as e:
            import sys
            sys.stderr.write(f"⚠️  Fallback BM25 search failed: {e}\n")
            conn.close()
            return []

    # 4. 하이브리드 검색 수행
    try:
        engine = LocalEmbeddingEngine()
        query_vector = engine.get_embedding(query_text)
        query_vector_bytes = struct.pack(f"{len(query_vector)}f", *query_vector)
        
        # BM25 가중치(0.6)와 벡터 유사도 가중치(0.4) 결합 가상 쿼리 실행
        # JOIN 결과가 존재하지 않을 때를 대비해 LEFT JOIN으로 합집합 결합 후 가중치 적용
        query_sql = """
        WITH bm25_hits AS (
          SELECT pf.slug, bm25(pf.pages_fts) AS bm25_score
          FROM pages_fts pf
          WHERE pf.pages_fts MATCH ?
          LIMIT 50
        ),
        vec_hits AS (
          SELECT slug, vec_distance_l2(embedding, ?) AS dist
          FROM page_vec
          LIMIT 50
        )
        SELECT 
            p.slug, 
            p.title, 
            p.type,
            COALESCE(b.bm25_score, 0.0) AS bm25_score,
            COALESCE(v.dist, 1.0) AS dist,
            (COALESCE(b.bm25_score, 0.0) * 0.6) + (COALESCE(v.dist, 1.0) * 0.4) AS hybrid_score
        FROM pages p
        LEFT JOIN bm25_hits b ON p.slug = b.slug
        LEFT JOIN vec_hits v ON p.slug = v.slug
        WHERE b.slug IS NOT NULL OR v.slug IS NOT NULL
        ORDER BY hybrid_score ASC
        LIMIT ?
        """
        
        cur = conn.execute(query_sql, (query_text, query_vector_bytes, limit))
        rows = cur.fetchall()
        
        results = []
        for r in rows:
            results.append({
                "slug": r["slug"],
                "title": r["title"],
                "type": r["type"],
                "score": float(r["hybrid_score"]),
                "bm25_score": float(r["bm25_score"]),
                "distance": float(r["dist"]),
                "method": "hybrid"
            })
            
        conn.close()
        return results
    except Exception as e:
        import sys
        sys.stderr.write(f"⚠️  Hybrid search query failed, falling back: {e}\n")
        try:
            conn.close()
        except:
            pass
        return []
