---
title: Changelog v0.7.131
created: 2026-07-08
updated: 2026-07-08
type: rule
audience: agent
confidence: high
---

# v0.7.131 — graph culling refinement + perf harness + positions policy

## BLUF
그래프 성능 작업을 작은 패치로 쪼개지 않고 한 배치로 정리했다. dense all-vault graph의 edge culling을 **incident-node 기준에서 true line-viewport intersection 기준**으로 올렸고, 반복 측정용 perf 스크립트와 `.graph_positions.json` 운영 정책 문서를 함께 추가했다.

## 무엇을 했는가

| 파일 | 변경 | 효과 |
|---|---|---|
| `dashboard/src/components/GraphCanvas.tsx` | `pointInsideExpandedRect`, `segmentIntersectsExpandedRect`, `edgeTouchesViewport` 추가 | viewport 밖이지만 화면을 가로지르는 긴 edge 유지 |
| `dashboard/src/components/GraphCanvas.tsx` | `screenNodeCenters` 상태 추가 + visible recompute에서 screen center 캐시 | edge 선분 교차 판정에 필요한 screen-space endpoints 확보 |
| `dashboard/tests/GraphPage.all-vault-scope.test.tsx` | true intersection culling contract 업데이트 | raw contract 회귀 가드 |
| `scripts/graph_perf_benchmark.py` | synthetic sparse/dense graph benchmark 추가 | layout 성능 반복 측정/비교용 harness |
| `docs/graph-positions-policy.md` | `.graph_positions.json` 운영 정책 문서화 | 로컬 상태 vs SOT 경계 명시 |

## 왜 했는가
- **재사용 가능성**: 그래프 성능 작업을 다음 세션에서도 재현 가능하게 측정/운영 문맥까지 묶어 둠
- **실패 방지**: 단순 endpoint-visible 기준 culling이 긴 edge를 과하게 잘라내는 문제를 줄임
- **맥락 추적**: `.graph_positions.json`을 content SOT로 오해하지 않도록 정책을 문서로 분리

## 검증
- `make typecheck` ✅
- `pytest tests/test_graph_positions.py -q` → **4 passed** ✅
- `cd dashboard && npx vitest run tests/GraphPage.all-vault-scope.test.tsx tests/GraphCanvas* tests/PageView*` → **60 passed** ✅
- `python scripts/graph_perf_benchmark.py --nodes 120,180 --iterations 20 --repeats 2` ✅

## perf sample
```text
iterations=20 repeats=2
case,nodes,edges,min_s,median_s,mean_s,max_s
sparse-120,120,232,0.0849,0.0854,0.0854,0.0859
dense-120,120,581,0.0937,0.0942,0.0942,0.0946
sparse-180,180,352,0.1971,0.1995,0.1995,0.2018
dense-180,180,881,0.2205,0.2207,0.2207,0.2209
```

## 메모
워킹트리에 남아 있던 다른 수정본(`log.md`, `raven/core/log.py`, 일부 tests, `changelog-v0.7.129.md`)은 이번 배치 범위 밖이라 commit에 포함하지 않았다.
