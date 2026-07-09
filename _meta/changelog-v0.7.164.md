---
title: Changelog v0.7.164
created: 2026-07-10
updated: 2026-07-10
type: rule
tags: [curator, mcp, api, dashboard, test]
---

# v0.7.164 — Phase 12: Hybrid Search API 및 RAG (Retrieval-Augmented Generation) 핵심 파이프라인 연동

## BLUF
FTS5와 임베딩 벡터가 결합된 하이브리드 검색 기능을 대시보드 및 외부 에이전트와 완벽히 통합했습니다. REST API와 MCP에 하이브리드 검색 및 AI Q&A(RAG) 전용 엔드포인트/도구를 신설하고, 대시보드의 기존 검색 화면을 지식 기반 AI 답변 및 출처 인용 연동 기능을 포함하는 차세대 탐색 창으로 고도화했습니다.

## 무엇을 했는가

| 변경 | 파일 | 효과 |
|---|---|---|
| Hybrid Search REST API 연동 | `raven/api/server.py` | `/api/vaults/{name}/hybrid-search` GET 엔드포인트를 노출하여 질의문(query)과 한계(limit)를 기반으로 하이브리드 매칭 리스트 반환 지원 |
| Hybrid Search MCP 도구 등록 | `raven/mcp/cli.py` | `wiki_hybrid_search` 도구를 등록하여 외부 에이전트(헤르메스 등)가 하이브리드 검색을 호출할 수 있도록 지원 |
| RAG (Retrieval-Augmented Generation) 핵심 모듈 신설 | `raven/core/rag.py` | 관련 문서를 최대 5개 추출하여 컨텍스트를 구성하고, Gemini API (또는 Fallback 가이드)를 통해 출처 파일 링크 인용이 포함된 답변을 도출하는 뼈대 구현 |
| RAG REST API 및 MCP 도구 연동 | `raven/api/server.py`, `raven/mcp/cli.py` | `/api/vaults/{name}/rag/query` GET 엔드포인트 및 `wiki_rag_query` MCP 도구를 노출하여 통합 지식 Q&A 제공 |
| RAG 및 Hybrid Search 유닛 테스트 구축 | `tests/test_rag.py`, `tests/test_hybrid_search.py` | RAG API 호출, Fallback 답변 생성, MCP 도구 등록 여부를 검증하는 테스트 시나리오 작성 및 통과 확인 |
| 대시보드 API 헬퍼 추가 | `dashboard/src/lib/api.ts` | `fetchHybridSearch` 및 `fetchRAGQuery` 함수를 추가하여 대시보드 클라이언트와 서버 연동 최적화 |
| 대시보드 Search UI / UX 고도화 | `dashboard/src/routes/SearchPage.tsx`, `dashboard/src/components/SearchResultItem.tsx` | 기존 검색 페이지를 하이브리드 검색 결과를 표시하도록 전환하고, 상단에 '🤖 AI 지식 탐색 답변 (RAG)' 카드 및 clickable citation 링크 연동 |

## 왜 했는가 (4 저장 신호)
- **재사용 가능성**: 하이브리드 지식 검색과 출처가 보장되는 로컬 RAG 파이프라인을 구축하여 향후 멀티 에이전트 및 인간 사용자가 볼트 전체에 흩어진 파편화된 지식을 질의 한 번으로 통합 요약해 활용할 수 있도록 했습니다.
- **인수인계**: 새로운 RAG 및 Hybrid Search API를 MCP 도구로 등록하여 외부 자율 에이전트가 지식 임베딩을 정밀 탐색하고 문맥에 맞게 활용할 수 있도록 인터페이스를 제공했습니다.
- **실패/리스크 기록**: LLM API key가 제공되지 않거나 호출 실패 시에도 하이브리드 매칭 상위 문서 추천 목록으로 우아하게 Fallback 하도록 구성해 서비스 신뢰성을 확보했습니다.
