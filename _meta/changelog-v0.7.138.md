---
title: Changelog v0.7.138
created: 2026-07-09
updated: 2026-07-09
type: rule
audience: agent
confidence: high
---

# v0.7.138 — vault 라벨: zoom out 가드 제거 + fontSize/위치 floor 적용

## BLUF
v0.7.137에서 vault 라벨을 nodeCanvasObject로 통합했지만 여전히 화면에 안 보였음. 원인: `scale >= 0.3` 가드 + fontSize/위치가 `* scale`만 있어서 zoom 4% (사용자 화면)에서 fontSize 0.56px로 사실상 안 보임. 가드 제거 + fontSize/location/lineWidth에 floor 추가.

## 무엇을 했는가

| 파일 | 변경 | 효과 |
|---|---|---|
| `dashboard/src/components/GraphCanvas.tsx` | (1) `scale >= 0.3` 가드 제거. (2) `fontSize = 14 * scale` → `Math.max(9, 14 * scale)`. (3) `labelY = vc.y - 50 * scale` → `vc.y - Math.max(24, 50 * scale)`. (4) `lineWidth = 3 * scale` → `Math.max(1.5, 3 * scale)` | extreme zoom out에서도 라벨이 식별 가능한 크기(9px)로 표시. 위치는 최소 24px 분리 |

## 왜 했는가
- **사용자 2026-07-09 보고**: 화면 4% zoom에서 라벨 안 보임
- **근본 원인**: `fontSize = 14 * scale`에서 scale=0.04면 fontSize 0.56 → 가시 영역 밖. `scale >= 0.3` 가드는 이걸 더 가림.

## 검증
- tsc exit 0
- vitest 149 passed + 1 skipped
- 실 브라우저에서 4% zoom 상태에서도 라벨 보이는지 확인 (사용자)