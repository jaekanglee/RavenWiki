---
title: Changelog v0.7.142
created: 2026-07-09
updated: 2026-07-09
type: rule
audience: agent
confidence: high
---

# v0.7.142 — vault 라벨 진단: 흰색 + 위치 floor 60

## BLUF
사용자가 TEST 마커는 보이지만 vault 라벨 본문은 안 보인다고 보고. 진단을 위해 라벨 색을 흰색으로 일시 변경하고 위치를 더 띄움 (zoom-floor 60). 안 보이면 위치 문제, 보이면 색/잘림 문제.

## 무엇을 했는가

| 파일 | 변경 | 효과 |
|---|---|---|
| `dashboard/src/components/GraphCanvas.tsx` | (1) `color = "#ffffff"` (한시 진단). (2) `labelY = vc.y - Math.max(60, 60 * scale)` (60px floor). (3) fontSize floor 14, lineWidth floor 0.5~1.5. (4) outline 검은색 | vault 색 무관하게 흰색 본문 + 검은 outline. 위치 더 위로 (노드들과 안 겹침) |

## 왜 했는가
- **사용자 보고 (2026-07-09)**: "캔버스 군집 중앙에 [TEST] 나옴". TEST는 보이는데 vault 라벨만 안 보임 → centroid에 라벨 띄우면 노드들이 빽빽한 곳에 박혀서 묻힘 가능성.

## 검증
- tsc exit 0
- vitest 149 passed + 1 skipped (회귀 0)
- 사용자 reload 후 5개 vault 라벨이 흰색으로 보이는지 확인. 보이면 → 색 라벨로 복귀, 안 보이면 → 위치 fix 추가

