---
title: Changelog v0.7.143
created: 2026-07-09
updated: 2026-07-09
type: rule
audience: agent
confidence: high
---

# v0.7.143 — vault 라벨: vault별 최상단 노드 위에 띄움 + 큰 글씨 + 진단 마커 정리

## BLUF
v0.7.142(흰색 진단)에서 라벨이 뜨긴 뜸 보고 받음. 사용자 추가 보고: "진짜 작다", "군집 가운데 뜨는 게 아니라 한쪽으로 치우침". centroid는 노드 평균이라 정확히 군집 한복판 — 그 위에 띄우면 노드들이 빽빽해서 묻힘. **vault별 최상단 노드 y**를 data effect에서 미리 계산해서 ref에 보관 → 라벨이 그 위에 떠 vault 영역과 자연스럽게 어울리게. fontSize floor 14 → 17 (사용자 "진짜 작다"). 진단용 TEST/X 마커 제거.

## 무엇을 했는가

| 파일 | 변경 | 효과 |
|---|---|---|
| `dashboard/src/components/GraphCanvas.tsx` | (1) `vaultTopYRef: Map<string, number>` 추가. (2) data effect에서 `graph.graphData()` 대신 `formattedNodes`로 vault별 최상단 y 계산해서 ref 갱신. (3) nodeCanvasObject 안에서 `topY = vaultTopYRef.current.get(vc.vault) ?? vc.y` → `labelY = topY - Math.max(20, 25*scale)`. (4) `fontSize = Math.max(17, 16*scale)`. (5) vault 색 복귀 (v0.7.142 흰색 진단에서). (6) 진단용 TEST/X 마커 제거 | vault 라벨이 실제 vault 영역의 최상단에 떠있음. 글씨 더 큼. TEST/X 진단 잡음 제거 |

## 왜 했는가
- **사용자 2026-07-09 보고**: "뜨긴뜨는데 진짜 작고, 그 볼트의 문서가 몰려있는 군집에 가운데 뜨는 게 아니라 [한쪽으로]"
- **근본 원인**: centroid = 노드 좌표 평균 → 정확히 군집 한복판. 한복판은 노드들이 빽빽한 곳이라 라벨이 묻히거나 한쪽 가장자리로 치우쳐 보임. **최상단 노드 y**가 라벨 위치로 더 자연스러움.

## 동작
- vault 라벨 = vault별 최상단 노드 바로 위 (zoom 따라 25*scale 또는 최소 20px)
- fontSize = max(17, 16*scale) — zoom 20%에서 17px, zoom 100%에서 16px
- 라인 outline = 검은색 0.5~2px (다크 배경 가독성)
- TEST/X 진단 마커 제거 (이전 보고로 위치/색 문제 규명 완료)

## 검증
- tsc exit 0
- vitest 149 passed + 1 skipped (회귀 0)
- 사용자 reload 후 vault 라벨이 vault 영역 최상단에 떠있고 글씨 충분히 큰지 확인

