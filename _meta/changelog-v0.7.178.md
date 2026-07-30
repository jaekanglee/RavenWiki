# Raven Changelog — v0.7.178

## 1. 개요

- **작성일**: 2026-07-30
- **주요 내용**: 동시 편집 lost update 방지(precondition 토큰), 임베딩 열화·보안 태세 정직화, 선언(문서)과 실제(코드)의 재정합 + 재발 방지 가드 테스트
- **계획 문서**: `docs/superpowers/plans/2026-07-29-raven-concept-reinforcement.md` (Theme A / B / C). G4(Zettelkasten 프리미티브)는 계획대로 별도 트랙으로 분리.

---

## 2. Theme A — 동시 편집 안전성

`FileLock`은 write 순간만 직렬화하므로, 문서를 읽고 고치는 사이에 다른 표면이 저장하면 그 편집이 조용히 사라졌다(lost update). precondition 토큰으로 이를 거부한다.

- **`raven/core/contracts.py`**: `precondition_for_path()` / `page_precondition()` 추가. `write_page(precondition=...)`가 락 안에서 현재 토큰과 비교해 어긋나면 `WriteResult(ok=False, error="stale_precondition")`으로 아무것도 쓰지 않고 반환. 토큰은 `(st_mtime_ns, st_size)` 파생이며, `None`이면 검사를 건너뛰어 기존 호출자는 영향 없음. `""`은 "아직 없어야 한다"는 주장.
  - 이 한 곳이 API/CLI/MCP 3표면의 유일한 write 관문이므로 검사도 한 곳에만 넣었다.
- **`raven/api/server.py`**: `GET /pages/{slug}` 응답에 `precondition` 추가. `PUT /pages/{slug}`가 `precondition`을 받고 stale이면 **409**. 성공 응답에도 다음 토큰을 실어 연속 편집이 가능하다. `_with_lock_holder()`로 MCP와 **같은 필드명**(`_lock_holder` / `_advisory_conflict`)으로 락 보유자를 노출 — 기존에는 MCP만 충돌을 알렸다.
- **리뷰(momus) 지적 반영 — 토큰을 실제로 보내지 않는 표면 4곳 보강**: `write_page`에 검사를 넣어도 호출자가 토큰을 주지 않으면 그 표면은 무방비다.
  - `raven/mcp/tools/write.py` `wiki_update(precondition=...)` 신설 + `write_page`로 전달 → 에이전트 간 lost update도 거부. 회귀 가드 `tests/test_v0_7_178_mcp_precondition.py` 3건.
  - Dashboard의 살아있는 read-modify-write 3경로에 토큰 전달: `PropertiesPanel`(type/tag/alias 즉시 저장), `PageView`(issue 상태 변경), `GardenPage`(고립 문서 링크 연결).
  - `EditButton.tsx`는 렌더되는 곳이 없는 dead code라 대상에서 제외 (grep 결과 주석 2건만 참조).
- **리뷰 라운드 2 반영 — 피드백·관계 write 경로 5종 보강**: 피드백 추가/수정/삭제와 관계 추가/제거는 모두 페이지를 읽어 본문·frontmatter를 재구성해 다시 쓰므로 본문 편집과 동일한 lost update 위험이 있었다.
  - `raven/api/server.py`: `FeedbackPayload` / `FeedbackUpdatePayload` / `RelationAddPayload`에 `precondition` 추가, `delete_page_feedback`는 query param으로 수용. 4개 경로 모두 stale이면 **409**.
  - `raven/mcp/tools/write.py`: `wiki_relation_add` / `wiki_relation_remove`에 `precondition` 추가 + `write_page`로 전달.
  - Dashboard: `sendPageFeedback` / `updatePageFeedback` / `deletePageFeedback` / `addRelation`이 토큰을 전달하고, 실패 시 상태코드가 아니라 서버 `detail` 문장을 던진다. 호출부는 `PageView`(피드백 3종)와 `PropertiesPanel`(관계 추가).
  - 회귀 가드: `tests/test_v0_7_178_feedback_relation_precondition.py` 8건, `dashboard/tests/Feedback-relation.precondition.test.ts` 6건.
- **리뷰 라운드 3 반영 — MCP 읽기 표면이 토큰을 내려준다**: write에 `precondition`을 받아도 에이전트가 토큰을 **얻을 경로**가 없으면 그 파라미터는 실사용 불가였다.
  - `raven/mcp/db.py` `get_page()`가 `precondition`을 함께 반환. 값은 **wiki.db가 아니라 markdown 파일**에서 뽑는다 — DB는 재생성 가능한 캐시라 파일보다 뒤처질 수 있고, precondition은 "실제 파일이 밀렸는가"를 물어야 하기 때문.
  - `raven/core/templates/agent/TOOLS.md`의 `wiki_get_page` / `wiki_update` 서명을 실제와 맞춤 (에이전트가 이 흐름을 알 수 있도록).
  - 회귀 가드: `tests/test_v0_7_178_mcp_read_precondition.py` 4건 (읽기 노출 / round-trip 수용 / 남이 쓰면 stale / DB 재빌드 없이도 파일 변경 추적).
- **Dashboard**: `updatePage()`가 `precondition`을 전달하고, 실패 시 상태코드가 아니라 서버가 준 `detail` 문장을 던진다. `InlineMarkdownEditor`가 `precondition` prop을 받아 저장 시 함께 보내고, 409 문장을 토스트로 띄운다. `PageView`가 `GET` 응답의 토큰을 내려준다.

## 3. Theme B — 열화 / 태세 정직화

- **`raven/core/hybrid_search.py`**: `embedding_health()` 추가. `sentence-transformers` 부재 시 `LocalEmbeddingEngine`은 sha256 mock 벡터로 fallback하면서도 랭킹된 결과를 정상처럼 반환했다 — 이제 `degraded` / `reason`으로 그 사실을 드러낸다.
- **`raven/api/server.py`**: `/hybrid-search`와 `/rag/query` 응답에 `embedding` 블록 부착. `/api/system/info`가 하드코딩 `"allow_all_cors": True`와 env 기본값 `bind_host` 대신 **실제 계산값**(`_allow_all_cors`, `BOUND_HOST`)을 보고한다 — 보안 태세를 알려주는 유일한 endpoint가 태세를 잘못 보고하고 있었다.
- **`raven/api/main.py` / `raven/desktop/runtime.py`**: 실제로 바인딩한 호스트/포트를 `RAVEN_BOUND_HOST` / `RAVEN_BOUND_PORT`로 전달.
- **동일 결함 1건 추가 발견·수정 (실표면 QA에서)**: `system_info`의 `port`도 `bind_host`와 같은 병으로 env 기본값을 보고했다 — `:8799`로 구동한 서버가 `8765`를 보고. 근본 원인은 `raven/api/__init__.py`의 `from .server import app` 때문에 이 모듈이 `main()`이 `RAVEN_BOUND_*`를 set하기 **전에** import된다는 것이었다(import 시점 스냅샷은 기동 값을 항상 놓친다). `bound_host()` / `bound_port()` **요청 시점 조회**로 교체.
- **Dashboard**: `DegradedNotice` 공통 컴포넌트 신설(`components/ui/`, AGENTS.md §13.1 재사용 원칙). `SearchPage`가 검색/RAG 표면 위에 열화 경고를 1회 표시.

## 4. Theme C — 선언-실제 재정합

- **버전 SOT 단일화**: `raven/__init__.py __version__ = "0.7.178"`을 FastAPI `app.version`이 직접 읽는다(기존 하드코딩 `"0.2.0"`). README 상태줄도 정합. 이전에는 서로 모르는 버전 문자열이 4종(`0.7.67` / `0.2.0` / README `v0.7.65` / 최신 changelog `v0.7.177`)이었고 `__version__` 소비처는 0건이었다.
- **README 카운트 정정**: endpoint 26 → **65**, MCP 9 tools + 5 resources → **23 + 4**, lint 14 → **22**, CLI 서브커맨드 그룹 12 → **11**.
- **가드 테스트 신설** (`tests/test_v0_7_178_doc_count_guards.py`): 위 카운트를 런타임/소스에서 파생해 README 표기와 비교한다. `CHECK_REGISTRY` 선례(`tests/test_lint_check_registry.py`)는 *등록 누락*만 잡고 *문서 표기*는 못 잡았다 — 그 빈틈을 막는다.

---

## 5. 검증

| 항목 | 결과 |
|---|---|
| `pytest tests/ -q` | 737 passed, 1 skipped / 사전 존재 실패 2건(`test_watcher_fs_contract.py` — `watchfiles` 미설치)은 이번 변경과 무관 |
| `npx vitest run` (dashboard) | 신규 18 tests 통과 / 사전 존재 실패 5건(jsdom `localStorage` 한계)은 이번 변경과 무관 |
| `npx tsc -b --noEmit` + `npm run build` | clean |
| 실표면 QA | `curl -i`로 GET 토큰 → 낡은 토큰 PUT **409** + 먼저 저장한 내용 보존, `/api/system/info` 실제값 보고, `/hybrid-search` degraded 노출 확인 |

## 6. 하지 않은 것 (계획 §6 non-goal 보존)

5번째 진입점 ❌ / auth·ACL·multi-tenant ❌ / CRDT·자동 merge·실시간 협업 ❌ / LLM 모듈 물리 이동·로컬 모델 번들 ❌ / changelog 원문 수정 ❌ / `PROJECT-WORKFLOW.md` 신설 ❌ / 사용자 vault 데이터 write ❌
