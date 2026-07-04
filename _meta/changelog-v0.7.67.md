# Changelog v0.7.67 — 아키텍처 평가 기반 전면 개편 (2026-07-05)

> **BLUF**: 아키텍처 전수 평가(4트랙 병렬 분석)에서 나온 P0 9건 + P1 다수를 수정.
> 핵심은 "단일 쓰기 계약" 원칙을 MCP까지 실제로 관철시킨 것 — MCP 쓰기 경로의
> path traversal 취약점, frontmatter 블록 YAML 데이터 손실, MCP 쓰기 후 재색인
> 영구 no-op을 한 번에 해소. 그 외 락 stale 회수, migrate 링크 강등 버그, CORS
> 전면 개방, 아카이브/버전 SOT 정리, 프론트 Graph 타입 드리프트까지 정리.

평가 문서: `docs/evaluations/2026-07-04-raven-architecture-evaluation.md` (4트랙 분석/근거/전체 발견 목록)

---

## P0 — 데이터 안전 / 보안

1. **frontmatter 블록 YAML 지원** (`raven/core/frontmatter.py`)
   - 커스텀 라인 파서가 들여쓴 줄을 전부 skip해 `tags:\n  - a\n  - b` 같은
     Obsidian 표준 블록 리스트와 `agents:` 이력을 조용히 삭제했다 (실행 재현됨).
   - PyYAML 기반 파싱으로 교체 (레거시 비-YAML 블록은 라인 파서로 폴백).
     render는 필요한 경우만 따옴표 처리해 YAML 안전성 확보.

2. **MCP `wiki_update`를 `contracts.write_page`로 전환** (`raven/mcp/tools/write.py`,
   `raven/core/contracts.py`)
   - 이전엔 slug 검증 없이 `vault / Path(slug)`를 그대로 조합해 `../`나 절대경로로
     **vault 밖에 파일을 쓸 수 있었다** (path traversal).
   - `frontmatter_data` 전달 시 기존 메타를 병합이 아니라 **대체**해 `created`/
     `tags`가 소실됐다. `.vault.json`의 `agents` 허용목록도 우회됐다.
   - provenance가 스칼라 `actor:` 키(CLI/API는 `agents:` 리스트)라 표면 간
     불일치. 이제 slug 검증 + FileLock + frontmatter merge + `agents:` 이력
     append까지 CLI/API와 동일한 계약을 탄다. `contracts.write_page`에
     `extra_meta`/`append_log` kwarg 신설 (MCP 전용 관심사 수용).
   - `core/log.py` 액션 화이트리스트에 `rename` 추가 (MCP가 쓰는데 CLI 경로는
     거부하던 비대칭 해소).

3. **MCP 재색인 수리 + `db.connect()` stale 검사 + 폴백 스키마 정합**
   (`raven/core/db.py`, `raven/mcp/tools/write.py`)
   - `_rebuild_db`가 `<vault>/scripts/build_db.py`를 찾았는데, 일반 사용자
     vault(`~/Raven/<name>/`)엔 그 파일이 없어 **MCP 쓰기 후 재색인이 영구
     no-op**이었다 (wiki_update는 재색인 시도조차 안 했음). 이제
     `core.db.build_db`를 직접 호출 — MCP로 쓴 페이지가 즉시 `wiki_search`에
     노출된다.
   - `db.connect()`가 DB 존재 여부만 보고 stale은 무시하던 것을 `garden.db_is_stale()`
     검사로 보강.
   - `_inline_build`(설치 패키지 폴백)가 `pages(slug,title,type,path,content)`뿐인
     구 스키마라 `pages_fts`/`links`/`created`/`updated`/`confidence`가 없어
     index_builder·garden 쿼리가 실패했다 — `scripts/build_db.py`의 v2.4 스키마를
     동일하게 이식.
   - 빌드 unlink~재생성 구간에 `lock_for_file` 적용 (동시 빌드 레이스 방지).

4. **락 stale 자동 회수 + 원자적 쓰기** (`raven/core/lock.py`)
   - `FileLock`에 소유자(PID+시각) 기록이 없어 락 보유 프로세스가 죽으면
     `.mcp/locks/`가 영구 고착되고, 이후 해당 파일 write가 timeout 후 실패했다
     (수동 삭제 전까지 복구 불가). 이제 죽은 PID이거나 `stale_after`(기본 60초)를
     넘긴 락은 자동 강탈.
   - 신규 `atomic_write_text()` (tmp+`os.replace`) — 페이지 쓰기(contracts.py)와
     log.md append 양쪽에 적용. 크래시 시 파일이 반쪽으로 잘리는 대신 구/신
     내용 중 하나가 온전히 남는다.

5. **CORS 축소 + `/log/rotate` 데드코드 복원** (`raven/api/server.py`)
   - `allow_origins=["*"]` + 무인증 조합이 127.0.0.1 바인딩을 무력화 — 브라우저에
     열린 임의의 웹페이지가 cross-origin으로 `DELETE /api/vaults/{name}?force=true`
     (rmtree) 같은 파괴적 엔드포인트를 호출할 수 있었다. 로컬 대시보드가 실제로
     쓰는 origin(`PORT_DASHBOARD`/`PORT_API`)만 허용.
   - `POST /log/rotate` 본문이 docstring뿐이라 항상 null을 반환 — 실제 구현은
     다른 함수(`post_debug_log`)의 `return` 뒤 데드코드로 잘못 붙어 있었다
     (2650줄 server.py 편집 사고). 원래 구현을 복원.

6. **migrate `apply_broken_to_missing` 수리** (`raven/migrate.py`)
   - `--apply`가 broken 링크만 골라내지 않고 페이지 내 intent-suffix 없는
     위키링크 **전부**를 `?` placeholder로 강등했다. 판별에 쓰인
     `_has_intent_suffix`는 루프가 즉시 종료돼 **항상 False를 반환하는 죽은
     로직**이었다 (`risk="safe"`로 자동 실행되던 경로). 이제 lint #1이 실제로
     지목한 target 하나만 강등한다 (`Fix.target` 필드 신설).

## P1 — 구조 정합

7. **아카이브 4벌 → `core.archive.archive_page()` 단일화**
   (`raven/core/archive.py`, `raven/cli/__main__.py`, `raven/api/server.py`,
   `raven/mcp/tools/write.py`)
   - CLI/API가 동일 레시피를 줄 단위로 복붙하고 있었고, MCP `wiki_delete`는
     **평면 경로**(`_archive/<stem>-<ts>.md`)를 써서 중첩 페이지 복원 시
     잘못된 위치(vault 루트)로 복원되는 버그가 있었다. 세 표면 모두
     `archive_page()`(중첩 경로 보존 + 충돌 카운터 + log append)를 호출하도록
     통일 — MCP로 아카이브한 중첩 페이지도 이제 정확히 복원된다.
   - 이 작업 중 CLI gardening REPL의 `archive_module.archive_page(v, slug)`
     호출이 애초에 **존재하지 않는 함수를 호출하는 AttributeError 버그**였음을
     발견 — 함수 신설로 자동 해소.

8. **보호 경로 표면 통일 + `_note_create` 계약 편입** (`raven/cli/__main__.py`)
   - `raven page new raw/x`가 CLI에서만 성공하고 API/MCP는 거부하던 비일관을
     해소 (raw/ 선제 차단; `_meta/` 직접 쓰기는 기존 CLI 능력으로 의도적 유지 —
     회귀 테스트로 고정된 기능이라 보존).
   - `note decision/concept/...` 트리거 헬퍼가 `contracts.write_page`를 거치지
     않는 5번째 쓰기 경로였고, `--project`가 `harumoa|homeauto|resume|design-spec`
     4개로 하드코딩돼 있었다 (범용 CLI에 개인 프로젝트명). 계약 편입 + 자유
     슬러그로 전환.

9. **죽은 테스트 스위트 정리 + deploy/Makefile 정합** (사용자 승인 하에 삭제)
   - `raven/mcp/tests/`(37 skip + `tests/`와 동시 수집 시 `mcp` 네임스페이스
     충돌) 삭제 — `tests/test_mcp_*.py`가 이미 동등/우월한 커버리지 제공.
   - `scripts/tests/test_build_db.py`(구 스키마 대상, 8개 FAILED) 삭제.
   - `deploy/systemd/wiki-mcp.service`의 `-m mcp.cli`(v0.6.0 네임스페이스
     변경 전 경로 — 현재 코드로 기동 불가) → `-m raven.mcp.cli` 수정,
     포트도 API와 충돌하던 8765 → MCP 기본 포트 8766으로 정정.
   - `Makefile` 헤더 "Docker 우선"이 README의 v0.7.55+ "Docker deprecated"
     정책과 정반대였던 것 정정.

10. **`/build` 이중 lint 제거** (`raven/api/server.py`)
    - `build_db()`가 내부에서 이미 lint를 실행해 `result["lint"]`에 담는데,
      `/build` 엔드포인트가 그 결과를 버리고 legacy `run_lint()`(subprocess +
      run_all 재실행)를 또 호출해 빌드 1회에 lint가 2~3회 돌았다.

11. **버전 SOT + MCP 기본 vault 해석 잔재 수리**
    - `raven/__init__.py`의 `__version__`이 `0.5.7`로 20개 마이너 방치돼 있던
      것을 최신으로 갱신, `raven/mcp/__init__.py`는 별도 버전 대신 top-level에
      연결.
    - `mcp/db.py`/`mcp/tools/__init__.py`의 `_default_vault()`가 무조건
      `raven` 패키지 디렉터리를 반환하던 것(단일-vault 시절 잔재, 잠복 결함)을
      레지스트리의 `resolve_active_vault()`를 우선 시도하도록 수정 (레거시
      폴백은 유지).
    - `make typecheck`가 AGENTS.md에서 지시되지만 실제로 없던 타깃을 신설
      (`cd dashboard && tsc -b --noEmit`).

12. **프론트엔드: Graph 타입 드리프트 수리 + 죽은 의존성 제거**
    (`dashboard/src/types.ts`, `GraphCanvas.tsx`, `PageView.tsx`, `GraphPage.tsx`,
    `FloatingGraphPanel.tsx`)
    - `types.ts`가 `GraphNode.slug`/`GraphEdge.source_slug`/`target_slug`를
      필수로 선언했으나 백엔드 실응답은 `id`/`source`/`target` — 타입이 현실과
      반대였고, 소비처 전역에 `(n as any).id ?? n.slug` 캐스트가 산재했다.
      타입을 실제 응답에 맞게 교정하고 모든 `as any` 봉합 제거.
    - `zustand`(import 0건), `minisearch` + `src/lib/search.ts`(자체
      "@deprecated 삭제 예정" 표기, 소비처 0건) 제거.
    - 테스트 fixture(`PageView.local-graph.test.ts`, `PageView.graph-scope.test.tsx`)도
      실제 API 형태로 갱신.

## 문서 동기화

- `docs/architecture.md` — 제거된 `_meta/system/`(SCHEMA/RULES/AGENTS) 참조를
  현행 `_meta/agents/`(SCHEMA/PROJECT-WORKFLOW)로 정정.
- `AGENTS.md` §14 — "`_meta/raven-architecture.md` 링크 깨짐" 자기모순 주석
  제거(파일 존재 확인됨), "`docs/` 신설 불필요" 선언을 v0.7.0+ 현실(architecture.md/
  vault-patterns.md/evaluations/)에 맞게 정정.
- 고아 디렉터리 `templates/ai-agent-wiki-1.0.0/`(코드 참조 0건, 실제 템플릿은
  `raven/core/templates/`) 삭제 (사용자 승인).

## 검증

- 전체 Python 테스트: **645 passed, 1 skipped** (신규 회귀 가드 41개 추가 —
  frontmatter 블록 YAML, MCP 쓰기 계약 전환, 락 stale 회수, 원자적 쓰기,
  migrate 링크 강등, CLI 보호 경로/노트 계약, API CORS/rotate)
- 대시보드: `tsc -b --noEmit` clean, vitest **117 passed, 1 skipped**
- `make typecheck` 신설 타깃 동작 확인

## 남은 백로그 (의도적 유예)

- **표면 간 역의존 잔존**: CLI가 rename(`wiki_rename`)·검색(`search_fts`) 로직을
  얻으려 `raven.mcp`를 import하는 지점 2곳. 복잡한 비즈니스 로직(링크 재작성,
  FTS 질의)을 core로 끌어내리는 작업이라 리스크 대비 이번 배치 범위 밖으로 유예.
- **server.py 모놀리스 추출**: 그래프 레이아웃 알고리즘(~450줄), git 연산을
  core 모듈로 추출하는 작업 — 순수 구조 개선이라 우선순위 낮게 유예.
- **lint 스캔 캐싱**: `run_all` 체크당 파일 재스캔 — 성능 이슈이나 정확성
  버그는 아니라 유예.
- **REST 관례 정리**(`POST /vaults/create` 네이밍, 에러 응답 envelope 통일,
  vault delete 거부의 200→409화): 대시보드 소비 코드와 동시 변경이 필요해
  리스크 대비 낮은 가치로 유예.
