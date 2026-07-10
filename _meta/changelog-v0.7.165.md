---
title: Changelog v0.7.165
created: 2026-07-10
updated: 2026-07-10
type: rule
tags: [curator, mcp, api, dashboard, test]
---

# v0.7.165 — Phase 13: LLM 기반 자동 태깅 및 모순 강화 탐지 파이프라인 구축

## BLUF
LLM 기반 자동 태깅(Auto-Tagging) 추천 및 연관 문서 간 내용상 논리적 모순 탐지(Contradiction Detection) 기능을 성공적으로 설계 및 구현하고, 이들을 REST API, MCP 도구, 그리고 대시보드 UI/UX에 완전 통합했습니다.

## 무엇을 했는가

| 변경 | 파일 | 효과 |
|---|---|---|
| Auto-Tagging 핵심 모듈 신설 | `raven/core/tagger.py` | 본문 텍스트와 제목을 받아 기존 태그 Taxonomy와 대조 분석하여 최대 5개의 태그를 추천하는 Gemini 프롬프트 및 heuristic fallback 구현 |
| Contradiction 핵심 모듈 신설 | `raven/core/contradiction.py` | 인접 노드(의미 관계) 및 유사도가 높은 문서 쌍의 본문을 추출하여 논리적 불일치(예: 포트 충돌)를 LLM으로 검출하는 모듈 및 heuristic fallback 구현 |
| REST API 엔드포인트 연동 | `raven/api/server.py` | `/api/vaults/{name}/suggest-tags` (POST), `/api/vaults/{name}/lint/contradictions` (GET), `/api/vaults/{name}/lint/contradictions/resolve` (POST) 추가 |
| MCP 도구 등록 | `raven/mcp/cli.py` | `wiki_suggest_tags` 및 `wiki_check_contradictions` 도구를 FastMCP 서버에 정식 등록 |
| 대시보드 API 헬퍼 추가 | `dashboard/src/lib/api.ts` | `suggestTags`, `fetchContradictions`, `resolveContradiction` 연동용 API 바인딩 추가 |
| 대시보드 태그 추천 UI 구현 | `dashboard/src/components/AITagSuggestion.tsx`, `NewPageInline.tsx`, `NewPageButton.tsx`, `InlineMarkdownEditor.tsx` | 페이지 생성 및 수정 화면에 "✨ AI 태그 추천" 단추와 승인(Accept/Accept All) 1-click UX 적용 |
| 대시보드 지식 정원 모순 카드 추가 | `dashboard/src/routes/GardenPage.tsx` | 지식 정원(Gardening) 하단에 모순 카드 섹션을 신설하여 충돌 정보 및 AI 피드백을 표시하고, 관계 업데이트/역참조 추가 승인 단추 제공 |
| 통합 유닛 테스트 구축 | `tests/test_tagger.py`, `tests/test_contradiction.py` | Mock API 호출 및 fallback 검증 유닛 테스트 작성 (pytest 100% 통과) |

## 왜 했는가 (4 저장 신호)
- **재사용 가능성**: 보관소 내에 누적되는 지식 파편 간의 상충 정보를 선제적으로 감지하고, 페이지 생성 시 통일된 태그 Taxonomy를 적용할 수 있게 하여 지식의 유기적 밀도를 높였습니다.
- **인수인계**: 새로운 기능을 표준 REST API와 MCP 도구로 동시 제공하여, 사람이 대시보드에서 작업할 때뿐 아니라 외부 자율 에이전트(헤르메스 등)가 지식 정합성 관리를 자동으로 도울 수 있는 인터페이스를 갖추었습니다.
- **실패/리스크 기록**: LLM 호출이 불가하거나 API key가 미지정된 환경에서도 정상적으로 지식 정원 및 편집기가 기동할 수 있도록 키워드 및 휴리스틱 기반 매칭 기능으로 우아하게 Fallback 하도록 안전망을 확보했습니다.
