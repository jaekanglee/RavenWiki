---
title: Changelog v0.7.156
created: 2026-07-09
updated: 2026-07-09
type: rule
tags: [mcp, database, dashboard, frontend, test]
---

# v0.7.156 — Phase 3: MCP Relations API Addition & Dashboard UI Integration

## BLUF
Phase 1(DB/Schema)과 Phase 2(마이그레이션 및 Lint)를 토대로, 에이전트가 frontmatter를 직접 수정하지 않고 의미 관계를 제어할 수 있도록 MCP 도구(`wiki_relation_add`, `wiki_relation_remove`, `wiki_relations_list`)를 추가하고, 대시보드 UI(`PageView`)에 5대 핵심 의미 관계 카테고리별 relations 렌더링 및 호버 툴팁 기능을 연동하였으며, 관련 유닛 테스트를 구현하여 전체 회귀가 발생하지 않음을 검증했습니다.

## 무엇을 했는가

| 변경 | 파일 | 효과 |
|---|---|---|
| MCP Relations 도구 구현 | `raven/mcp/tools/write.py`, `raven/mcp/tools/read.py` | frontmatter 및 DB relations 테이블과 동기화하여 관계를 안전하게 추가/삭제/조회하는 `wiki_relation_add`, `wiki_relation_remove`, `wiki_relations_list` 구현 |
| MCP 도구 허가 권한 및 CLI 등록 | `raven/mcp/tools/__init__.py`, `raven/mcp/cli.py` | 추가된 도구들을 `WRITE_TOOLS` whitelist 및 FastMCP 서버 데몬에 정식 등록 |
| 대시보드 문서 상세 페이지 연동 | `dashboard/src/routes/PageView.tsx`, `dashboard/src/types.ts` | 5대 핵심 의미 관계 카테고리별로 정렬하여 클릭 가능한 링크 형태로 Relations를 렌더링하고, 호버 시 `evidence`와 `reason`을 툴팁으로 시각화하는 UI 추가 |
| 유닛 테스트 추가 및 회귀 검증 | `tests/test_mcp_relations.py` | 추가된 MCP 관계 도구들의 유닛 테스트 구현 및 `make test` 전체 회귀 테스트 통과 |

## 왜 했는가 (4 저장 신호)

- **재사용 가능성**: 단순 텍스트로 보존되던 relation을 MCP API를 통해 에이전트 및 외부 시스템이 정규화된 데이터로 제어하고 조회할 수 있는 표준 인터페이스를 제공함.
- **인수인계**: frontmatter의 relations 필드를 대시보드 상세 보기 화면에서 직관적으로 렌더링함으로써, 사람 운영자 및 AI 에이전트가 문서 간의 맥락과 의존성을 신속하게 파악할 수 있도록 도모함.
- **scope/provenance 추적 필요성**: 관계 맺음의 신뢰성을 위해 필수 기재되어야 하는 `evidence`와 `reason`을 툴팁 형태로 대시보드에 노출하여 지식 연결의 투명성을 극대화함.

## 검증

- **유닛 테스트 검증**: `python3 -m pytest tests/test_mcp_relations.py` (Passed) ✅
- **회귀 테스트 검증**: `make test` 실행 → 742 passed, 1 skipped, 1 warning (35.58s) ✅
- **정적 타입 및 빌드 검증**: `npx tsc` 및 `npm run build` 정적 번들 검증.
