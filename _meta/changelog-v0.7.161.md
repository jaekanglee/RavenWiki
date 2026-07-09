---
title: Changelog v0.7.161
created: 2026-07-10
updated: 2026-07-10
type: rule
tags: [api, database, dashboard, frontend, mcp, test]
---

# v0.7.161 — Phase 8: 다각도 시각화 레이아웃 모드 도입, 동적 속성 확장 및 자율 치유 연동

## BLUF
그래프 시각화의 활용성을 극대화하기 위해 3종의 대체 레이아웃(동심원, 도메인, 타임라인)을 프론트엔드에 추가하고, 지식 분석의 질을 높이기 위해 `layer`(지식 깊이)와 `freshness`(신선도) 동적 속성을 DB 스키마 및 캐싱 파이프라인에 이식했습니다. 또한 외부 에이전트의 정원 가꾸기 보조를 위해 `wiki_get_advice` MCP 툴을 신설하고 자율 치유 행동 절차를 정착시켰습니다.

## 무엇을 했는가

| 변경 | 파일 | 효과 |
|---|---|---|
| 시각화 레이아웃 모드 도입 | `dashboard/src/components/GraphCanvas.tsx`<br>`dashboard/src/routes/GraphPage.tsx`<br>`dashboard/src/components/FullscreenGraphModal.tsx` | Force-directed 외 Concentric(동심원), Domain(커뮤니티 구획 렌더링), Timeline(작성일 x축/타입 y축 정렬 및 그리드) 3대 뷰 모드와 관련 툴바, 줌 수준 보존 연동 구현 |
| 동적 속성 확장 및 DB 갱신 | `raven/core/analytics.py`<br>`raven/core/db.py`<br>`scripts/build_db.py` | `pages` 테이블에 `layer`(평균 논리적 깊이) 및 `freshness`(반감기 180일 노후화 공식) 컬럼 추가, DB 스키마 drift 가드에 반영 및 분석 엔진 2-pass 캐싱 연동 완비 |
| API 및 타입 확장 | `raven/api/server.py`<br>`dashboard/src/types.ts` | `/api/vaults/{name}/graph` 노드 정보에 `layer`, `freshness`, `created`, `updated` 추가 바인딩 및 프론트엔드 타입 정합성 확보 |
| AI 조언 재사용 모듈화 및 MCP 툴 신설 | `raven/core/advice.py`<br>`raven/mcp/cli.py` | API와 MCP 양 레이어에서 활용 가능하도록 네트워크 진단 로직을 `raven/core/advice.py`로 추출 모듈화하고, `wiki_get_advice` MCP 툴을 등록하여 외부 에이전트(헤르메스 등) 연동 지원 |
| 자율 치유 워크플로우 추가 | `raven/core/templates/agent/PROJECT-WORKFLOW.md` | 에이전트용 볼트 진입 가이드에 고립 노드 발견 시 `wiki_relation_add`를 사용하는 자율 치유 행동 절차를 명세화하여 워크플로우 정착 |
| 테스트 검증 및 타입 세이프티 | `make typecheck`<br>`make test` | 타입 에러 100% 제거 및 기존 테스트 스위트 748 Passed 완벽 대응 확인 |

## 왜 했는가 (4 저장 신호)
- **재사용 가능성**: `raven/core/advice.py` 로 모듈화된 진단 로직은 향후 CLI, API, MCP 모든 진입점에서 일관된 지식 네트워크 헬스 진단을 수행할 수 있게 보장합니다.
- **인수인계**: 새로운 시각화 뷰어와 동적 깊이/신선도 산출을 통해 볼트 구조의 이해도를 높이며, 자율 치유 워크플로우를 템플릿에 직접 명세하여 다른 에이전트들이 이를 즉시 지침으로 삼게 했습니다.
- **실패/리스크 기록**: TypeScript 컴파일 단계에서의 엄밀한 검사를 통과시켜 런타임 타입 캐스트 위험 요소를 사전 예방했습니다.
- **맥락 추적**: 문서의 작성 시기별 타임라인 흐름과 도메인별 응집도를 시각적으로 추적 가능하게 하여 지식 정원의 현황 파악 능력을 개선했습니다.
