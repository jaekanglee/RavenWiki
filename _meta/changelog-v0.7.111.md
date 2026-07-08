# Changelog v0.7.111 — Dashboard Sidebar canonical vault tree

> **BLUF**: Dashboard Sidebar는 vault 실제 폴더 구조를 바꾸지 않고, 화면 표시만 SCHEMA 9종 type 기준 canonical tree로 표준화한다. flat / singular / plural / custom folder 차이를 UI에서 흡수하고, 자동 카탈로그(`content/index`, `content/_index/*`)는 탐색 트리에서 숨긴다.

이전 changelog: `_meta/changelog-v0.7.110.md`

---

## §0 — 묶음 메타

| 항목 | 값 |
|---|---|
| 묶음 | Dashboard Sidebar canonical tree |
| 범위 | v0.7.111 (단일 사이클) |
| 기간 | 2026-07-08 |
| 시작 트리거 | 사용자 명시: "대시보드는 표준화 하는게 좋겠다" |
| 종료 트리거 | tsc 통과 + vitest regression 통과 + vite build 통과 |
| 정책 변경 | 0 — vault 구조/SCHEMA 변경 없음 |
| ADR 동반 | 0 — Dashboard 표시 레이어 변경만 |

## §1 — 무엇을 했나

`dashboard/src/components/Sidebar.tsx`:

| 변경 | 내용 |
|---|---|
| canonical tree helper | `normalizeSidebarTree()` 추가 — 실제 `content/` tree를 page `pageType` 기준으로 grouping |
| type order | `concept → rule → journal → issue → project → tool → person → comparison → query` 고정 |
| catalog hide | `content/index`, `content/_index/*` 자동 카탈로그를 Sidebar에서 숨김 |
| active auto-expand | 물리 slug split 대신 실제 렌더 tree에서 ancestor를 찾아 펼침 — canonical group에서도 active highlight 유지 |
| label | canonical group dir은 `__canonical/concept` 대신 `concept`처럼 표시 |

`dashboard/tests/Sidebar.canonical-tree.test.ts`:

- flat page, `concepts/` 복수형 폴더, `default/` custom 폴더가 섞여도 Sidebar 표시가 `concept`, `rule` 그룹으로 normalize되는지 검증
- `content/index`, `content/_index/*`가 탐색 트리에서 제거되는지 검증

## §2 — 변경 안 한 것

- vault filesystem 구조 변경 없음
- `raven build` / `content/_index/*` 생성 정책 변경 없음
- API `/api/vaults/{name}/tree` contract 변경 없음
- raw/ 표시 방식 변경 없음

## §3 — 검증

- `./node_modules/.bin/tsc -b --pretty false` — 통과
- `./node_modules/.bin/vitest run tests/Sidebar.canonical-tree.test.ts` — 1 test 통과
- `npx vite build` — 통과 (`992 modules`, built in `1.83s`)

## §4 — 4 저장 신호

| 신호 | 충족 |
|---|---|
| 재사용성 | 모든 vault Dashboard 탐색에 적용되는 표시 레이어 규칙 |
| 인수인계 | filesystem은 자유, Dashboard는 canonical이라는 경계 명확화 |
| scope/provenance 추적 | `_index` 혼란과 folder 구조 차이 관찰에서 나온 UX 결정 기록 |
| 실패/리스크 기록 | 실제 vault를 마이그레이션하지 않고 UI에서만 흡수했다는 안전 경계 기록 |
