---
title: Changelog v0.7.139
created: 2026-07-09
updated: 2026-07-09
type: rule
audience: agent
confidence: high
---

# v0.7.139 — vault 라벨 디버그 로그 (한시적)

## BLUF
v0.7.138에서도 사용자가 라벨 안 보인다고 보고해서 진단. centroids가 실제로 그려지고 있는지 확인용 한시적 console.log 추가.

## 무엇을 했는가

| 파일 | 변경 | 효과 |
|---|---|---|
| `dashboard/src/components/GraphCanvas.tsx` | centroids.length > 0일 때 첫 매치 1회에 한해 console.log | 사용자가 DevTools Console에서 `[vault label] centroids: 5 [...]` 형태로 확인 가능 |
