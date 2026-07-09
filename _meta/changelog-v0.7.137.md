---
title: Changelog v0.7.137
created: 2026-07-09
updated: 2026-07-09
type: rule
audience: agent
confidence: high
---

# v0.7.137 — vault 라벨: onRenderFramePost → nodeCanvasObject 통합

## BLUF
v0.7.135~136의 vault 라벨이 `graph.onRenderFramePost`에 등록되어 있어서 force-graph가 frame redraw를 trigger하지 않으면 라벨이 영영 안 그려졌다 (fitView만 했을 때 발생). 사용자 보고: "왜 전체모드일 때 군집에 볼트이름 안나오냐고 대체". `nodeCanvasObject` 안으로 라벨 그리기 로직을 옮겨서 매 paint마다 안정적으로 그려지도록 수정.

## 무엇을 했는가

| 파일 | 변경 | 효과 |
|---|---|---|
| `dashboard/src/components/GraphCanvas.tsx` | (1) v0.7.135~136의 `drawVaultLabel` useEffect 제거 (`graph.onRenderFramePost` 등록 코드). (2) `nodeCanvasObject` 안에서 vaultCentroids 순회하며 centroid 위치에 텍스트 + outline 그림. fillText idempotent이므로 매 노드 × 매 vault 호출되어도 결과 동일 | vault 라벨이 매 paint마다 안정적으로 표시됨. force-graph frame redraw 트리거에 의존 안 함 |

## 왜 했는가
- **사용자 2026-07-09 보고**: "아니 왜 전체모드일 때 군집에 볼트이름 안나오냐고 대체" — all-scope 모드에서 5 vault 라벨이 영영 안 보임.
- **근본 원인**: force-graph의 `onRenderFramePost` 콜백은 **frame redraw가 trigger되어야만** 호출됨. fitView만 했을 때 정적 layout이면 frame 다시 안 그릴 수 있어 콜백 미호출 → 라벨 없음.

## 동작
- **이전 (v0.7.135~136)**: `onRenderFramePost` 1회 등록 → frame redraw 시에만 라벨 그림
- **현재 (v0.7.137)**: 매 노드 canvas render 시 vault 라벨도 같이 그림 → 항상 보임
- **performance**: 369 노드 × 5 vault = 1845 fillText/frame → 무시 가능

## 검증
- tsc exit 0
- vitest 149 passed + 1 skipped (회귀 0)
- 실 브라우저에서 reload 후 5개 vault 라벨 보이는지 확인 (사용자)