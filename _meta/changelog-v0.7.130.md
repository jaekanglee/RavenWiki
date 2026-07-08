---
title: Changelog v0.7.130
created: 2026-07-08
updated: 2026-07-08
type: rule
audience: agent
confidence: high
---

# v0.7.130 — visibleNodeIds recompute rAF coalescing

## BLUF
edge viewport culling의 `visibleNodeIds` 재계산을 `onMove`마다 즉시 수행하지 않고, **`requestAnimationFrame` 기준 frame당 1회로 합쳤다**. pan/zoom 중 state churn을 더 줄인다.

## 무엇을 했는가

| 파일 | 변경 | 효과 |
|---|---|---|
| `dashboard/src/components/GraphCanvas.tsx` | `visibleNodeIdsRafRef` 추가 | 중복 frame 예약 방지 |
| `dashboard/src/components/GraphCanvas.tsx` | `recomputeVisibleNodeIdsNow` / `recomputeVisibleNodeIds` 분리 | 실제 계산 vs 스케줄링 분리 |
| `dashboard/src/components/GraphCanvas.tsx` | `requestAnimationFrame` coalescing 적용 | pan/zoom 중 frame당 최대 1회 재계산 |
| `dashboard/src/components/GraphCanvas.tsx` | unmount 시 `cancelAnimationFrame` cleanup | dangling callback 방지 |
| `dashboard/tests/GraphPage.all-vault-scope.test.tsx` | rAF contract 추가 | 회귀 가드 |

## 왜 했는가
- **재사용 가능성**: all-vault dense graph 이동 성능 최적화의 다음 단계
- **실패 방지**: viewport move 이벤트가 잦을 때 setState 폭주 방지
- **맥락 추적**: v0.7.129가 edge 수를 줄였다면, v0.7.130은 recompute 빈도를 줄인다

## 구현 메모
- `recomputeVisibleNodeIdsNow()` = 실제 visible set 계산
- `recomputeVisibleNodeIds()` = 이미 예약된 frame이 없을 때만 `requestAnimationFrame` 등록
- 초기 mount 동기화는 즉시 계산 유지 (`recomputeVisibleNodeIdsNow()`)
- `resize` / `onMove`는 scheduling 경로 사용

## 검증
- `make typecheck` ✅
- `cd dashboard && npx vitest run tests/GraphPage.all-vault-scope.test.tsx tests/GraphCanvas* tests/PageView*` → **60 passed** ✅
