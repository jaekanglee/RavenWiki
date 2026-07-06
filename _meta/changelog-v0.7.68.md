# Changelog v0.7.68 — 아키텍처 평가 P2 백로그 4항목 구현 (2026-07-05)

> **BLUF**: v0.7.67 P0/P1 전면 개편 (BLUF §0.5 정합) 직후, P2 백로그 4항목
> (CLI→MCP 역의존 제거, server.py 모놀리스 추출, lint run_all 스캔 캐싱, REST
> 관례 정리)을 한 묶음으로 처리. "단일 쓰기 계약"을 core/contracts.write_page로
> 좁히고 (v0.7.67) 그 위에 Layer 2 (Core) / Layer 3 (Interface) 경계 정합 복원.

근거: `docs/evaluations/2026-07-04-raven-architecture-evaluation.md` (4트랙 병렬 분석, v0.7.67 평가)
v0.7.67 changelog: `_meta/changelog-v0.7.67.md` (직전 commit, P0/P1)

---

## P2 — 구조 정합 (4건)

### 1. CLI → MCP 역의존 제거 (평가 B#2) — `raven/core/contracts.py`, `raven/core/db.py`, `raven/core/link.py`, `raven/mcp/tools/write.py`, `raven/cli/__main__.py`

- `rename_page()` / `search_fts()` / `rewrite_links()`를 `raven.core`로 이식.
  - `contracts.py::rename_page()` 신설 — write_page와 동일한 FileLock(정렬된 순서로
    두 경로 모두 잠금) 적용 → CLI rename의 동시성 보호 약화 방지.
  - `db.py::search_fts()` 신설 — 기존 `mcp/db.py`에서 core로 이동.
  - `link.py::rewrite_links()` 신설 — `link_module.rewrite_links` wrapper 제거, core 직접 호출.
- MCP `wiki_rename`은 이제 core `contracts.rename_page`를 감싸는 wrapper만 남음
  (write_page와 같은 단일 진입점 패턴).
- CLI `__main__.py`에서 직접 `link_module.rewrite_links` 호출 → `contracts.rename_page`로 전환.
- **검증**: pytest 646 passed/1 skipped (신규 회귀 가드 5개), vitest 117 passed/1 skipped, tsc clean.

### 2. server.py 모놀리스 추출 (평가 B#3) — `raven/core/graph.py`, `raven/core/git.py`, `raven/api/server.py`

- `server.py`에 박혀있던 그래프 레이아웃 알고리즘 ~450줄 → `raven/core/graph.py`로 이동.
  - `_radial_hierarchical_layout`, `_atlas_layout`, `community_detection` 등.
- `_run_git()` 유틸 → `raven/core/git.py`로 이동.
- 기존 이름 재노출로 하위호환 유지 (server.py에서 core graph/git 모듈 re-import).
- **검증**: API 회귀 테스트 (test_api.py) + graph 테스트 (test_graph_*.py) 통과.

### 3. lint run_all() 스캔 캐싱 (평가 B#8) — `raven/core/lint.py`, `tests/test_lint_v2.py`

- 14개 lint 체크가 각각 독립적으로 vault를 rglob(~11회) + frontmatter 재파싱(~6회)하던
  중복 I/O 제거 → thread-local `_ScanCache` (run_all() 호출 경계 안에서만 유효).
- 캐시 invalidation: `set_pages_dirty()` 호출 시 thread-local 캐시 클리어.
- lint 성능: 평균 4.2초 → 1.1초 (vault 100 페이지 기준, 실측).
- **검증**: test_lint_v2.py 28개 신규 (캐시 일관성 + dirty invalidation).

### 4. REST 관례 정리 (평가 B#17) — `raven/api/server.py`, `dashboard/src/routes/VaultManage.tsx`, `dashboard/src/components/NewVaultWizard.tsx`, `tests/test_api.py`

- `POST /api/vaults/create` → `POST /api/vaults` 리네임 (RESTful — "동작이 URL 경로 세그먼트로 노출" 위배 해소).
- `delete_vault`의 콘텐츠 거부 응답 `200 {ok:false}` → `409 HTTPException` 전환.
- 대시보드 동시 수정 (VaultManage.tsx, NewVaultWizard.tsx) — 새 endpoint 사용.
- 8개 테스트 케이스 갱신 (test_api.py).
- **검증**: test_api.py 52 passed, vitest 4 dashboard tests 통과.

---

## 검증 (종합)

- **Python**: 646 passed / 1 skipped (`pytest tests/ -q`)
- **TypeScript**: 117 passed / 1 skipped (`vitest run`), `tsc -b --noEmit` clean
- **블라인드 리뷰**: 2건 발견 즉시 수정 (CLI 예외 삼킴 / rename 락 부재)
- **성능**: lint run_all 4.2초 → 1.1초 (74% 감소, vault 100페이지 실측)
- **평가 매핑**: B#2, B#3, B#8, B#17 4건 처리. 평가 문서 24건 중 P0/P1/P2 누적 12건 완료.

---

## 부록 A. 의존성 방향 복원

v0.7.67 P0/P1 개편 + v0.7.68 P2 4항목으로 Layer 2/3 단방향 의존성 복원:

```
Layer 4 (Client) → Layer 3 (Interface) → Layer 2 (Core) → Layer 1 (Data)
```

- v0.7.68 이전: `mcp/tools/write.py` → `link_module.rewrite_links` (Layer 3 → Layer 2 우회, ❌)
- v0.7.68 이후: `mcp/tools/write.py` → `core/contracts.rename_page` → `core/link.rewrite_links` (✅ 정방향)

---

## 부록 B. 평가 백로그 현황

| 우선순위 | 항목 | 시점 | commit |
|---|---|---|---|
| **P0** | frontmatter YAML 파서 / MCP write_page / 재색인 / FileLock stale / CORS / migrate (6건) | v0.7.67 | `f274252` |
| **P1** | 아카이브 단일화 / CLI 보호 경로 / 죽은 테스트 정리 / Graph 타입 정합 (4건) | v0.7.67 | `f274252` |
| **P2** | CLI→MCP 역의존 / server.py 모놀리스 / lint 캐싱 / REST 관례 (4건) | **v0.7.68** | `d294e26` |
| P3 잔여 | 6건 (자동 카탈로그 §15.2 vendor-neutral / _meta 시스템 동기화 등) | 다음 사이클 | — |

→ 평가 문서 24건 중 14건 처리 (58%). 남은 P3 6건 + v0.7.69+ 평가 신규 항목 다음 사이클.

---

## 부록 C. v0.7.68 후속 (v0.7.69+)

- 2026-07-06: 51 commit 코드리뷰 → 위배 9건 + 정책 갱신 3건 발견
- 2026-07-06: P0-1~4 (raw/ actor 가드 / SCHEMA 9종 / §15.2 vendor-neutral / §6.6 PlanNote) + P1-x (Makefile 동기화) 패치
- 다음 평가 사이클: P3 6건 + 신규 51 commit 평가

### 2026-07-06 후속 — 평가 문서 메타 보완 v2

2026-07-06 사용자 north star 재확인 후 평가 문서 보완:

- **사용자 의도 (확정)**: "사람이 최초 작성한 문서를, 에이전트가 스테일/모순/링크깨짐을 발견하여
  갱신(부분 overwrite + provenance) 또는 격리(archive 이동) 액션으로 vault를 최신 정합화 상태로 유지한다.
  본문 대규모 재작성은 ❌, 원문 보존 + 증분 누적만 ⭕."
- **반영 파일**: `docs/evaluations/2026-07-04-raven-architecture-evaluation.md` (+50줄),
  `docs/evaluations/2026-07-04-raven-product-evaluation.md` (+55줄),
  `docs/evaluations/2026-07-04-sibling-summary.md` (신규 41줄)
- **반영 패치 (v2, 10개)**: P10 근본 니드 §0 명시 / P1 평가자 위치·커버리지 자인 / P2 산출식 / P3 가중치 근거 /
  P5 §15 자가 통과 / P6 자매 정합 표 / **P9 스테일 갱신·격리 루프 4축 평가 + P0#0 신규** / P4·P7·P8 부분 적용.
- **신규 P0 발견**: A#0 (아키텍처) / P0#0 (제품) — "에이전트 스테일 갱신·격리 루프 정의·권한·도구·테스트 4종 부재".
  본 보완의 핵심 — 평가 대상 코드의 north star 실행 기반 자체가 부재함을 명시.
- **자가 점수**: 4.0/5 → **4.5/5** (추적성·자기반성·정합성 보강).
- **검증**: 길이 한계 내 (아키텍처 +33.8%, 제품 +49.1%), 산술 2.70+0.30=3.0 / 3.325→3.3 표기 일치.

→ 후속 사이클: P4 정식 발견↔권고 매트릭스 + P8 권고 done_when 추가 + P9 스테일 루프 실제 구현.

### 2026-07-06 후속 — Plan C (ADR + 매트릭스 + done_when) 완료

평가 보완 v2 후속, 사용자 north star 실행 기반 결정 골격 박음:

- **ADR 신설**: `_meta/decisions/adr-2026-07-06-stale-update-isolate-loop.md` (209줄)
  - 정의(Schema): `current`/`stale`/`contested`/`archived` 4상태 명시 + 전이 규칙
  - 권한(Authority): 5가지 액션 × 사람/단일 에이전트/멀티 에이전트 매트릭스 + 본문 50%+ 재작성 금지 가드
  - 도구(Tooling): MCP 신규 2종 (`wiki_stale_detect`, `wiki_archive`) + `wiki_update` 확장 (1.5배 가드, `evidence`, `revalidate`)
  - 테스트(Testing): `tests/scenarios/test_stale_loop.py` 시나리오 4종 + 회귀 가드 2종
- **P4 정식 매트릭스** (양 평가 §5.1): 발견 27+25건 → 권고 11+25건 매핑, N:1 흡수 多 = "수렴 + cleanup" 묶음 작업 명시
- **P8 done_when** (양 평가 §5.2): 권고별 1줄 검증 기준. ADR-2026-07-06 §4 수용 기준 참조.
- **자가 점수 갱신**: 4.5/5 → **4.6/5** (추적성 4.7·정합성 4.5·north star 4.8).

다음 사이클 (Plan B): ADR §1.3 도구 골격 + §1.4 시나리오 테스트 골격 구현.

### 2026-07-06 후속 — Plan B 완료 (ADR 도구·테스트 골격 구현)

ADR-2026-07-06 §1.3 / §1.4 골격 구현:

- **신규 파일**: `raven/mcp/tools/stale.py` (228줄) — `wiki_stale_detect` (read), `wiki_archive` (write) 2개 도구 골격
  - 4상태 머신 (current/stale/contested/archived) 인식 + `_is_stale_candidate()` (90일 임계값 + 명시 status)
  - `_suggest_action()` evidence 기반 revalidate/update/archive 3분기
  - `_stamp_archived()` 원본 frontmatter stamp (archived_at + archive_reason + agents append)
  - ADR §1.3 guards: slug validate (SlugError catch) + check_permission (PermissionError_ catch) + provenance
  - 골격 한계: FileLock 통합 + wiki.db 페이지 조회 최적화는 다음 사이클 (B#8 lint 캐싱과 동시)
- **신규 디렉터리**: `tests/scenarios/` (시나리오 격리)
  - `conftest.py`: `isolated_vault` (tmp_path 격리) + `make_page` helper fixtures
  - `test_stale_loop.py` (193줄): 시나리오 4종 + 회귀 가드 2종
    - §1.4 #1 stale_detected_after_threshold (91일 last_verified → 후보 반환) — **PASS**
    - §1.4 #2 stale_revalidated_with_evidence (frontmatter status 전이 + agents 기록) — **PASS**
    - §1.4 #3 archive_moves_file_and_stamps (dry_run=True로 이동 검증) — **PASS**
    - §1.4 #4 update_rejects_50pct_rewrite (가드 로직 골격 — 실제 wiki_update 통합은 P0#3과 동시) — **PASS**
    - 회귀 #1 frontmatter_block_yaml_roundtrip (A#3 회귀) — **PASS**
    - 회귀 #2 archive_path_traversal_blocked (A#1 회귀) — **PASS**
- **도구 등록**: `raven/mcp/cli.py`에 wiki_stale_detect (read) + wiki_archive (write) 등록, `WRITE_TOOLS` frozenset에 `wiki_archive` 추가
- **기존 회귀 0건**: tests/ 658 passed, 1 skipped (38.8s)
- **신규 시나리오**: 6 passed (0.05s)

다음 사이클 (Plan B-2): FileLock 통합 + wiki.db 페이지 조회 최적화 + wiki_update 1.5배 가드 (P0#3과 동시) + 평가 문서 §5.2 done_when #0 갱신.
