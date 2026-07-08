---
title: Changelog v0.7.126
created: 2026-07-08
updated: 2026-07-08
type: rule
audience: agent
confidence: high
---

# v0.7.126 — 그래프 노드 드래그 위치 영구 저장 (backend + frontend 통합)

## 무엇을 했는가

GraphCanvas에서 노드를 드래그해 위치를 옮긴 뒤 페이지 reload나 vault 재진입 시에도 그 위치가 유지되도록 backend 저장 + frontend dispatch를 구현했다. ADR 후속 #1의 완결.

### 1. Backend: sidecar JSON + endpoint
- **`raven/core/graph.py`**: `load_user_positions(vault_root)` / `save_user_positions(vault_root, positions)` 헬퍼 추가. vault 루트의 `.graph_positions.json` sidecar를 읽고/쓴다. JSON 스키마: `{schema: 1, updated_at, positions: {slug: {x, y}}}`. 파일 없음/손상/잘못된 키 → 빈 dict 반환 (forceatlas 결과 fallback).
- **`raven/api/server.py` `vault_graph`**: forceatlas 좌표 계산 직후 user override 적용. 두 분기(wiki.db / fallback rglob) 모두에서 동일 패턴.
- **`POST /api/vaults/{name}/graph/positions`**: Pydantic `GraphPositionsBody(positions: dict[str, dict[str, float]])` 받아서 existing과 merge 후 sidecar 저장. 빈 dict 보내면 기존 좌표 그대로 유지.

### 2. Frontend: GraphCanvas → GraphPage → POST
- **`GraphCanvas`**: `onPositionsChange?: (positions) => void` prop 추가. `useNodesState`의 `onNodesChange`를 wrapper로 가로채 `NodeChange` 중 `type: "position" && dragging === false`만 골라 dict로 모아 부모에 1회 callback. 매 mousemove마다 POST가 안 가도록 drag-end 시점에만.
- **`GraphPage.persistPositions`**: callback을 받아 current scope + vault 있을 때 slug 매핑 → `POST /api/vaults/{vault}/graph/positions`. all-scope는 slug 형식이 `{vault}:{slug}`라 별도 사이클에서 처리 (현재 silent skip).

### 3. 사용자 체감 효과
- 노드를 옮긴 뒤 페이지 reload → 그대로 유지.
- 다른 vault 갔다가 돌아와도 그대로.
- forceatlas 재계산 (orphan toggle 등)에도 사용자 위치 존중.

## 변경

| 파일 | 변경 |
|---|---|
| `raven/core/graph.py` | `GRAPH_POSITIONS_FILENAME` 상수 + `load_user_positions` / `save_user_positions` 헬퍼 신규 |
| `raven/api/server.py` | `_load_user_positions`/`_save_user_positions` import. `vault_graph` 두 return 직전에 user override 적용. `GraphPositionsBody` Pydantic + `POST /api/vaults/{name}/graph/positions` endpoint 신규 |
| `dashboard/src/components/GraphCanvas.tsx` | `onPositionsChange` prop + `handleNodesChange` wrapper 신규. ReactFlow `onNodesChange={handleNodesChange}` 연결 |
| `dashboard/src/routes/GraphPage.tsx` | `persistPositions` callback 신규. GraphCanvas에 `onPositionsChange={persistPositions}` 연결. `useCallback` import 추가 |
| `tests/test_graph_positions.py` | 신규 — load/save/roundtrip/invalid JSON/skip invalid entries 4개 테스트 |

## 왜 그렇게 했는가 (§5 4 신호)

- **인수인계 필요성**: ADR 후속 #1 (v0.6.12 종합 changelog에 명시) "노드 드래그 위치 백엔드 persist"의 완결. 다음 사이클에 다시 짤 일 없도록 기반 + 동작 모두 제공.
- **재사용 가능성**: `load_user_positions`/`save_user_positions`은 graph.py 순수 함수 — 다른 layout (예: 향후 Barnes-Hut)에서 동일하게 사용 가능.
- **실패/리스크 기록**: 손상된 sidecar/잘못된 키 silent fallback → 사용자 좌표 잃어도 atlas 계산은 정상. POST 실패도 silent (다음 reload에 retry).

## 검증

| 항목 | 결과 |
|---|---|
| `make typecheck` | exit 0 |
| `pytest tests/test_graph_positions.py` | 4/4 pass |
| `pytest tests/test_api.py` | 55/55 pass (regression) |
| `vitest tests/GraphCanvas*` | 18/18 pass |
| `vitest tests/GraphPage*` | 9/9 pass |
| `vitest tests/PageView*` | 31/31 pass |

## 후속

- **all-scope 노드 드래그 persist**: `{vault}:{slug}` ID 분해해서 per-vault sidecar 또는 단일 통합 sidecar 결정. ADR.
- **.gitignore 처리**: `.graph_positions.json`은 머신별/사용자별 — gitignore 추가 여부는 사용자 결정.
- **Barnes-Hut quadtree**: C1 ADR 후 multi-session.
- **FullscreenGraphModal / FloatingGraphPanel**에 derive 함수 재사용 적용 (B2의 다음 단계).