---
title: Changelog v0.7.145
created: 2026-07-09
updated: 2026-07-09
type: rule
audience: agent
confidence: high
---

# v0.7.145 — single vault 그래프 라벨 시인성: weight threshold 6→8

## BLUF
사용자 보고: "라벨이 너무 많이 떠있어서 시인성이 어렵다". `canShowNormalLabel`의 weight 임계값을 `>=6` → `>=8`로 단일 라인 조정. 작은 vault에서도 weight 8+ hub 노드만 라벨 유지 → 시야가 뚫리고 그래프 구조 파악 용이.

## 무엇을 했는가

| 파일 | 변경 | 효과 |
|---|---|---|
| `dashboard/src/components/GraphCanvas.tsx` | `canShowNormalLabel = scale > 0.85 \|\| (node.weight ?? 0) >= 8` (L538, 1줄) | weight 6~7 leaf/mid 노드 라벨 자동 제거. weight 8+ hub만 항상 라벨 |

## 왜 했는가
- **사용자 2026-07-09 보고**: "라벨이 너무 많이 떠있어서 시인성이 어렵다"
- **진단 (codex cli + agy cli 협의)**: `weight >= 6` 조건이 scale 무관하게 발동 → 작은 vault에서도 weight 6+ 노드가 다수라 라벨 과다
- **선택 옵션**:
  - A. threshold 상향 1줄 — agy/codex 모두 surgical 추천
  - B. hover-only — 둘 다 ❌ (overview 손실)
  - C. toolbar 토글 — 변경량 큼, 기본값은 여전히 잡음
  - D. importance frontmatter — backend 변경 큼, 우선순위 제외

## 동작
- single vault 그래프에서 weight 8+ 만 무조건 라벨
- weight 6~7 mid-importance 노드는 zoom-in 시에만 라벨 (`scale > 0.85` 살아 있음)
- focus/highlighted 노드는 그대로 라벨 유지 (UX 일관성)

## 보존/제외
- 보존: scale > 0.85 (zoom-in 시 라벨 활성), focus/highlight 라벨 강제
- 보존: dense 분기 (현재 코드에서 `density="dense"` 사용처 없지만 contract 유지)
- 제외: toolbar 토글 (후속 사용자가 보고 싶다면 추가 가능)

## 검증
- tsc exit 0
- vitest 137 passed + 1 skipped (회귀 0)
- (사용자 reload 후 라벨 수 줄어드는지 확인)

## 협의 출처
codex cli + agy cli 병렬 consult (`deleg_29eae589`). agy가 `B+A` (threshold + 토글)도 surgical 추천이었지만, 사용자 결정 "심플하게 1줄" → 옵션 A만 적용.
