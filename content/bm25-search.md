---
title: BM25 검색 (Okapi BM25)
created: 2026-06-25
updated: 2026-06-25
type: concept
tags: [concept, search, system]
sources: [_meta/system-design.md]
confidence: high
---

# BM25 검색 (Okapi BM25)

## 정의

> [Okapi BM25](https://en.wikipedia.org/wiki/Okapi_BM25) — **용어 빈도(TF)와 역문서 빈도(IDF)** 기반의 랭킹 함수.
> TF-IDF의 후속판. Elasticsearch/Lucene 기본 랭킹 알고리즘.

공식 (간략):
```
score(D, Q) = Σ IDF(qi) · (f(qi, D) · (k1 + 1)) / (f(qi, D) + k1 · (1 - b + b · |D| / avgdl))
```

- `f(qi, D)` = 문서 D에서 용어 qi의 빈도
- `|D|` = 문서 길이
- `avgdl` = 평균 문서 길이
- `k1`, `b` = free parameter (보통 k1=1.5, b=0.75)

## TF-IDF에서 진화한 점

| 차원 | TF-IDF | BM25 |
|---|---|---|
| TF 포화 | 무한 증가 | **포화 곡선** (k1 파라미터) |
| 문서 길이 정규화 | ❌ | ✅ (b 파라미터) |
| 짧은 쿼리 | 약함 | 강함 |
| 현실 corpus | 보통 | **강함** (Elasticsearch 기본) |

**핵심 차이**: BM25는 "이 문서에 용어가 10번 나왔는가"보다 "이 문서가 짧으면서 용어가 있는가"를 더 잘 평가.

## SQLite FTS5 사용

우리 vault = 수백~수천 페이지. **Elasticsearch 오버스펙**.

채택: **SQLite FTS5** (BM25 내장)
- `wiki.db`의 `pages_fts` 가상 테이블 ([[scripts/build_db]] SCHEMA_SQL)
- 표준 SQL 쿼리로 검색 가능
- 추가 서비스 0개

**예시 쿼리**:
```sql
SELECT slug, title, bm25(pages_fts) AS score
FROM pages_fts
WHERE pages_fts MATCH 'MCP OR Tailscale'
ORDER BY score
LIMIT 10;
```

→ BM25 점수가 낮을수록 = 관련도 높음 (SQLite 관례).

## 우리 vault에서의 빌드

[[scripts/build_db.py]]가 `wiki.db` 빌드 시 FTS5 trigger 자동 생성:
```sql
CREATE VIRTUAL TABLE pages_fts USING fts5(slug, title, tags_concat, content);
```

→ 마크다운 추가/수정 → FTS 인덱스 자동 갱신
→ 검색은 즉시 (별도 빌드/워밍업 불필요)

**현재 우리 vault**:
- 페이지 11+개, 증가 중
- 평균 페이지 길이: ~80 라인
- 검색 응답 시간: < 50ms (예상)

## 한계 + vector 비교

| 차원 | BM25 (FTS5) | Vector (sqlite-vec / Qdrant) |
|---|---|---|
| **시맨틱 매칭** | ❌ (키워드 일치만) | ✅ ("자동차" ↔ "vehicle") |
| **다국어** | 영어/한국어 tokenizer 분리 필요 | 자동 (임베딩이 다국어 학습) |
| **인덱스 크기** | 작음 (DB 안에 포함) | 큼 (임베딩 벡터 384~1536 차원) |
| **쿼리 속도** | 매우 빠름 (FTS) | 빠름 (ANN 인덱스) |
| **구축 비용** | $0 | 임베딩 모델 필요 (~$0 로컬 가능) |
| **우리 시스템** | ✅ M1 (지금) | 🟡 M3 (sqlite-vec) |

**결론**: 1차 = BM25로 시작 → 충분한 페이지(100+) 쌓이면 vector hybrid 추가 ([[SCHEMA]] M3 로드맵).

### Hybrid (M3 예정)

```python
def hybrid_search(query: str, top_k: int = 10):
    bm25_hits = bm25_search(query, top_k * 2)         # recall 우선
    vec_hits = vector_search(embed(query), top_k * 2)
    merged = reciprocal_rank_fusion(bm25_hits, vec_hits)
    return merged[:top_k]
```

## 한국어 처리

FTS5의 `unicode61` tokenizer는 공백 기준 분리. 한국어 = 어절 단위.
→ "위키백과" 검색 시 "위키" / "백과" 매칭 (의도적).

고려 옵션:
- **ngram tokenizer** (3-gram): 부분 매칭 강화, 인덱스 3배
- **mecab-ko**: 형태소 분석기 (한국어 정확한 매칭)
- 지금은 기본 unicode61 → 필요 시 [[_meta/ai-roadmap]]에서 결정

## 왜 BM25인가

1. **충분히 좋음**: Elasticsearch/Solr/Algolia 모두 기본
2. **무료 + 무설치**: SQLite FTS5 내장
3. **예측 가능**: 디버깅 쉬움 (점수 설명 가능)
4. **MCP 통합 쉬움**: `wiki_search(query)` 결과에 score 함께 반환

## 한계 / 미결정

- 동의어/의미 매칭 불가 → vector 보완 예정 (M3)
- 한국어 형태소 분석 미적용 → 정확도 한계
- 페이지 10k+ 시 ranking 재정렬 필요 가능성

## 관련

- [[content/llm-wiki]] — LLM Wiki 패턴의 검색 컴포넌트
- [[content/rag-vs-llm-wiki]] — RAG vs LLM Wiki (BM25는 RAG 쪽 기법)
- [[content/sqlite-vs-postgres]] — SQLite 위에서 BM25의 trade-off
- [[_meta/system-design]] — Layer 1 (search.idx)
- [[scripts/build_db]] — FTS5 schema 정의
