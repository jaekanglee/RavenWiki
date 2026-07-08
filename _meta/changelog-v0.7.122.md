---
title: Changelog v0.7.122
created: 2026-07-08
updated: 2026-07-08
type: rule
audience: agent
confidence: high
---

# v0.7.122 — 그래프 캔버스 서버 layout 동기화 정밀화 + vault halo 좌표 변환 헬퍼 통합

## 무엇을 했는가

대시보드 그래프 캔버스의 서버 layout → xyflow controlled state 동기화 및 all-vault 모드 vault halo/label 좌표 변환을 정밀화했다.

### 1. Server layout sync 정밀화 (GraphCanvas.tsx)
- **변경 전**: `useEffect(() => setFlowNodes(rfNodes), [rfNodes, setFlowNodes])` — props 변경마다 무조건 setState.
- **변경 후**: `nodesLayoutChanged(prev, rfNodes)` 의미 비교 후 변경 있을 때만 setState. id 리스트 변동 또는 같은 id의 (x, y) 변동만 감지 → drag 등 client-only 필드 변경 시 xyflow 내부 상태 보존.
- **부수 효과**: `useNodesState(rfNodes)` mount 직후 1회 불필요 setState 제거 → React 18 strict mode + xyflow 마운트 비용 절감.
- **ADR 후속 기반**: `adr-2026-06-29-graph-v0.6.12-summary.md` 후속 #1 (노드 드래그 위치 persist)의 1단계. 다음 라운드에서 position 변경 시 backend `POST /api/vaults/{vault}/graph/positions` 추가 가능.

### 2. Vault halo/label 좌표 변환 헬퍼 통합
- **변경 전**: `vaultCentroids.map(vc => flowToScreenPosition(...) + radius * zoom)` 로직이 mount useEffect와 `handleMove` 양쪽에 inline 중복.
- **변경 후**: `vaultScreenFromCentroids(vaultCentroids, zoom, flowToScreenPosition)` 모듈 레벨 헬퍼로 추출 → 두 호출처가 동일 contract 공유.
- **deps 정밀화**: mount useEffect deps에서 `zoom` 제거. zoom/pan 미세 변동마다의 setState 폭증 차단. pan/zoom 시의 재계산은 `handleMove`(xyflow `onMove`)가 단일 담당.

## 변경

| 파일 | 변경 |
|---|---|
| `dashboard/src/components/GraphCanvas.tsx` | `nodesLayoutChanged`/`edgesRefChanged` 헬퍼 신규, setState 호출에 의미 비교 적용. `vaultScreenFromCentroids` 헬퍼 신규로 mount useEffect + handleMove 중복 제거. |
| `dashboard/tests/GraphPage.all-vault-scope.test.tsx` | vaultScreenFromCentroids 헬퍼 추출에 맞춰 contract 테스트 갱신 (헬퍼 내 `vc.radius * zoom` 존재 검증). |

## 왜 그렇게 했는가 (§5 4 신호)

- **인수인계 필요성**: 1004줄짜리 GraphCanvas.tsx의 setState 흐름이 다음 라운드 노드 드래그 persist 패치의 진입점. 의미 비교 헬퍼가 그 기반.
- **실패/리스크 기록**: drag 중 부모 props 재평가 → 무조건 setFlowNodes → xyflow 내부 drag 위치 reset되는 잠재 회귀 가능성을 헬퍼로 차단.
- **재사용 가능성**: vaultScreenFromCentroids는 mount 시점 + 매 viewport 변경 양쪽에서 동일 contract. 추후 test 또는 다른 vault 시각화 layer에서 재사용 가능.

## 검증

| 항목 | 결과 |
|---|---|
| `make typecheck` | exit 0 |
| `vitest tests/GraphCanvas*` | 18/18 pass |
| `vitest tests/GraphPage*` | 9/9 pass |
| 회귀 (Folder-hover-menu, Modal-close-sidebar) | main에서도 같은 2건 실패 — 무관 |

## 후속

- **노드 드래그 위치 백엔드 persist**: `useNodesChange`로 position 변경 감지 → `POST /api/vaults/{vault}/graph/positions` (per-vault `.vault.json` 또는 sidecar JSON에 저장) → 다음 loadGraph 시 rfNodes 머지.
- **Barnes-Hut quadtree (force-atlas O(n²) → O(n log n))**: ADR 작성 후 multi-session.