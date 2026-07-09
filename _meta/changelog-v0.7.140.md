---
title: Changelog v0.7.140
created: 2026-07-09
updated: 2026-07-09
type: rule
audience: agent
confidence: high
---

# v0.7.140 — vault 라벨 시각 디버그 마커 (한시적)

## BLUF
v0.7.137~139에서도 vault 라벨이 여전히 안 보인다는 사용자 보고. 원인 진단을 위해 화면에 2개 마커 임시 추가: (1) screen 좌표 (200,100)에 빨간 "TEST" 텍스트 — ctx.fillText 정상 동작 확인. (2) 첫 vault centroid 위치에 초록 "X" — centroid 좌표가 viewport 안에 있는지 확인. 일시적 코드.

## 무엇을 했는가

| 파일 | 변경 | 효과 |
|---|---|---|
| `dashboard/src/components/GraphCanvas.tsx` | (1) vault 라벨 코드 진입 시 screen 좌표 (200, 100)에 빨간 "TEST" 텍스트 1회 fillText. (2) 첫 vault centroid 위치에 초록 "X" 1회 fillText. (3) vault 라벨 본문/순서 정리: 본문(filled) → outline(stroked) order 변경, fontSize floor 11, lineWidth max 0.8 floor | 사용자 reload 후 3가지 마커 표시 여부로 fillText/centroid/라벨 원인 규명 가능 |

## 동작
- 빨간 TEST 보임 → fillText 정상
- 초록 X 위치 확인 → centroid viewport 안/밖 판단
- vault 본문 라벨 보임 → 라벨 코드 정상

## 검증
- tsc exit 0
- 사용자 reload 후 3개 마커 상태 보고 필요