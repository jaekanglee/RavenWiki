---
title: Changelog v0.7.146
created: 2026-07-09
updated: 2026-07-09
type: rule
audience: agent
confidence: high
---

# v0.7.146 — single vault 그래프 시각 polish 3종 (라벨/LOD/edge)

## BLUF
사용자 2026-07-09 보고: "어떤건 라벨 나오고 어떤건 안나와" + "path랑 노드 스타일이 매우 올드해. 부드럽거나 세련된 느낌 아니라, 투박해". 3가지 surgical polish 적용.

## 무엇을 했는가

| 변경 | 위치 | 효과 |
|---|---|---|
| **(A) zoom-aware 라벨 LOD 분리** | `GraphCanvas.tsx` L538 | `scale > 1.0 && weight >= 3` (zoom-in mid) OR `weight >= 8` (hub). zoom-out (예: 8%)에서 weight 8+ hub만 보이던 게 자연스럽게: zoom 100%+에선 weight 3+도 보임 |
| **(B) 라벨 collision 회피** | `GraphCanvas.tsx` L553 부근 | `scale < 1.5`이면 라벨을 노드 오른쪽으로 `(size + 8) / scale` 오프셋. zoom-out에서 라벨이 노드 본체에 박혀 깨짐 해소 |
| **(C) edge stroke polish** | `GraphCanvas.tsx` L470 | edge alpha 0.28 → 0.40 (slate-400), highlight 0.85. lineWidth 0.8 → 1.2. "투박함" 단순 polish — 색/굵기만 |

## 왜 했는가
- **사용자 2026-07-09 보고**: "이렇게 나오는데 맞아? 그넫 어떤건 라벨이 나오고, 어떤건 안나오거.. 그리거 패쓰랑 노드 스타일이 매우 올드해. 부드럽거나 세련된 느낌 아니라, 투박해"
- **옵시디안 모방 안 함** — 사용자 톤 ("고딥필 필요 없음"). 단순 polish 3개로 충분.

## 동작
- **zoom-out** (8%): weight 8+ hub만 라벨 (LOD 정확히) — 이제 zoom-in 시 mid importance 추가 보임
- **zoom-in** (100%+): weight 3+ 도 모두 라벨 — 사용자 탐색 보강
- **라벨 위치**: zoom-out에선 노드 옆으로 띄움, zoom-in에선 가운데 (그대로)
- **edge**: 더 진하고 두꺼워서 "세련" 느낌 (alpha 0.40, lineWidth 1.2)

## 보존/제외
- 옵시디안 모방 (gradient ring, halo 등) ❌ — 사용자 톤 위배
- footer cmd (폴리곤화) ❌ — surgical 변경 손해 보기 큼
- toolbar 토글 ❌ — 사용자 단순화 요청

## 검증
- tsc exit 0
- vitest 137 + 1 skipped (회귀 0)
- (사용자 reload 후 3개 polish 확인)
