---
title: Changelog v0.7.144
created: 2026-07-09
updated: 2026-07-09
type: rule
audience: agent
confidence: high
---

# v0.7.144 — all-scope 그래프 모드 제거 (사용자 결정 2026-07-09)

## BLUF
v0.7.122~v0.7.143 11 commit 동안 시도한 all-vault(`?scope=all`) 한 캔버스 그래프 모드 제거. 사용자 보고: "전체볼트 한 캔버스에서 보는건 없애자. 연관 없는 볼트를 같이 보려니 그래프만 자꾸 엉망." → **GraphPage는 current 단일 vault만 표시**.

## 무엇을 했는가

| 파일 | 변경 | 효과 |
|---|---|---|
| `raven/api/server.py` | `scope=all` 분기 (~70줄 격자 배치 로직) 전부 제거. `scope: Literal["current","all"]` Query 파라미터 제거. docstring의 "all nodes: ..." 컨트랙트 정리 | endpoint는 current만 지원. `?scope=all` 호출 시 current로 동작 |
| `dashboard/src/components/GraphCanvas.tsx` | `VaultCentroid` 인터페이스 + `VAULT_HALO_COLORS` + `resolveVaultColor` + `vaultCentroids?` prop + `vaultCentroidsRef` + `vaultTopYRef` + vault 라벨 draw 코드 (~70줄) + vault ring 그리기 코드 + 라벨 drawVaultLabel useEffect dummy 등 모두 제거 | all-scope 시각화 코드 dead. **보존**: `hexToRgba` helper, nodeSize dense 분기 |
| `dashboard/src/routes/GraphPage.tsx` | `graphScope` state + `setGraphScope` + `deriveVaultCentroids` import + `vaultCentroids` 변수 + `<SelectField value={graphScope}>` (전체 vault 토글) + `density="dense"` 분기 + `contextLabel`/`centerTitle` "우주 지도" 텍스트 등 정리 | GraphPage는 current만 + `density="normal"` 고정 + 일반 control UI |
| `dashboard/src/lib/graph/derive.ts` | `VaultCentroid` import + `deriveVaultCentroids` 함수 제거 | client-side centroid 도출 불필요 |
| `dashboard/tests/GraphPage.all-vault-scope.test.tsx` | **파일 삭제** (12개 all-scope contract 테스트) | obsolescent contract 회귀 가드 정리 |
| `tests/test_api.py` | `test_api_vault_graph_all_scope_prefixes_node_ids_by_vault` + `test_api_vault_graph_all_scope_keeps_current_layout_grid_separated` 2개 함수 제거 (55 → 53개 테스트). v0.7.144 contract에 맞게 `current_scope` docstring만 정리 | all-scope 회귀 가드 dead. current-scope 가드는 보존 |

## 왜 했는가
- **사용자 2026-07-09 결정**: "전체볼트 한 캔버스에서 보는건 없애자. 연관 없는 볼트를 같이 보려니 그래프만 자꾸 엉망."
- **근본 원인**: 5+ vault를 한 force-atlas + 격자 배치 캔버스에 다 모아도 의미 있는 시각화 ❌. **연관 없는 데이터 = 노이즈**. vault별 persona/관심사가 다른데 강제 한 그래프 = 사용자에게 무가치.

## 동작
- **GraphPage 진입 → 현재 vault의 그래프만 표시** (예전처럼)
- "전체 vault" 토글 버튼 사라짐 (현재 vault / 전체 vault 선택 UI 없음)
- `?scope=all` 쿼리는 무시됨 (서버는 current 동작)
- vault 색 ring / vault 라벨 모두 사라짐 (single vault에서는 무의미 — 모든 노드가 같은 vault)

## 보존된 것
- `hexToRgba` (다른 ring 효과 재사용 가능)
- `nodeSize` dense/multiplier 로직 (향후 다른 밀도 모드 가능)
- `nodeSize(weight, "dense")` 옵션 (현재 사용처 0이지만 API contract 유지)
- `GraphCanvas`의 `density?: "normal" | "dense"` prop (향후 dense 모드 확장 여지)

## 후속 작업 (별도, 적용 안 함)
- **Layer 2 vault 간 자동 cross-link assist** (사람/에이전트가 후보 제안 → 사람 confirm 필수) — 현재 backlog. 자동 link ❌.
- 자동 후보 추천을 위해 vault 별 graph 검색 + 사람 confirm UI 가 필요. ADR 후보.

## 검증
- tsc -b exit 0
- vitest 137 passed + 1 skipped (이전 149 — 12개 all-scope contract 사라짐)
- pytest tests/test_api.py 55 passed (이전 57 — 2개 all-scope 테스트 사라짐)

## history 기록
- 사용자가 vault 운영 (`~/Raven/raven-dev/content/journal/all-vault-그래프-도입·실패·제거-결정-history-2026-07-09.md`) 발행 완료. 도입 동기/v0.7.122~v0.7.143 흐름/결론/Lessons 정리.
- Raven changelog v0.7.122~v0.7.143 (12개) + 본 v0.7.144 = vault 결정 history에서 인용 가능.
