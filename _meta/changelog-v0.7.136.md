---
title: Changelog v0.7.136
created: 2026-07-09
updated: 2026-07-09
type: rule
audience: agent
confidence: high
---

# v0.7.136 — dense 노드 사이즈 축소 + vault 링 톤 다운 + 팔레트 lilac + cell_span 축소

## BLUF
all-scope 그래프의 시각적 잡음을 일괄 정리. (1) dense 노드 사이즈 축소 (multiplier 7→4, base 10→7), (2) vault 링 alpha 0.55→0.30, 두께 2.4→1.6px, (3) 팔레트 pink → lilac (사용자 "촌시러" 보고), (4) server.py cell_span 1300→850로 fitView 후 zoom scale 회복 → vault 라벨 식별 가능.

## 무엇을 했는가

| 파일 | 변경 | 효과 |
|---|---|---|
| `raven/api/server.py` | `cell_span = 1300.0` → `cell_span = 850.0` | 5 vault 격자 좌표 ±3250 → ±~2100. fitView 후 zoom scale 0.23 → 0.45 회복 |
| `dashboard/src/components/GraphCanvas.tsx` | `nodeSize` dense: multiplier 7→4, base 10→7 | dense 노드 leaf 17→11, w=10 → 38→20, hub → 48→26 |
| `dashboard/src/components/GraphCanvas.tsx` | vault ring: alpha 0.55→0.30, lineWidth 2.4→1.6, arc 1.6/scale | 노드 본체 색/type 식별 회복 |
| `dashboard/src/components/GraphCanvas.tsx` | VAULT_HALO_COLORS 5번째 pink(#ec4899) → lilac(#a78bfa) | 비비드 분홍 → 차분한 라일락. TYPE_COLORS의 person은 유지 |
| `dashboard/tests/GraphCanvas.obsidian-style.test.ts` | dense > normal → dense < normal contract 변경 + dense hub cap 30px 테스트 추가 | 회귀 가드 갱신 |

## 왜 했는가
- **사용자 2026-07-09 보고들**:
  - "노드들이 너무 크다기보다 두껍다" → dense 노드 사이즈 축소
  - "path도 너무 색이..." → ring 톤 다운
  - "분홍계열 너무 촌시러" → lilac 교체
  - "안보임 맞춤보기 해도" → cell_span 1300→850로 fitView zoom 회복

## 검증
- tsc exit 0
- vitest 149 passed + 1 skipped
- pytest graph 11/11
- 실 브라우저 reload 후 라벨 가독성 + lilac 톤 + 노드 크기 확인 필요 (사용자)