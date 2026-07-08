---
title: Changelog v0.7.128
created: 2026-07-08
updated: 2026-07-08
type: rule
audience: agent
confidence: high
---

# v0.7.128 — Barnes-Hut adaptive gate/theta

## BLUF
Barnes-Hut 전환을 `n >= 180` 고정값 하나에만 의존하지 않고, **노드 수 + 평균 degree**를 함께 보는 adaptive gate로 바꿨다. dense all-vault graph는 더 일찍 근사 경로를 타고, sparse graph는 exact pairwise를 더 오래 유지한다.

## 무엇을 했는가

| 파일 | 변경 | 효과 |
|---|---|---|
| `raven/core/graph.py` | `should_use_barnes_hut(node_count, avg_degree)` 추가 | dense graph 조기 전환 |
| `raven/core/graph.py` | `barnes_hut_theta(avg_degree)` 추가 | dense graph에서 더 보수적인 theta 적용 |
| `raven/core/graph.py` | `forceatlas_layout()`가 adaptive gate/theta 사용 | hard-coded `n >= 180` 제거 |
| `tests/test_api.py` | adaptive gate/theta pure helper 회귀 추가 | threshold 흔들림 방지 |

## 왜 했는가
- **재사용 가능성**: large graph 성능 정책은 이후 그래프 작업의 공통 기반
- **맥락 추적**: v0.7.127의 고정 전환값이 왜 바뀌었는지 남겨야 함
- **실패 방지**: all-vault dense map에서 작은 n에도 O(n²) 병목이 먼저 오는 케이스 방지

## 정책
- `node_count >= 180` → 무조건 Barnes-Hut
- `node_count >= 140` and `avg_degree >= 6.0` → Barnes-Hut
- `node_count >= 110` and `avg_degree >= 10.0` → Barnes-Hut
- 그 외 → exact pairwise 유지

### theta
- `avg_degree >= 10.0` → `0.82`
- `avg_degree >= 6.0` → `0.86`
- else → `0.90`

## 검증
- `make typecheck` ✅
- `pytest tests/test_api.py -q` → **57 passed** ✅
- `pytest tests/test_api.py tests/test_graph_positions.py -q` → **61 passed** ✅

## 메모
이번 사이클의 변화는 frontend 무변경, backend layout heuristic 조정이다. 다음 후보는 edge viewport culling 또는 `.graph_positions.json` 정책 정리.
