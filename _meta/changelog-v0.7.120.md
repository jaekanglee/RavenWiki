---
title: Changelog v0.7.120
created: 2026-07-09
updated: 2026-07-09
type: rule
audience: agent
confidence: high
---

# v0.7.120 — GardenPage object-shaped link_candidates 렌더 크래시 수정

## 무엇을 했는가

Dashboard 정원(Garden) 탭에서 API 200 이후 화면이 공백으로 사라지는 렌더 크래시를 수정했다.

### Root cause

`/api/vaults/{name}/garden`의 `orphan[].link_candidates`는 실제로 다음 shape의 객체 배열을 반환한다:

```json
{"slug":"content/...","title":"...","reason":"본문 내 'index' 키워드 포함","score":5}
```

하지만 Dashboard 타입은 `string[]`로 선언되어 있었고, `GardenPage.tsx`가 `{cand}`를 그대로 React child로 렌더링했다.

브라우저 debug log 실제 에러:

```text
Objects are not valid as a React child (found: object with keys {slug, title, reason, score})
```

즉 v0.7.119의 DB schema drift fix로 API 500은 해결됐지만, 그 다음 단계에서 **frontend type/API contract drift**가 드러난 것.

## 변경

| 파일 | 변경 |
|---|---|
| `dashboard/src/lib/api.ts` | `GardenLinkCandidate = string | {slug,title?,reason?,score?}` 추가, `OrphanPage.link_candidates` 타입 갱신 |
| `dashboard/src/routes/GardenPage.tsx` | candidate를 `candSlug/candTitle/candReason`으로 정규화 후 렌더. object/string 모두 호환 |
| `dashboard/tests/GardenPage.link-candidates.test.tsx` | object-shaped candidate가 렌더되는 regression test 추가 |
| `raven/api/server.py` | stale comment `# list of slugs` → `# list of {slug,title,reason,score} objects` |

## 왜 그렇게 했는가 (§5 4 신호)

- **재사용 가능성**: Garden API contract를 Dashboard 타입과 맞춤. 같은 shape를 수동 연결 버튼에도 재사용.
- **인수인계 필요성**: v0.7.119는 backend 500만 해결했고, v0.7.120은 그 다음 React render crash를 분리 기록.
- **scope/provenance 추적**: `find_link_candidates()`는 원래 객체를 반환한다. 프론트 타입이 틀렸던 것.
- **실패/리스크 기록**: "API는 200인데 화면 공백" = React render crash. debug log와 regression test로 고정.

## 검증

- `npx vitest run tests/GardenPage.link-candidates.test.tsx` → 1 passed
- `npx tsc -b --noEmit` → exit 0
- `npm run build` → `vite_exit=0`, 993 modules transformed
- `/api/vaults/{raven-dev,harumoa,homelab,babymoa,hermes-infra}/garden` → all HTTP 200

## 후속

- GardenPage에는 아직 일부 raw `<button>`/inline style이 남아 있음. 이번 범위는 render crash fix만. UI 정리(§13 Button 통일)는 별도 사이클.

---

# v0.7.120-hotfix — LintPage unsafe Quick Fix 제거 + rebuild 결과 contract 보강

## 무엇을 했는가

Lint 탭의 클라이언트-side Quick Fix 버튼을 제거하고, `wiki.db 리빌드` 결과 표시가 실제 build result contract와 어긋나지 않도록 보강했다.

### Root cause

- `#10 frontmatter` Quick Fix는 기존 frontmatter가 있는 문서에도 새 YAML 헤더를 앞에 한 번 더 붙였다.
- `#1 broken link` Quick Fix는 실제 수리라기보다 missing target에 stub 문서를 생성하는 shortcut이었다.
- `POST /api/vaults/{name}/build`의 legacy build path는 Dashboard가 표시하는 `pages` 값을 반환하지 않아, UI가 `undefined pages`를 표시할 수 있었다.

## 변경

| 파일 | 변경 |
|---|---|
| `dashboard/src/routes/LintPage.tsx` | `#1/#10` Quick Fix handlers/buttons 제거. 리빌드 후 lint summary를 `by_check` 포함해 유지 |
| `raven/core/db.py` | legacy build result에 `pages` count 추가, inline build result에 `returncode: 0` 추가 |
| `dashboard/tests/LintPage.no-quickfix.contract.test.ts` | unsafe Quick Fix가 다시 노출되지 않도록 source contract test 추가 |
| `tests/test_db_build_result.py` | build result가 `pages`/`returncode`를 포함하는지 회귀 테스트 추가 |

## 왜 그렇게 했는가 (§5 4 신호)

- **실패/리스크 기록**: frontmatter duplicate write와 stub 노이즈 생성을 Dashboard에서 막음.
- **재사용 가능성**: rebuild action의 API/UI contract를 명확히 해 다른 toolbar action 패턴에도 재사용.
- **scope/provenance 추적**: 실제 자동수리는 `raven.migrate` safe plan/apply 쪽으로 분리해야 함.

## 검증

- `pytest tests/test_db_build_result.py tests/test_migrate.py -q` → 11 passed
- `npx vitest run tests/LintPage.no-quickfix.contract.test.ts` → 2 passed
- `npx tsc -b --noEmit` → exit 0
- `npx vite build` → `vite_exit=0`, built in 2.03s

## 후속

- 진짜 lint repair를 Dashboard에 붙일 경우, 임시 client-side mutation이 아니라 `raven.migrate`의 safe/review/manual plan을 API로 노출한 뒤 dry-run → apply 흐름으로 붙이는 게 맞다.
---

# v0.7.120-hotfix — GraphPage community/cluster UI 다이어트

## 무엇을 했는가

그래프 탭의 기본 UX에서 알고리즘 내부 용어를 걷어내고, 노드 선택 흐름을 단순화했다.

## 변경

| 파일 | 변경 |
|---|---|
| `dashboard/src/routes/GraphPage.tsx` | `커뮤니티별 색상` toggle, `클러스터 필터`, `커뮤니티 #n` chip 제거. `고아` → `연결 없는 문서`, `그래프 다시 계산` → `새로고침` 용어 정리 |
| `dashboard/src/components/GraphCanvas.tsx` | 기본 노드 색상을 community id가 아니라 문서 type 색상으로 고정. hover 시 같은 community 전체 highlight 제거 |
| `dashboard/src/styles/globals.css` | 제거된 community palette toggle CSS 삭제, control grid 3열로 축소 |

## 왜 그렇게 했는가 (§5 4 신호)

- **재사용 가능성**: 그래프 색상 의미를 문서 type 기준으로 고정해 다른 그래프 surface에서도 같은 해석을 재사용.
- **인수인계 필요성**: community/Louvain은 내부 layout·분석 용어이지 사람 기본 UX 용어로 노출하지 않도록 기록.
- **scope/provenance 추적**: 사용자 피드백 — “커뮤니티 색상/클러스터 의미가 이해 안 감”, “오른쪽 패널 복잡함”, “다시 계산 유명무실” 반영.
- **실패/리스크 기록**: hover만으로 오른쪽 패널이 바뀌는 흐름은 시인성을 해치므로 click 선택 중심으로 정리.

## 검증

- `npx tsc -b --pretty false` → exit 0
- `npm test -- --run PageView.local-graph.test.ts PageView.graph-scope.test.tsx` → 2 files / 27 tests passed
- `npm run build` → `build_exit=0`, 993 modules transformed, built in 1.95s

## 후속

- 전체 vault 우주 지도는 별도 API/ID contract가 필요하다. node id는 `{vault}:{slug}` 형태로 충돌 방지 후 진행하는 게 안전하다.

---

# v0.7.120-hotfix — GraphPage 전체 vault 우주 지도

## 무엇을 했는가

그래프 탭에서 현재 보관소 그래프와 모든 registered vault를 합친 all-vault graph를 전환할 수 있게 했다.

## 변경

| 파일 | 변경 |
|---|---|
| `raven/api/server.py` | `GET /api/vaults/{name}/graph?scope=current|all` contract 추가. `scope=all`은 모든 registered vault를 병합하고 node/edge id를 `{vault}:{slug}`로 prefix |
| `dashboard/src/types.ts` | `GraphNode.vault?: string` 추가 |
| `dashboard/src/routes/GraphPage.tsx` | 범위 toggle(`전체 vault` / `현재 vault`) 추가, all scope fetch, node/panel vault chip 표시, all scope 문서 열기 시 node.vault 기준 navigate. all scope는 `GraphCanvas` dense mode로 렌더 |
| `dashboard/src/components/GraphCanvas.tsx` | `density="dense"` 모드 추가. dense에서는 기본 노드 제목 라벨을 숨기고 hover/선택/강조 노드만 라벨 표시, 기본 edge opacity를 낮춤 |
| `raven/api/server.py` | `scope=all` lightweight vault-cluster layout. registered vault들의 centroid를 큰 원형(반경 380, ±500 정규화 유지)에 균등 배치하고, 각 vault 노드를 자기 vault centroid 근처로 평행이동. force-directed는 다시 돌리지 않음 (surgical A'). current scope 좌표 contract는 변경 없음 |
| `dashboard/src/components/GraphCanvas.tsx` | all-vault dense 모드에서 vault halo + centroid 라벨 렌더 추가. vault별 6색 halo 팔레트로 소속을 시각적으로 표시 |
| `dashboard/src/routes/GraphPage.tsx` | `deriveVaultCentroids`로 클라이언트 측 centroid 계산, dense 모드일 때만 GraphCanvas에 vaultCentroids prop 전달 |
| `dashboard/src/styles/globals.css` | `--graph-vault-halo-{1..6}` 토큰 6색 추가 (sky/orange/violet/green/amber/pink) |
| `dashboard/src/components/GraphCanvas.tsx` | v0.6.15 multiscale 잔재 `NebulaNode`/nodeTypes.nebula 제거 (dead code, PLANET 단일). vault halo div에 명시 `pointerEvents: "none"` 추가 — 부모 layer의 `none`이 자식에게 상속 안 되는 xyflow pane 가로채기 회귀 가드 |
| `dashboard/src/components/GraphCanvas.tsx` | v0.7.123+ vault halo/label을 ReactFlow 바깥 형제로 옮기고 `flowToScreenPosition` + `onMove`로 server → screen 좌표 매번 재계산. zoom/pan 따라 halo와 라벨이 노드와 함께 움직임 |
| `dashboard/src/components/GraphCanvas.tsx` | v0.7.123+ dense 모드에서 cross-vault edge(`{vault}:{slug}` source/target prefix가 다른 edge)를 `opacity 0.08`로 강하게 dim. intra-vault edge는 dense base `0.18` 유지 → vault 내부 연결은 약하게 보이고 다른 vault로 가는 라인은 잡음 제거 |
| `dashboard/src/styles/globals.css` | 4열 graph control grid + `graph-vault-chip` 토큰 스타일 추가 |
| `tests/test_api.py` | all-vault graph id collision 방지 API regression test 추가 |
| `dashboard/tests/GraphPage.all-vault-scope.test.tsx` | UI/API contract source test 추가 |
| `dashboard/tests/{GraphCanvas.obsidian-style,PageView.local-graph}.test.ts` | type color 기준 회귀 가드 최신화 |
| `tests/test_api.py` | `test_api_vault_graph_all_scope_groups_nodes_per_vault` (vault centroid 분리 회귀), `test_api_vault_graph_current_scope_keeps_atlas_layout` (current scope 무영향 회귀) 추가 |

## 왜 그렇게 했는가 (§5 4 신호)

- **재사용 가능성**: all-vault graph contract를 `{vault}:{slug}`로 고정해 다른 graph surface에서도 충돌 없는 id 체계를 재사용. dense 렌더 모드는 이후 대형 그래프 surface에도 재사용 가능.
- **인수인계 필요성**: 현재 vault graph와 all-vault universe map의 API/UI scope 차이를 명확히 기록.
- **scope/provenance 추적**: 특정 문서 주변 floating graph는 기존 `/api/vaults/{vault}/graph?scope=current` 흐름을 유지하고, GraphPage만 toggle로 all scope를 사용.
- **실패/리스크 기록**: 여러 vault에 같은 slug가 있는 경우 node id 충돌이 발생할 수 있어 API regression test로 고정. all-vault에서 모든 제목 라벨이 상시 노출되면 시인성이 급락하므로 dense 모드로 기본 noise를 줄임.

## 검증

- `pytest tests/test_api.py::test_api_vault_graph_all_scope_prefixes_node_ids_by_vault tests/test_api.py::test_api_vault_graph_nodes_carry_weight_field -q` → 2 passed
- `pytest tests/test_api.py -q` → 55 passed
- `npx vitest run tests/GraphPage.all-vault-scope.test.tsx tests/PageView.local-graph.test.ts tests/PageView.graph-scope.test.tsx tests/GraphCanvas.obsidian-style.test.ts tests/GraphCanvas.mobile-tap-label.test.ts tests/GraphCanvas.zoom-persistence.test.tsx` → 6 files / 54 tests passed
- `npx tsc -b --pretty false` → exit 0
- `npx vite build` → `vite_exit=0`, 993 modules transformed, built in 1.97s

## 후속

- all-vault scope는 현재 vault별 내부 링크를 prefix해 합치는 read-only union이다. vault 간 wikilink resolution은 별도 product decision/API contract가 필요하면 후속으로 다룬다.

