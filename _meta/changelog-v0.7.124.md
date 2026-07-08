---
title: Changelog v0.7.124
created: 2026-07-08
updated: 2026-07-08
type: rule
audience: agent
confidence: high
---

# v0.7.124 — 그래프 페이지 필터 useReducer 통합 + persistent 노드 hover 시각 위계 강화

## 무엇을 했는가

### 1. GraphPage 필터 상태 useReducer 통합 (B1)
- **변경 전**: `query` / `selectedType` / `hideOrphans` / `selectedNodeId` 4종이 각각 `useState`로 평면 분산. `resetGraphFilters`는 다중 setState를 수동 동기.
- **변경 후**: `useReducer(filterReducer, initialFilters)`로 묶음. action type 5종 (`setQuery` / `setSelectedType` / `setHideOrphans` / `setSelectedNodeId` / `reset`)으로 의도 명시.
- **부수 효과**:
  - 호출처 12개 (GraphCanvas onNodeClick, TextField onChange, SelectField onChange, hideOrphans toggle, resetGraphFilters 등) setState → dispatch 마이그레이션
  - "이 문서로 포커스" 액션의 `setQuery` + `setSelectedType("all")` 2회 setState → 2회 dispatch (atomic 보장)
  - 향후 undo/redo, 필터 preset 저장 등 확장 시 reducer step만 추가하면 됨
- 인사이트 hover 2종 + loading/loadError/showFullGraph는 데이터 라이프사이클/UI 토글로 빈도 낮아 그대로 useState 유지.

### 2. Persistent 노드 hover scale 차별화 (A1)
- **변경 전**: hover 시 모든 노드 `scale(1.75)`. persistent(현재 문서) 노드도 leave 후 `scale(1.45)`로 복귀 → hover 중에는 persistent 강조와 일반 hover 강조가 동일.
- **변경 후**: persistent + hover → `scale(1.95)`, 일반 hover → `scale(1.75)`. persistent 강조가 hover 중에도 시각 위계 유지.
- 결과: 현재 페이지 노드가 hover 시 더 부풀어 보여 "여기 내가 있다" 신호가 일관되게 살아 있음.

## 변경

| 파일 | 변경 |
|---|---|
| `dashboard/src/routes/GraphPage.tsx` | `useReducer` import 추가, `GraphPageFilters`/`GraphPageFilterAction` type + `filterReducer` + `initialFilters` 정의. 4종 useState → useReducer 통합. 호출처 12개 setState → dispatch 마이그레이션. `resetGraphFilters` 한 줄 dispatch로 단순화. |
| `dashboard/src/components/GraphCanvas.tsx` | `ObsidianNode`의 onMouseEnter에서 persistent 분기 추가 (hover scale 1.75 vs 1.95). |

## 왜 그렇게 했는가 (§5 4 신호)

- **재사용 가능성**: filterReducer는 향후 필터 preset/undo 같은 GraphPage 기능 확장 시 단일 진입점. atomic dispatch 보장.
- **인수인계 필요성**: GraphPage의 setState 11종 → reducer dispatch 5종으로 의도가 명시적. 다음 개발자가 새 필터 추가 시 action type 한 줄로 끝.
- **실패/리스크 기록**: "이 문서로 포커스" 액션의 query + selectedType 동시 변경이 atomic 보장됨. 이전엔 두 번의 setState 사이 렌더링 race 가능.

## 검증

| 항목 | 결과 |
|---|---|
| `make typecheck` | exit 0 |
| `vitest tests/GraphCanvas*` | 18/18 pass |
| `vitest tests/GraphPage*` | 9/9 pass |
| `vitest tests/PageView*` | 31/31 pass |
| 회귀 (Folder-hover-menu, Modal-close-sidebar) | main에서도 같은 2건 실패 — 무관 |

## 후속

- **B2**: derive 함수(`deriveGraphInsights`/`deriveNodeDetail`/`filterGraphView`/`deriveVaultCentroids`)를 `dashboard/src/lib/graph/` 폴더로 분리 → `FullscreenGraphModal`, `FloatingGraphPanel`, 테스트에서 재사용. PageView.local-graph.test.ts의 import 경로 호환 유지.
- **노드 드래그 backend persist**: v0.7.122의 `nodesLayoutChanged` 기반 + `POST /api/vaults/{vault}/graph/positions`.
- **Barnes-Hut quadtree**: force-atlas O(n²) → O(n log n), ADR 작성 후 multi-session.