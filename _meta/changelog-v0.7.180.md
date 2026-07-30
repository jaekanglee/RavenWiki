# Raven Changelog — v0.7.180

## 1. 개요

v0.7.179가 "남은 백로그"로 남긴 두 항목을 마감했다.

- **precondition 토큰의 충돌 한계** — v0.7.178이 스스로 "optimistic check, 절대적 방지 아님"으로
  자백한 구멍을 닫았다.
- **baseline 테스트 실패 7건** — pytest 2건 + vitest 5건. 이전 세션이 "환경 한계"로 뭉뚱그려
  baseline 처리했으나, 실제로는 **테스트 자체의 결함 3종 + 선언된 의존성 미설치**였다.

의존성 추가 없음. 진입점 변경 없음. vault 데이터 write 없음.

## 2. precondition 토큰 — stat 파생에서 내용 파생으로

`raven/core/contracts.py` `precondition_for_path()`

v0.7.178 토큰은 `(st_mtime_ns, st_size)`였다. 그래서 **같은 mtime tick 안에서 바이트 수까지
같은** 개입 write는 토큰을 바꾸지 못해 검사를 통과했고, 그 편집을 조용히 덮어썼다.
v0.7.180은 파일 바이트의 sha256(앞 32자)을 쓴다.

부수적으로 의미가 두 곳에서 달라졌고, 둘 다 개선 방향이다:

- `touch`처럼 **내용은 그대로인데 mtime만 바뀐** 경우는 더 이상 충돌이 아니다.
- 남이 저장했지만 결과 바이트가 내가 읽은 것과 동일하면(같은 편집을 두 번) 충돌이 아니라 통과다.

충돌 재현은 타이밍 운에 기대지 않는다. `os.utime(ns=...)`로 mtime을 원래 값으로 되돌려
`(mtime_ns, size)`가 완전히 동일한 상태를 결정론적으로 만든 뒤 검사한다.

기존 계약은 그대로다: 토큰 없음 = 검사 생략(하위 호환), `""` = 부재 단언, stale = `stale_precondition` + 409.

`tests/test_v0_7_178_write_precondition.py`의 `stat_token()` 헬퍼는 옛 공식을 재유도하고 있었다.
그대로 두면 **포맷 불일치 덕에 통과하는 tautology**가 되므로 `content_token()`으로 갱신했다
(삭제/skip ❌ — 7건 모두 의미를 유지한 채 통과).

## 3. baseline 실패 7건 — 실제 원인

| 실패 | 진짜 원인 | 조치 |
|---|---|---|
| vitest `Folder-hover-menu`, `GraphPage.detail-panel` | jsdom 25.0.1은 직접 쓰면 `localStorage`를 주지만 **vitest 2.1.9의 jsdom environment는 노출하지 않는다** (직접 JSDOM probe로 확인). `api.ts:138` `getActiveHostId`가 무조건 호출 | `tests/setup.ts`에 `localStorage` stub 추가 (기존 `matchMedia`/`scrollTo` stub 선례와 동일한 자리). `beforeEach`로 suite 간 누수 차단 |
| vitest `PageView.graph-scope` | `vi.mock`이 모듈 전체를 대체하면서 `apiFetch`를 빼먹음 → `PageView.tsx:318` 그래프 fetch에서 렌더가 죽음 | `importOriginal` 스프레드로 실제 `apiFetch`를 남기고 단언 대상만 교체 |
| vitest `useHybridSearch` 2건 (각 3.0초) | **별도 결함이 아니었다.** `fetchHybridSearch` → `getActiveHostId` → `localStorage` throw를 훅의 `.catch(() => {})`가 삼켜 `waitFor`가 3초 타임아웃을 태웠다 | 위 stub으로 동시 해소. 537ms에 3건 통과 |
| pytest `test_watcher_fs_contract.py` 2건 | `watchfiles`가 `requirements.txt:13`에 이미 선언돼 있는데 `scripts/.venv`에만 없었다 | `pip install -r requirements.txt`. 부수적으로 httpx 0.27.2 → 0.28.1 — 이것도 `requirements.txt:7` `httpx>=0.28` **위반 상태를 정합화**한 것이며 신규 의존성이 아니다 |

`tests/setup.ts`는 `beforeEach`를 쓰면서 import가 없어 `tsc -b`가 TS2304로 깨졌다 (vitest는
`globals: true`로 통과, 빌드는 실패). import를 추가해 두 경로를 함께 맞췄다.

## 4. 검증

| 항목 | 결과 |
|---|---|
| `pytest tests/ -q` | 769 passed, 1 skipped, **0 failed** |
| dashboard `npx tsc -b --noEmit` | exit 0 |
| dashboard `npm run build` | 성공 |
| dashboard `npx vitest run` | 38 files, 179 passed, 1 skipped, **0 failed** |

v0.7.179까지 남아 있던 baseline 실패 7건이 모두 사라졌다.

실서버(127.0.0.1:8803) curl QA 6항목:

1. 토큰 형태 `sha256-687270f2...` 확인
2. fresh 토큰 → 200
3. stale 토큰 → 409, 개입 편집 보존, 거부된 내용 파일에 없음
4. `touch`만 한 경우 토큰 불변 (내용 파생 증거)
5. **`(mtime_ns, size)`가 완전히 동일한 내용 변경 → 409** (v0.7.178이 놓쳤던 케이스)
6. 토큰 없는 legacy write → 200

신규 테스트: `tests/test_v0_7_180_precondition_collision.py` 9건 — 충돌 검출 2건,
기존 계약 보존 6건(과잉 변경 방지), 토큰이 파일 바이트 파생인지 독립 확인 1건.

## 5. 남은 백로그

- **G4 Zettelkasten 프리미티브** — 별도 계획 + ADR. 안정 id가 lint #15
  (`check_slug_title_1to1`, ADR-2026-07-08)을 정면으로 부정하는 재창립급 변경.
- **관계 제거 UI 부재** — MCP `wiki_relation_remove`는 `precondition`을 받지만
  Dashboard에 관계 제거 경로가 없어 그 파라미터가 실사용되지 않는다.
