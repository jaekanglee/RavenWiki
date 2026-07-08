---
title: Changelog v0.7.129
created: 2026-07-08
updated: 2026-07-08
type: rule
audience: agent
confidence: high
---

# v0.7.129 — GraphCanvas edge viewport culling

## BLUF
all-vault dense graph에서 edge를 항상 전부 그리지 않고, **현재 viewport 근처 node에 연결된 edge만 렌더**하도록 바꿨다. focus/highlight edge는 예외로 유지한다.

## 무엇을 했는가

| 파일 | 변경 | 효과 |
|---|---|---|
| `dashboard/src/components/GraphCanvas.tsx` | `shouldCullEdges` 추가 (`dense && edge >= 400`) | 작은 그래프 회귀 없이 큰 그래프만 최적화 |
| `dashboard/src/components/GraphCanvas.tsx` | `visibleNodeIds` 계산 (`flowToScreenPosition` + container bounds + overscan 120) | viewport 주변 node 판별 |
| `dashboard/src/components/GraphCanvas.tsx` | `baseDisplayEdges` / `displayEdges`에서 offscreen edge filter | idle/focus 모두 edge 수 감소 |
| `dashboard/tests/GraphPage.all-vault-scope.test.tsx` | viewport culling raw contract 추가 | 회귀 가드 |

## 왜 했는가
- **재사용 가능성**: all-vault dense map의 공통 성능 병목 완화
- **실패 방지**: edge 수가 커질 때 팬/줌 인터랙션이 끊기는 회귀 예방
- **맥락 추적**: Barnes-Hut 이후 남은 주요 프론트 병목이 edge DOM churn이었음

## 구현 메모
- 전면적인 geometric line clipping 대신 **incident-edge culling**으로 surgical 적용
- 기준: `isDense && flowEdges.length >= 400`
- visible 판정: node center screen 좌표가 viewport + overscan(120px) 안에 있으면 visible
- edge 렌더 유지 조건:
  - normal idle: source/target 중 하나라도 visible
  - focus active: highlighted edge는 항상 유지, 나머지는 동일 기준

## 검증
- `make typecheck` ✅
- `cd dashboard && npx vitest run tests/GraphPage.all-vault-scope.test.tsx tests/GraphCanvas* tests/PageView*` → **60 passed** ✅

## 메모
긴 edge가 화면을 가로질러도 양 끝점이 모두 바깥이면 생략될 수 있다. 이번 사이클은 성능 우선의 surgical trade-off이며, 필요하면 다음엔 true line-viewport intersection culling으로 고도화 가능.
