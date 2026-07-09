---
title: Changelog v0.7.133
created: 2026-07-09
updated: 2026-07-09
type: rule
audience: agent
confidence: high
---

# v0.7.133 — all-scope graph: 진짜 edge만 path로 렌더링

## BLUF
전체 vault 그래프(`?scope=all`)에서 vault들이 edge와 무관하게 원형으로 묶여 보이던 요식행위(vault centroid 원형 배치 + cluster_compaction 0.78)를 제거했다. 대신 vault들을 sqrt(N) × sqrt(N) 격자로 분산 배치해 시각적 분리는 유지하되, "링처럼 연결된 것처럼" 보이던 거짓 효과는 제거했다. 진짜 wikilink edge만 시각적 연결로 의미가 있고, edge가 없으면 vault들은 자기 격자 셀 안에 흩어져 있을 뿐 서로 연결되지 않는다.

## 무엇을 했는가

| 파일 | 변경 | 효과 |
|---|---|---|
| `raven/api/server.py` | all-scope 분기에서 vault_ring_radius / vault_centroids / cluster_compaction 제거. 대신 격자 배치(`grid_side = ceil(sqrt(n_vaults))`, `cell_span = 1300`) 도입 | edge 0건일 때 vault들이 "링처럼" 묶여 보이지 않음. 사용자가 "연결된 것"으로 오해할 수 있는 시각적 묶음 해소. 단 vault들이 자기 격자 셀에 흩어져 시각적 구분은 유지 |
| `tests/test_api.py` | `test_api_vault_graph_all_scope_groups_nodes_per_vault` → `test_api_vault_graph_all_scope_keeps_current_layout_grid_separated`로 교체 | (1) intra-vault 상대 패턴 보존 (centroid 평행이동만 함) (2) cross-vault wikilink 0건 → edges=[] 검증 (3) 격자로 vault 간 시각적 분리 (inter > max(intra) + 100) |
| `dashboard/tests/GraphPage.all-vault-scope.test.tsx` | 새 it 블록: `cluster_compaction`/`vault_centroid`/`vault_ring`/cos(angle)/sin(angle) 패턴이 프론트에 등장하면 실패 | 프론트가 자체적으로 vault centroid 연산을 다시 도입하는 회귀 차단 |
| `_meta/changelog-v0.7.133.md` | 본 changelog 작성 | |

## 왜 했는가
- **요구 (사용자 2026-07-09)**: "실제로 연결된 것만 path로 연결해서 보여주도록 해줘. 연결 안된건 적당히 노드만 보여주고. 의미없이 요식행위로 모든 노드를 path로 엮는 걸로 보고싶진 않다."
- **실측**: v0.7.123~v0.7.132의 lightweight A' layout은 vault centroid를 큰 원형에 균등 배치 + cluster_compaction 0.78로 vault 안 노드끼리 뭉치게 함 → edge 0개여도 vault들이 시각적으로 묶여 보임. 사용자 입장에서는 "vault들이 서로 연결된 것"으로 오해.

## 동작 변화
- **Before**: vault A/B/C 등록만 해도 → A/B/C 노드들이 원형에 균등 배치되어 "링" 형성. edge 0개여도 링 보임.
- **After**: 동일 조건 → A/B/C 노드들이 격자 셀에 흩어져 있음. edge 없으면 path 없음. vault 구분은 노드 외곽선 vault 색 ring (v0.7.139+)에 의존.

## contract 노트
- ±500 정규화 contract는 **단일 vault (current scope) 전용**. all-scope은 N vault를 격자 분산하므로 좌표 범위는 ±(cell_span × grid_side / 2 + 500) ≈ ±2350 (N=12일 때). `fitView`가 자동 처리.
- intra-vault 좌표는 current scope의 force-atlas 결과를 centroid 평행이동만 함 → vault 내부 상대 패턴은 보존.

## 검증
- `cd dashboard && ./node_modules/.bin/tsc -b` exit 0
- `cd dashboard && ./node_modules/.bin/vitest run tests/GraphPage.all-vault-scope.test.tsx` 12/12 통과
- `pytest tests/test_api.py -k "all_scope or current_scope_keeps_atlas"` 3/3 통과
- 실제 5 vault 환경에서 `curl /api/vaults/raven-dev/graph?scope=all`: 5 vault centroid가 격자로 분산 (±1300 step), edges 1290, cross-vault edges 0