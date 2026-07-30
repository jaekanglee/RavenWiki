# Raven Changelog — v0.7.179

## 1. 개요

`docs/issues/`에 `status: open`으로 추적되던 **코드 결함 3건**을 마감했다. 세 건 모두
`docs/evaluations/2026-07-04-raven-architecture-evaluation.md`(B#8, B#17)에서 발견돼
v0.7.68 백로그로 넘어간 잔여이며, v0.7.178 계획(`docs/superpowers/plans/2026-07-29-raven-concept-reinforcement.md` §150)이
"코드 결함이므로 별도 트랙"으로 scope-out한 항목이다.

- **진입점 추가/제거 없음** (4개 고정). clone은 **같은 엔드포인트의 경로 재배치**다.
- **의존성 추가 없음**, vault 데이터 write 없음.

## 2. REST 네이밍 — clone이 동작을 경로 세그먼트로 노출

`docs/issues/vaults-clone-rest-네이밍-위반.md`

v0.7.68이 `POST /api/vaults/create` → `POST /api/vaults`로 고친 것과 **동일한 위반**이
형제 엔드포인트에 남아 있었다.

- `raven/api/server.py`: `POST /api/vaults/clone` → **`POST /api/vaults/{name}/clone`**.
  소스 vault가 body의 `src` 필드에서 경로 파라미터로 이동했고, `VaultClone`에서 `src`를 제거했다.
- 호출부: `dashboard/src/lib/api.ts` `cloneVault()`가 `src`를 경로로 분리해 보낸다
  (호출 시그니처는 그대로라 `VaultManage.tsx`는 변경 없음). `tests/test_api.py` 3곳 갱신.

## 3. 에러 envelope — 전수 분류 후 "진짜 실패"만 전환

`docs/issues/server-전역-에러-envelope-불일치.md`

이슈 문서가 경고한 대로 "전역 통일" 선언을 하지 않았다. `{"ok": False}` 사이트 7개를
전수 조사해 **전환 대상과 보존 대상을 분류**하고, 그 경계를 테스트로 고정했다.

| 위치 | 판정 | 근거 |
|---|---|---|
| `_err()` (구 `:124`) | **삭제** | 저장소 전체 호출자 0개 — dead code |
| `git/status` 실패 | **502 전환** | 진짜 실패. 같은 함수의 인접 에러는 이미 HTTPException |
| `git/diff` 실패 | **502 전환** | 동일 (`git_diff` 내부 불일치 해소) |
| `log/rotate` 거부 | **409 전환** | 500 entries 미만 = 클라이언트 오류 (`?force=true`로 해결) |
| `crosslink` not_found | **보존** | "못 찾았다"는 조회 결과. `test_v0_7_37_crosslink_federation.py`가 계약으로 고정 |
| `debug-log` OSError | **보존** | 전역 에러 보고 채널. 500화하면 에러 보고가 에러를 부른다 |
| `lint` 실패 | **보존** | AGENTS.md §9 graceful degrade가 의도된 계약 |

Dashboard 쪽: `fetchGitStatus`/`fetchGitDiff`가 `!r.ok → null`로 삼켜서 **502 전환만으로는
사용자가 실패 문장을 보지 못했다** (기존에도 `{ok:false,error}`에 `has_workspace`가 없어
"워크스페이스를 연결하세요" 화면으로 흘렀다). 5xx는 서버 `detail`을 던지고, `WorkspacePage`가
`formatApiError()`로 표시하도록 배선했다. 404/400(미연동)은 기존대로 `null`.

기존 가드 갱신: `tests/test_v0_7_67_api_hardening.py`의 A#7 회귀 가드는 rotate 거부를
200으로 단언하고 있었다. **원래 의도(본문이 docstring뿐이라 항상 null이던 데드코드 회귀 방지)를
보존**하면서 거부=409 + force=200 양쪽을 확인하도록 갱신했다 (삭제/skip ❌).

## 4. link 스캔 중복 — content glob 4회 → 1회

`docs/issues/link-module-rglob-3회-잔여.md`

- `raven/core/link.py`: `find_broken` / `find_missing` / `find_broken_intent`에
  keyword-only `pages` 파라미터 추가 (`None` = 기존 동작, 단일 slug 조회 경로 보존).
  세 함수의 중복된 스캔 블록을 `_scan_targets()` 하나로 합쳤다.
- `raven/core/lint.py`: `_link_scan_pages()`가 목록을 만들어 3함수에 주입.
  **`_all_pages()`를 재사용하지 않는다** — 그쪽은 `_meta/` 포함 + `_archive/` 제외라
  스코프가 달라, 재사용하면 성능 개선이 아니라 lint #1-#3 **결과 변경**이 된다.
  대신 `_content_files()`가 원본 glob 1회를 캐시하고 각자 스코프를 파생시킨다.
- 실측: `run_all()` 1회의 `content_root` rglob이 **4회 → 1회**, 같은 content 페이지
  중복 `read_text()` 0회.

## 5. 검증

| 항목 | 결과 |
|---|---|
| `pytest tests/ -q` | 758 passed, 1 skipped (신규 21건) |
| dashboard `npx tsc -b --noEmit` | exit 0 |
| dashboard `npx vitest run` | 174 passed (신규 5건) |

사전 존재 실패는 손대지 않았다: pytest 2건(`test_watcher_fs_contract.py` — `watchfiles`가
`scripts/.venv`에 없음), vitest 5건(jsdom `localStorage` 부재). 둘 다 v0.7.178 이전부터 동일.

신규 테스트:
- `tests/test_v0_7_179_rest_convention.py` — clone 경로 4건 + envelope 전환 3건 + **보존 3건**
  (과잉 전환 방지 가드).
- `tests/test_v0_7_179_link_scan_injection.py` — characterization 6건(변경 전 코드에서 통과) +
  주입 3건 + I/O 감소 증명 2건.
- `dashboard/tests/Workspace.git-error.test.ts` — 5xx 문장 전달 / 404는 `null` 유지.

## 6. 남은 백로그

- **G4 Zettelkasten 프리미티브** — 별도 계획 + ADR. 안정 id가 lint #15
  (`check_slug_title_1to1`, ADR-2026-07-08)을 정면으로 부정하는 재창립급 변경.
- **precondition 토큰의 충돌 한계** — 토큰이 `(st_mtime_ns, st_size)`라 같은 tick +
  같은 byte size 변경은 구별하지 못한다. optimistic check이며 절대적 방지가 아니다.
  완전히 닫으려면 content hash 또는 단조 revision이 필요하다.
- **관계 제거 UI 부재** — MCP `wiki_relation_remove`는 `precondition`을 받지만
  Dashboard에 관계 제거 경로가 없어 실사용되지 않는다.
- **baseline 실패 2종** — `watchfiles` 미설치(pytest 2건), jsdom `localStorage`(vitest 5건).
