---
title: AI 활용 로드맵 (M3-M6)
created: 2026-06-25
updated: 2026-06-25
type: rule
tags: [system, meta, ai, roadmap]
---

# AI 활용 로드맵 (M3-M6)

> **한 줄 요약**: 검색 → 추천 → Q&A → 자동 태깅 → 모순 탐지 → 작성 도우미 — 단계적 AI 기능 확장

---

## 단계별 로드맵

| 단계 | 기능 | 시점 |
|---|---|---|
| M1 | 인덱싱 자동화 (curator) | ✅ M1 완료 |
| M2 | MCP server (외부 AI 접근, read-only 기본) | M2 |
| M3 | Vector Search (`sqlite-vec` 1차) + 관련 문서 추천 | M3 |
| M4 | 문서 Q&A (RAG over vault) | M4 |
| M5 | 자동 태깅 + 모순 강화 탐지 (LLM-driven) | M5 |
| M6 | 작성 도우미 (초안 생성) | M6 |
| ❌ | AI 채팅 (실시간 대화) | OUT |

---

## M3: Vector Search (sqlite-vec 1차)

| 후보 | 결정 |
|---|---|
| `sqlite-vec` | ✅ M3 기본 (FTS5와 hybrid) |
| Qdrant | M4+ 이관 검토 (10k+ 페이지 시) |
| pgvector | ❌ (Postgres 자체호스팅 과함) |
| Chroma | ❌ (별도 프로세스, 운영 부담) |

**전략**:
- 같은 `wiki.db`에 `vec0` 가상 테이블 추가 (sqlite-vec extension)
- 임베딩 모델: `sentence-transformers` (로컬) — 한국어 모델 조사 필요 (예: `ko-sroberta`, `bge-m3-ko`)
- FTS5 BM25 + vector cosine = **hybrid search** (가중치 평균: BM25 0.6 + vector 0.4)

```sql
-- vec0 가상 테이블
CREATE VIRTUAL TABLE page_vec USING vec0(
  slug TEXT PRIMARY KEY,
  embedding FLOAT[768]  -- bge-m3-ko 차원
);

-- hybrid query
WITH bm25_hits AS (
  SELECT slug, bm25(pages_fts) AS score FROM pages_fts WHERE pages_fts MATCH ? ORDER BY score LIMIT 20
),
vec_hits AS (
  SELECT slug, distance AS dist FROM page_vec WHERE embedding MATCH ? ORDER BY dist LIMIT 20
)
SELECT b.slug, b.score * 0.6 + v.dist * 0.4 AS hybrid
FROM bm25_hits b JOIN vec_hits v ON b.slug = v.slug
ORDER BY hybrid DESC LIMIT 10;
```

> **M3 이전**: BM25 단독 (충분). M3에서 vec 추가하여 hybrid.

**기존 BM25 검색**: [[content/bm25-search]]

---

## M3: 관련 문서 추천

```sql
-- co-citation: "X를 참조하는 다른 페이지들이 함께 참조하는 페이지"
SELECT target_slug, COUNT(*) AS shared_inbound
FROM links
WHERE source_slug IN (
  SELECT source_slug FROM links WHERE target_slug = ?
)
GROUP BY target_slug
ORDER BY shared_inbound DESC LIMIT 5;

-- tag overlap: "비슷한 태그 가진 페이지"
SELECT p.slug, p.title, COUNT(t.tag) AS overlap
FROM pages p
JOIN tags t ON t.page_slug = p.slug
WHERE t.tag IN (SELECT tag FROM tags WHERE page_slug = ?)
GROUP BY p.slug
ORDER BY overlap DESC LIMIT 5;
```

**전략**:
- Dashboard에서 페이지 하단에 "관련 문서" 섹션 표시
- 둘 중 score 높은 5개 표시
- vector search 결과와도 cross-reference

---

## M4: 문서 Q&A (RAG)

```
[사용자] "JWT 패턴 어떻게 설명되어 있어?"
   ↓
[wiki-mcp] wiki_search("JWT") → top 5
   ↓
[wiki-mcp] wiki_get_page(slug) × 5 → context 5000자
   ↓
[LLM: 헤르메스/M2.7] context + question → 답변 (출처 인용)
   ↓
[사용자] 답변 + 출처 페이지 5개 링크
```

**핵심**: 출처 인용 **필수** / 답변은 "종합"이 아닌 "원문 인용 + 약간의 연결" / context 크기 엄격 제한 (hallucination 방지)

---

## M5: 자동 태깅 + 모순 강화 탐지

**자동 태깅**: 신규 페이지 작성 시 LLM이 tag 추천 (top 5) → 사용자 승인 필수 (1-click accept/reject) / 시스템 태그는 자동 부여 ❌

**모순 강화 탐지**: 현재 lint는 `contested=true` frontmatter만 / M5에서 LLM이 두 페이지 비교 → "이거 모순 아니야?" 자동 propose → 사용자 confirmed → 양쪽 페이지에 역참조 추가

---

## M6: 작성 도우미

```
[사용자] "JWT 패턴에 대해 써줘"
   ↓
[wiki-mcp] wiki_update_draft(topic, structure, related_pages)
   ↓
[LLM] 초안 생성 → frontmatter + 본문 + outbound links
   ↓
[사용자] 편집 → commit
```

**제약**: 초안은 `drafts/`에만 생성 (lint 면제) / 사용자가 명시적으로 commit해야 content/로 이동 / LLM이 임의로 기존 페이지 수정 ❌

---

## OUT: AI 채팅

**의도적 제외**:
- 실시간 대화 인터페이스는 만들지 않음
- MCP tools (read-only)로 충분
- 채팅 UI = lock-in 위험, "내 입맛" 자유도 ↓

**대안**:
- Claude iOS 앱에서 내 MCP server 연결 → 동일 경험
- 헤르메스(wiki-orchestrator)에서 직접 검색/Q&A 호출

---

## AI 활용 원칙

1. **사용자가 항상 컨텍스트** — AI는 검색/추천만, 결론은 사용자
2. **근거 추적** — AI 인용 페이지 무조건 표시 (Q&A, 추천)
3. **오버라이드 쉬움** — AI 제안 무시 1-click (태깅, 모순)
4. **Privacy** — vault 내용 외부 API 전송 ❌ (로컬 LLM 옵션 검토)
5. **비용** — 임베딩/LLM 호출 모두 로컬/구독 모델 우선 (외부 API $$$)

---

## 모델 배분

| 단계 | 모델 | 이유 |
|---|---|---|
| M3 임베딩 | sentence-transformers (로컬) | 한국어 + 무료 |
| M4 Q&A | 헤르메스(M2.7 또는 M3) | 헤르메스 인프라 재사용 |
| M5 자동 태깅 | 헤르메스 (light) | 단순 분류 |
| M5 모순 탐지 | 헤르메스 (heavy, M3) | reasoning 필요 |
| M6 작성 도우미 | 헤르메스 (heavy) | 초안 품질 |

> **위임**: [[content/hermes-agent]] — 헤르메스 에이전트 자체

---

## 비용 (월)

| 항목 | 비용 |
|---|---|
| 임베딩 (sentence-transformers 로컬) | $0 |
| LLM (헤르메스 구독 모델) | $0 (기존) |
| 외부 API | ❌ 사용 안 함 |
| **합계** | **$0** |

---

## 관련

- [[SCHEMA]] — vault 규약
- [[RULES]] — 운영 정책
- [[_meta/architecture-5layer]] — 5-Layer (Layer 2: MCP)
- [[content/mcp-server]] — MCP server 개념
- [[content/bm25-search]] — BM25 검색 (M3 이전)
- [[content/ssg-vs-spa]] — Dashboard 선택
- [[content/hermes-agent]] — 헤르메스 에이전트
