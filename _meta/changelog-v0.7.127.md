---
title: Changelog v0.7.127
created: 2026-07-08
updated: 2026-07-08
type: rule
audience: agent
confidence: high
---

# v0.7.127 — all-vault 드래그 저장 + Barnes-Hut + edge churn 절감

## BLUF
그래프 대형화 시 체감 성능 병목 3개를 한 사이클에서 함께 줄였다: **all-vault 드래그 위치 영구 저장**, **large graph repulsion의 Barnes-Hut 근사**, **idle dense edge object churn/animation 축소**.

## 무엇을 했는가

| 파일 | 변경 | 효과 |
|---|---|---|
| `dashboard/src/routes/GraphPage.tsx` | drag persist fan-out 로직 추가 | all-scope에서도 vault별로 좌표 저장 |
| `dashboard/src/components/GraphCanvas.tsx` | `baseDisplayEdges` memo + dense idle edge 재사용 + dense highlight animation off | 대형 all-vault 그래프 idle 렌더 부담 감소 |
| `raven/core/graph.py` | `forceatlas_layout()` large-graph Barnes-Hut repulsion 추가 (`n >= 180`) | O(n²) repulsion 병목 완화 |
| `tests/test_api.py` | large-graph deterministic/normalized 회귀 테스트 추가 | Barnes-Hut 안정성 가드 |
| `dashboard/tests/GraphPage.all-vault-scope.test.tsx` | all-vault persist + dense edge contract 갱신 | UI/API contract 회귀 가드 |

## 왜 했는가

AGENTS.md §5 저장 신호 기준:
1. **재사용 가능성** — large vault graph 성능/배치 저장은 반복 사용되는 핵심 UX
2. **인수인계 필요성** — Barnes-Hut threshold(`n >= 180`)와 dense edge idle 정책은 다음 세션도 알아야 함
3. **맥락 추적** — current-scope persist만 있던 상태에서 all-scope 누락을 메웠음
4. **실패 방지** — 대형 그래프에서 exact repulsion O(n²) 병목 재발 방지

## 구현 메모

### 1. all-vault drag persist
- 기존 v0.7.126은 current scope만 저장
- 이번엔 `GraphPage`에서 드래그 종료 payload를 `vault -> {slug: {x,y}}`로 fan-out
- 각 vault의 `/api/vaults/{vault}/graph/positions`로 병렬 POST

### 2. Barnes-Hut threshold
- exact pairwise repulsion은 유지하되 `n >= 180`에서만 quadtree 근사 사용
- small graph는 기존 deterministic exact path 그대로 유지
- self-force approximation 방지를 위해 **현재 노드를 포함하는 cell은 재귀 하강**, 충분히 먼 타 cell만 aggregate mass 근사

### 3. edge churn 절감
- dense idle 상태에선 `baseDisplayEdges` memoized array 재사용
- focus가 켜질 때만 highlight overlay style object 재생성
- dense mode에선 edge animation 비활성화 (`animated: highlighted && !isDense`)

## 검증
- `make typecheck` ✅
- `pytest tests/test_api.py tests/test_graph_positions.py -q` → **60 passed** ✅
- `cd dashboard && npx vitest run tests/GraphPage.all-vault-scope.test.tsx tests/GraphCanvas.mobile-tap-label.test.ts` → **15 passed** ✅
- `cd dashboard && npx vitest run tests/GraphCanvas* tests/GraphPage* tests/PageView*` → **59 passed** ✅

## 다음 후보
1. large graph에서 Barnes-Hut threshold/`theta` 자동 튜닝 (`n`, avg degree 기반)
2. `.graph_positions.json` gitignore / 운영정책 정리 (사용자 승인 필요)
3. edge viewport-level culling (정말 큰 all-vault 전용, 별도 사이클)
