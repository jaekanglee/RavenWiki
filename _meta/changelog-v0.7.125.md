---
title: Changelog v0.7.125
created: 2026-07-08
updated: 2026-07-08
type: rule
audience: agent
confidence: high
---

# v0.7.125 — 그래프 derive/filter 함수 lib 분리

## 무엇을 했는가

GraphPage.tsx에 inline되어 있던 5개 derive/filter 순수 함수 + 4개 type + 2개 helper를 `dashboard/src/lib/graph/derive.ts`로 분리했다.

### 분리된 함수
- `deriveVaultCentroids` — vault별 centroid + halo 반경 계산
- `deriveGraphInsights` — topConnected/topOrphans/typeBreakdown 계산
- `deriveNodeDetail` — 선택 노드의 inbound/outbound/neighbors 도출
- `deriveCommunityOptions` — community relation-group 필터 옵션
- `filterGraphView` — hideOrphans/query/selectedType/selectedCommunity 기반 visible 노드/엣지 추출

### 분리된 타입
- `GraphInsight`, `GraphNodeDetail`, `GraphFilterState`, `CommunityOption`

### 분리된 헬퍼
- `normalizeGraphText`, `matchesGraphQuery`

### GraphPage.tsx 변경
- 위 5개 함수를 inline 정의에서 import로 교체
- 외부 호환을 위해 `export ... from "../lib/graph/derive"` re-export 추가
- 결과: GraphPage.tsx 659줄 → ~493줄 (-25%)

## 변경

| 파일 | 변경 |
|---|---|
| `dashboard/src/lib/graph/derive.ts` | **신규** — 5개 derive/filter 순수 함수 + 4개 type + 2개 helper. React/xyflow/DOM 미의존. |
| `dashboard/src/routes/GraphPage.tsx` | 5개 함수 inline 정의 제거 + import. `export ... from` re-export로 외부 import 경로 보존. `GraphFilterState`/`GraphInsight`/`GraphNodeDetail` local interface 제거(lib 타입 사용). |

## 왜 그렇게 했는가 (§5 4 신호)

- **재사용 가능성**: FullscreenGraphModal, FloatingGraphPanel 등 다른 그래프 뷰에서 같은 derive 로직 사용 가능. PageView.local-graph.test.ts의 import 경로는 re-export로 보존.
- **인수인계 필요성**: GraphPage(React 컴포넌트)와 derive 로직(순수 함수)의 책임 분리. 다음 개발자가 derive 함수만 따로 단위 테스트 가능.
- **scope/provenance 추적**: lib/graph/가 그래프 데이터 처리 SOT. GraphPage는 UI/orchestration만 담당.

## 검증

| 항목 | 결과 |
|---|---|
| `make typecheck` | exit 0 |
| `vitest tests/GraphCanvas*` | 18/18 pass |
| `vitest tests/GraphPage*` | 9/9 pass |
| `vitest tests/PageView*` | 31/31 pass |

## 후속

- **FullscreenGraphModal / FloatingGraphPanel**에서 `deriveNodeDetail`, `deriveGraphInsights` 직접 import 가능 (현재는 GraphPage 결과 prop drilling)
- **노드 드래그 backend persist**: v0.7.122 기반 + 새 endpoint
- **Barnes-Hut quadtree**: ADR 후 multi-session