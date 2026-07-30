---
title: Raven 개념 보강 계획 — 선언과 실제의 재정합
created: 2026-07-29
type: rule
audience: agent
confidence: high
status: current
tags: [plan, concept, north-star, write-safety, sot-drift]
---

# Raven 개념 보강 계획 — 선언과 실제의 재정합

> **BLUF**: Raven의 개념적 문제는 기능 부재가 아니라 **코드가 문서를 앞질러 갔고, 그 문서가 SOT로 선언되어 있다는 것**이다. 보강은 A(동시 편집 안전성) → B(Layer 경계 + 열화 정직화) → C(선언-실제 재정합 번들) 순서로 진행하고, Zettelkasten 프리미티브(G4)는 재창립급 변경이므로 **별도 계획으로 분리**한다.

이 계획은 `ulw-plan` (Prometheus) 세션 산출물이다. 실행은 별도 워커 세션에서 시작한다 (`$start-work` 등). 이 문서 자체는 제품 코드를 변경하지 않았다.

- 근거 노트패드: `/var/folders/h8/6sh9zmx13gd4_93tbh_3179h0000gn/T/ulw-20260730-020514.XXXXXX.md.8WN6PQN3Kj` (193줄, 갭 인벤토리 G1~G8 + 결정 갈림길 R1~R10)
- 모든 주장은 2026-07-29 세션에서 실측한 `file:line` 근거를 가진다.

---

## 1. 왜 이 순서인가 (우선순위 논거)

| 순위 | 테마 | 무엇을 잃고 있나 | 근거 요약 |
|---|---|---|---|
| **A** | 동시 편집 안전성 | **데이터** (lost update) | precondition 개념 저장소 전체 0건 + v0.7.176~177이 원격 동시 접속을 정면으로 개방 |
| **B** | Layer 경계 + 열화 정직화 | **결과 신뢰** (무의미한 벡터로 랭킹) | `hybrid_search.py:56-57` mock embedding fallback이 조용히 성공처럼 보임 |
| **C** | 선언-실제 재정합 | **문서 신뢰** (SOT가 거짓) | 버전 문자열 4개 불일치, endpoint 26 vs 65, MCP 9 vs 23, lint 14 vs 22 |
| 분리 | G4 Zettelkasten 프리미티브 | **정체성** | 안정 id 도입이 lint #15(ADR-2026-07-08)와 정면 충돌 = 재창립 |

**A를 앞에 둔 이유**: 데이터 손실은 문서 부정확보다 무겁다. C가 더 싸고 눈에 잘 보이지만, C부터 하면 기분은 좋아지고 제품은 그대로다.

**C를 앞으로 당기는 반론도 유효했다** (기록): C의 실체가 "자동 파생 + 가드"이므로 먼저 깔면 A/B가 새 drift를 만들지 않는다. 그래도 A를 택한 근거가 위와 같으며, C 단계에서 A/B가 바꾼 카운트를 손으로 두 번 고치지 않도록 **A/B의 새 응답 필드·엔드포인트는 C의 파생 대상 목록에 미리 등록**해 상쇄한다.

---

## 2. Theme A — 동시 편집 안전성 (lost update 방지 + 충돌 표면화)

### A.0 North Star 연결

"markdown = SoT, 사람 1차"가 성립하려면 **사람이 쓴 글이 조용히 사라지지 않아야** 한다. 현재는 사라질 수 있다.

### A.1 실측 상태

- `contracts.write_page`가 **모든 write 표면의 유일한 seam**이다 (R7):
  - API: `raven/api/server.py:1797, :1877, :1969, :2049, :2120`
  - CLI: `raven/cli/__main__.py:448, :633, :1542, :1599`
  - MCP: `raven/mcp/tools/write.py:501, :1203, :1391`
- 그 seam은 이미 안전하다: `raven/core/contracts.py:179` `with lock_for_file(...)`, `:269` `atomic_write_text(fp, rendered)`, `raven/core/lock.py:130` (tmp + `os.replace`).
  → **AGENTS.md §8 "모든 write가 core 단일 contract" 는 실제로 성립한다. 이건 갭이 아니다.**
- 남은 갭 2개:
  1. **lost update**: `FileLock`은 write 순간만 직렬화한다. read-modify-write 사이의 덮어쓰기를 막는 수단이 없다. `rg "if_match|If-Match|etag|ETag|expected_updated|expected_mtime|base_version|precondition|412" raven/ dashboard/src` → **0건**.
  2. **충돌 가시성 비대칭**: MCP write는 `_lock_holder` / `_advisory_conflict`를 응답에 붙인다 (`raven/mcp/tools/write.py:209-257`, `:430` `lock_conflict`). REST `update_page` 응답은 `{ok, vault, slug, created}`뿐 (`raven/api/server.py:1889-1895`) → Dashboard는 남이 덮어썼다는 사실을 알 방법이 없다.

### A.2 결정 사항 (구현자가 다시 물을 것 없음)

| 결정 | 값 | 근거 |
|---|---|---|
| precondition 토큰 | **`st_mtime_ns` + `size` 조합** | `raven/api/server.py:864`가 이미 `(stat.st_mtime_ns, stat.st_size)`를 읽는다 → 새 개념 도입 0. content sha256은 전 파일 재해시 비용 + core에 문서 해시 개념이 아예 없음(`hashlib` 사용처는 `lock.py:162` 경로해시 / `graph.py:135` salt / `hybrid_search.py:57` mock뿐) |
| `updated` 필드 사용 | **불가** | day precision (`contracts.py:196` `{"updated": today}`, `:388` `date.today()`, `frontmatter.py:249`) — 같은 날 두 편집을 구분 못 함 |
| 검사 위치 | **`contracts.write_page` 단일 지점** | R7 — 한 곳에 넣으면 API/CLI/MCP 3표면 동시 적용 |
| 토큰 미제공 시 동작 | **기존 동작 유지 (통과)** | 하위 호환. precondition은 opt-in 파라미터 |
| 불일치 시 반환 | `WriteResult(ok=False, error="stale_precondition")` → REST **409** | 기존 `delete_vault` 409 선례 (docs/issues/server-전역-에러-envelope-불일치.md) |
| 충돌 표면화 범위 | REST 응답에 MCP와 **같은 이름**의 필드 (`_lock_holder`) | 표면 간 용어 분기 방지 |
| scope-out | 자동 merge / 3-way diff / CRDT / 실시간 협업 | 단일 사용자 전제 유지. "덮어쓰기를 막고 알린다"까지가 이 테마 |

### A.3 의존 순서

A.1 (contracts에 precondition 파라미터 + 검사) → A.2 (REST 409 + `_lock_holder` 부착) → A.3 (Dashboard가 409를 사람이 읽을 수 있는 경고로 표시, 저장 전 최신 토큰 획득).

### A.4 검증

- 회귀 테스트: 같은 `mtime_ns` 토큰으로 두 번 write → 두 번째가 `stale_precondition`. 토큰 생략 시 기존과 동일 통과.
- 3표면 각각 1건: `pytest tests/ -q`에 API/CLI/MCP 경로별 테스트.
- 실표면: Dashboard 탭 2개로 같은 문서 편집 → 두 번째 저장이 경고를 띄우고 **첫 편집이 파일에 남아 있음**을 `git diff`로 확인.

---

## 3. Theme B — Layer 경계 + 열화 정직화

### B.0 North Star 연결

"Layer 1 = 에이전트 없이 완성된 제품, Layer 2 = 옵션"이 선언인데, LLM 호출이 `raven/core/` 안에 있고 사람용 API로도 노출된다. 그리고 의미 검색이 조용히 무의미해진다.

### B.1 실측 상태

- core 안의 LLM 결합: `raven/core/ai_advice.py`, `rag.py`, `tagger.py:26`, `draft.py:42` — `GEMINI_API_KEY` / `OPENAI_API_KEY` + `httpx.post`. 사람용 API 노출: `/api/vaults/{name}/ai-advice`, `/rag/query`, `/suggest-tags`, `/drafts/generate`.
- **무성 열화**: `raven/core/hybrid_search.py:50-60` — `sentence-transformers` 미설치 시 sha256 기반 결정론적 mock 768차원 벡터로 fallback. stderr 경고 1회만 나가고, 랭킹된 결과는 계속 정상처럼 반환된다.
- 태세 보고가 틀렸다 (R8): `raven/api/server.py:167-188` `system_info()`가 `:186` `"allow_all_cors": True`를 **하드코딩**한다 (실제 계산값 `_allow_all_cors`는 `:56-59`). `:185` `bind_host`는 실제 바인딩과 무관한 env 기본값.
- 재사용 가능한 게이팅 축이 이미 있다 (R6): `raven/core/vault.py:66` `is_llm_wiki` (`.vault.json` `features.llm_wiki` 또는 `_meta/agents/` 구조 신호; changelog-v0.7.25/26). 사용처: `contracts.py:229`, `mcp/tools/write.py:470`.

### B.2 결정 사항

| 결정 | 값 | 근거 |
|---|---|---|
| LLM 모듈 물리 이동 | **하지 않음** | 큰 패치 금지 (AGENTS.md §13.3). 개념 경계는 "선언 + 게이팅"으로 세운다 |
| 경계 표현 방식 | LLM 의존 기능은 **degraded 상태를 응답에 명시**하고, 문서에서 Layer 2 부속으로 재분류 | 사람이 켜지 않으면 Layer 1이 온전하다는 주장을 검증 가능하게 만듦 |
| mock embedding | **조용한 fallback 금지** — 응답에 `embedding: "mock"` 류 degraded 표시 | 무성 실패 > 잘못된 메시지 (AGENTS.md §9 우선순위) |
| `system_info` | 하드코딩 제거 → **실제 계산값 보고** (`_allow_all_cors`, 실제 bind host) | 태세 보고 endpoint가 태세를 잘못 보고하면 G2 선언도 의미 없음 |
| API 키 없을 때 | 기존 template fallback 유지 + degraded 표시 추가 | 동작 축소 ❌ |
| scope-out | 로컬 LLM 번들, 임베딩 모델 자동 설치, 자체 모델 서빙 | 의존성 추가 = 사용자 승인 사항 (AGENTS.md §10) |

### B.3 의존 순서

B.1 (`system_info` 실제값 보고) → B.2 (hybrid/RAG 응답에 degraded 표시) → B.3 (Dashboard 검색/RAG 화면에 degraded 배지) → B.4 (README/architecture에서 LLM 기능을 Layer 2 부속으로 재분류).

### B.4 검증

- `sentence-transformers` 없는 환경에서 `/hybrid-search` 호출 → 응답에 degraded 표시 존재. 있는 환경에서는 없음.
- `RAVEN_ALLOW_ALL_CORS` 미설정 + 127.0.0.1 바인딩으로 기동 → `/api/system/info`의 `allow_all_cors`가 **false**, `bind_host`가 실제 값.
- Dashboard 검색 화면에서 배지 육안 확인.

---

## 4. Theme C — 선언-실제 재정합 번들 (G3 + G6 + G7 + G8 + G2 선언부)

### C.0 North Star 연결

문서가 SOT라고 선언되어 있으면, 문서가 틀린 순간 SOT가 거짓이 된다. 이 테마는 **문서를 사람이 고치는 대상에서 코드가 파생하는 대상으로 바꾼다**.

### C.1 실측 drift 목록 (전수)

| 항목 | 선언 | 실제 |
|---|---|---|
| 버전 (R10) | `raven/__init__.py:13` `"0.7.67"` / `raven/api/server.py:40` FastAPI `version="0.2.0"` / `README.md:577` v0.7.65 | 최신 `_meta/changelog-v0.7.177.md`. `__version__` 소비처 **0건** (선언만 있고 아무도 안 읽음) |
| API endpoint | `README.md:25, :246` "26 endpoints" | 실측 **65** (`rg -c "^@app\.(get\|post\|put\|delete\|patch)"`) |
| MCP 도구 | `README.md:27, :304` "9 tools + 5 resources" | `@mcp.tool` **23** + `@mcp.resource` **4** |
| lint 개수 | `README.md:230` "lint 14개" | `raven/core/lint.py:109-141` `CHECK_REGISTRY` **22종** (`#1`~`#18`, `#20`~`#23` — 실측 id 열거) |
| lint `#19` | `templates/agent/SCHEMA.md:285` "#19 guide freshness" | `CHECK_REGISTRY`에 `#19` **없음** (id가 `#18` → `#20`으로 건너뜀). Tier 2 표면이 존재하지 않는 체크를 문서화 |
| 진입점 (G7) | `README.md:50` "4개 진입점", `:571` "5번째 금지" | `README.md:228` 스스로 "**5개 진입점** 모두 `raven.core.log.append`" — 저장소 안에서 용어가 두 뜻 |
| Tier 2 표면 (G8) | AGENTS.md §4 "SCHEMA.md + TOOLS.md 2종" / README "SCHEMA / PROJECT-WORKFLOW / log.md" | `raven/core/templates/agent/` = `SCHEMA.md`(20651B), `TOOLS.md`(4892B)뿐. **`PROJECT-WORKFLOW.md` 파일은 저장소에 존재하지 않음** (`find` 0건) — 그런데 참조는 **70개 파일**에 퍼져 있다: `README.md` 4곳(`:344, :389, :549, :577`), `_meta/changelog-v*.md` 42파일, `docs/superpowers/` 6파일, 그 외 `docs/vault-patterns.md` / `docs/architecture.md` / `_meta/SCHEMA.md` / `_meta/index.md` / `_meta/raven-architecture.md` 등. **살아있는 소비처 2건**: `tests/test_v0_7_50_raw_endpoints.py:53, :107`이 `_meta/system/PROJECT-WORKFLOW.md`를 fixture로 생성, `raven/core/templates/agent/SCHEMA.md:38`이 vault로 배포되는 디렉토리 트리에 이를 명시 |
| 관계 추론 (G6) | `_meta/index.md`, `docs/superpowers/plans/semantic-relation-inference-plan.md` "Inference Engine 완료" | `raven/core/`에 `infer` 함수 **0건**. 실체 = 관계 계약(`relations.py`) + lint #23 검증 + analytics/recommend/contradiction |
| type taxonomy | `README` frontmatter 예시 8종 | `templates/agent/SCHEMA.md:48, :108` 9종 (issue 포함). CLI `raven note`는 decision/lesson/gate까지 노출 |
| 위협 모델 (G2 선언부) | README "127.0.0.1 기본 바인딩, 단일 사용자 가정" | `raven/desktop/runtime.py:76, :86, :96` 기본 `0.0.0.0` + `RAVEN_ALLOW_ALL_CORS=1` 자동. `server.py:41` 주석이 스스로 위험을 명시. changelog-v0.7.177이 확정 |

### C.2 결정 사항

| 결정 | 값 | 근거 |
|---|---|---|
| 해법 형태 | **숫자 수동 수정 ❌ → 코드에서 파생 + 가드 테스트** | 선례: `lint.py:109-119` `CHECK_REGISTRY` + `tests/test_lint_check_registry.py:38` (대시보드 14 ↔ 실제 개수 drift를 근본 해결). 단 이 선례는 *등록 누락*만 잡고 *문서 표기*는 못 잡는다 — `#19` 사례가 그 증거 |
| 버전 SOT | `raven/__init__.py:__version__` **1개로 단일화**, `server.py:40` FastAPI version이 이를 읽고, README 상태줄은 파생/가드 대상 | 현재 4개 문자열이 서로 모름 |
| 카운트 3종 | endpoint / MCP tool / lint check 수를 **런타임 집계값과 문서 값 일치 가드 테스트**로 고정 | R9 — doc-contract 테스트 계열 선례 존재 (`tests/test_north_star_contract.py`, `test_vendor_neutrality.py`, `test_v0_7_1_lite_bootstrap_surface.py`) |
| 진입점 용어 | **client ≠ entry point 정의 1문장** 추가 → desktop/mobile을 client로 배치, `README.md:228`의 "5개 진입점" 표현 수정 | 규칙이 반증 가능해야 규칙이다 |
| `PROJECT-WORKFLOW.md` | **파일 신설 ❌ + 참조 제거는 살아있는 표면만** | 실체 없는 문서를 만드는 건 Tier 2 표면 확장 = AGENTS.md §4와 충돌. 실제 2종(SCHEMA/TOOLS)이 정답 |
| 위 참조 제거 범위 | **살아있는 표면만**: `README.md`(4곳), `_meta/SCHEMA.md`, `_meta/index.md`, `_meta/raven-architecture.md`, `docs/architecture.md`, `docs/vault-patterns.md`, `raven/core/templates/agent/SCHEMA.md:38`, `raven/core/contracts.py:442` 주석. **`_meta/changelog-v*.md` 42파일 + `docs/superpowers/` + `docs/evaluations/` + `_meta/plans/`는 손대지 않음** (역사 기록) | changelog append-only 원칙 (AGENTS.md §0.5). 70파일 일괄 치환은 역사 변조 |
| `tests/test_v0_7_50_raw_endpoints.py` | fixture가 왜 `_meta/system/PROJECT-WORKFLOW.md`를 만드는지 확인 후 **경로만 실재 파일로 교체** (테스트 삭제/skip ❌) | 살아있는 소비처이므로 참조 제거 시 RED가 될 수 있다 — 먼저 확인 |
| G6 라벨 | "Inference Engine" → **관계 계약 + 검증 + 분석**으로 개칭 (기능 축소 ❌) | 기능은 좋고 이름이 거짓말을 함 |
| G2 선언 | "localhost only" → **"신뢰된 tailnet 전제"** 로 재선언 1문단 | 전제 변경 사실을 명시. auth/ACL 도입은 여전히 non-goal |
| changelog 원문 | **불변** (append-only, 역사 보존) | AGENTS.md §0.5 호환 노트 원칙 |
| scope-out | pairing secret 도입, auth, `docs/issues/` 3건의 코드 수정 | pairing secret은 실제로 tailnet을 남과 공유할 때 결정. issues 3건은 코드 결함으로 별도 트랙 |

### C.3 의존 순서

C.1 (버전 단일화 + 소비) → C.2 (카운트 3종 파생/가드 테스트, **A/B가 추가한 필드·엔드포인트 포함**) → C.3 (진입점 정의 + `README.md:228` 수정) → C.4 (`PROJECT-WORKFLOW.md` 참조 제거, Tier 2 = 2종 확정) → C.5 (G6 개칭) → C.6 (G2 위협 모델 재선언) → C.7 (type taxonomy 9종 통일).

### C.4 검증

- 가드 테스트가 **실제로 실패할 수 있음**을 증명: 문서 카운트를 일부러 1 틀리게 바꾸면 테스트 RED, 되돌리면 GREEN.
- `pytest tests/ -q` 전체 통과 (기존 629 test 회귀 0).
- `rg "PROJECT-WORKFLOW" README.md` → 0건. `rg -l "PROJECT-WORKFLOW" raven/` → 0건. (changelog/evaluations/superpowers는 잔존이 정상 — 역사 기록)
- lint 개수: `README.md`의 lint 개수 표기 == `len(CHECK_REGISTRY)` (현재 22). `#19` 표기는 SCHEMA.md에서 제거하거나 체크를 등록하거나 — 둘 중 하나로 정합.
- `rg "5개 진입점" README.md` → 0건.
- 버전: `python -c "import raven; print(raven.__version__)"` 와 `curl -s localhost:8765/openapi.json | jq -r .info.version` 와 README 상태줄이 **동일 문자열**.

---

## 5. 분리 — G4 Zettelkasten 프리미티브 (별도 계획)

이 계획에 **포함하지 않는다**. 별도 계획 파일 + ADR로 다룬다.

### 왜 분리인가

패치가 아니라 재창립이다:
- 안정 id 도입은 lint #15 `check_slug_title_1to1` (`raven/core/lint.py:795-807`, ADR-2026-07-08)을 정면으로 부정한다 — 현재는 `slug == slugify(title)`이 강제되어 **제목을 고치면 노드 정체성이 바뀐다**. `aliases`(`node_meta.normalize_aliases`, `db.py:316` FTS5 aliases)가 완충하지만 canonical id는 여전히 제목 파생.
- 관계 어휘 확장은 `raven/core/relations.py:11-13`의 `{uses, depends_on, implements, implemented_by, related}` (전부 소프트웨어 아키텍처 술어)에 지식 술어(contradicts/supports/refines/generalizes/example_of)를 더하는 일이며, `raven/core/db.py:311` `CHECK (relation_type IN (...))` 변경 = 스키마 변경이다.
  - **마이그레이션 인프라는 신설 불필요** (R4): `raven/core/db.py:129-147` `db_schema_drift()` + 자동 rebuild hook (ADR-2026-07-09)이 정확히 이 경우를 위한 기존 경로다.
- 부재 확인된 프리미티브: transclusion / block ref (`![[` 저장소 0건), unlinked mention (`raven/core/` 0건 — orphan은 inbound 0만 봄, lint #4), folgezettel (0건).

A/B/C가 끝난 뒤 착수하면 문서·가드가 이미 정합 상태라 재창립의 blast radius를 측정할 수 있다.

---

## 6. 명시적으로 하지 않을 것 (non-goal 보존)

- **5번째 진입점 추가 ❌** — CLI / HTTP API / Dashboard / MCP 4개 고정 (AGENTS.md §2). desktop/mobile은 client로 정의될 뿐 진입점 신설이 아니다.
- **auth / ACL / multi-tenant ❌** — G2는 "전제 재선언"이며 인증 도입이 아니다.
- **Obsidian 플러그인 생태계 ❌**, **sync 서비스 ❌**, **canvas / database view ❌**
- **실시간 협업 / CRDT / 자동 merge ❌** — Theme A는 "덮어쓰기를 막고 알린다"까지.
- **LLM 모듈 물리 이동 / 로컬 모델 번들 ❌** — 의존성 추가는 사용자 승인 사항 (AGENTS.md §10).
- **changelog 원문 수정 ❌** — append-only, 역사 보존.
- **`PROJECT-WORKFLOW.md` 신설 ❌** — 참조를 제거하는 방향이 정답.
- **사용자 vault 데이터 write ❌** (`~/Raven/*`), **`.vault.json` / `wiki.db` gitignore 변경 ❌**
- **commit ❌ 사용자 승인 없이** (AGENTS.md §6.5)

---

## 7. 전체 의존 순서 요약

```
A.1 contracts precondition  →  A.2 REST 409 + _lock_holder  →  A.3 Dashboard 충돌 경고
                                                                      ↓
B.1 system_info 실제값  →  B.2 degraded 표시  →  B.3 Dashboard 배지  →  B.4 문서 Layer 재분류
                                                                      ↓
C.1 버전 단일화  →  C.2 카운트 파생+가드 (A/B 산출물 포함)  →  C.3 진입점 정의
                 →  C.4 Tier 2 2종 확정  →  C.5 G6 개칭  →  C.6 G2 재선언  →  C.7 type 9종
                                                                      ↓
                                          [별도 계획] G4 Zettelkasten 프리미티브
```

각 테마 종료 조건: 해당 테마의 §검증 항목 전부 PASS + `pytest tests/ -q` 회귀 0 + changelog 새 섹션 append.

---

## 8. 관련 문서

- `AGENTS.md` — §2 진입점 고정, §4 Tier 경계, §8 write contract 단일화, §9 silent 버그 정책, §13.3 surgical 유지
- `README.md` — 제품 정체성, 사용자 3종, non-goal 선언
- `docs/architecture.md` — 4-Layer
- `_meta/decisions/adr-2026-07-08-slug-title-1to1-lint-15.md` — G4가 부정해야 하는 결정
- `_meta/decisions/adr-2026-07-09-wiki-db-schema-migration.md` — G4 관계 어휘 확장의 마이그레이션 경로
- `_meta/decisions/adr-2026-06-30-llm-wiki-plus-alpha.md` — Layer 2 옵션 원칙
- `docs/issues/*.md` — 코드 결함 3건 (이 계획 scope-out, 별도 트랙)
