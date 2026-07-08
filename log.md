# Wiki Log

> 시간순 액션 기록. append-only.
> 포맷: `## [YYYY-MM-DD] action | subject`
> Actions: create, ingest, update, query, lint, archive, delete

## [2026-06-24] create | Wiki initialized
- Domain: 자체구축 위키 시스템 (Obsidian 비의존)
- SCHEMA.md, index.md, log.md 작성
- 디렉토리: concepts/, entities/, comparisons/, queries/, _meta/, _archive/, raw/

## [2026-06-24] ingest | karpathy-llm-wiki-2026.md
- Source: https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f
- 80 lines, 12KB, sha256: 916af9d6dc32e942fb8e00347a3f3015a7e31c3b97dad51af3ead3bf617a93ea
- 후속 페이지: concepts/llm-wiki.md, comparisons/rag-vs-llm-wiki.md, concepts/beyond-karpathy-llm-wiki.md

## [2026-06-24] create | wiki-schema (SCHEMA.md)
- Frontmatter, 태그 taxonomy, page thresholds 정의
- 자체구축 원칙 명시 (Obsidian 비의존, markdown+git, BM25 검색)

## [2026-06-24] create | mvp-prd
- 5 goals, 5 non-goals, 90일 성공지표, 5 milestones
- 페르소나 3개, 시나리오 5개

## [2026-06-24] create | wiki-persona
- Primary: Jake (혼자 일하는 개발자, Obsidian 안 사려는 사람)
- Secondary: Riya (리서치)
- Anti-persona: 대규모 팀

## [2026-06-24] create | wiki-scenario
- S1. ingest (Primary) — 새 소스 → 10-15페이지 자동 업데이트
- S2. 탐색 (Primary) — 자체 뷰어로 검색/그래프
- S3. lint/모순 (Secondary) — 자동 모순 탐지
- S4. 새 프로젝트 (Future) — 같은 시스템 재사용
- S5. 뷰어 빌드 (Dev) — 자체 UI

## [2026-06-24] create | llm-wiki (concept)
- Karpathy 패턴 정리
- 우리 시스템 적용 (Obsidian 의존 부분 → 자체 도구로 대체 매핑)

## [2026-06-24] create | rag-vs-llm-wiki (comparison)
- 7가지 차원 비교
- 언제 뭘 쓰는지 가이드

## [2026-06-24] create | beyond-karpathy-llm-wiki (concept)
- Jônadas Techio의 비판 정리
- "Docile Compiler 문제" + Cognitive Governance 해결

## [2026-06-24] update | model-per-profile
- wiki-architect → MiniMax-M3
- wiki-curator → MiniMax-M2.7-highspeed
- wiki-writer → MiniMax-M3
- wiki-dashboard → MiniMax-M2.7
- (모두 minimax-oauth 프로바이더)

## [2026-06-24] create | system-design (5-Layer 아키텍처)
- 5개 레이어 정의: Data / MCP / Dashboard / Hosting / Backup
- 6개 결정사항(D1-D6) 사용자에게 질문 필요
- 통합 아키텍처 다이어그램 (architecture.html, 25KB SVG) 작성
- 비용 분석: ~$5/월 (VPS만, 나머지 무료)
- 6 마일스톤 (M0-M6) 정의

## [2026-06-24] create | architecture.html
- 통합 아키텍처 SVG 다이어그램
- 다크 테마 + 그리드 배경
- 5개 레이어 + 데이터 플로우 화살표 + 6개 요약 카드
- 25KB, 단일 HTML, 오프라인 작동

## [2026-06-24] M1 W1 | Foundation (v1 → v2.4)
- `.gitignore` 생성 (wiki.db, .venv, node_modules 등 제외)
- **v1 → v2.4 마이그레이션**:
  - `concepts/llm-wiki.md` → `content/llm-wiki.md`
  - `concepts/beyond-karpathy-llm-wiki.md` → `content/beyond-karpathy-llm-wiki.md`
  - `comparisons/rag-vs-llm-wiki.md` → `content/rag-vs-llm-wiki.md`
  - 빈 `concepts/`, `comparisons/`, `entities/`, `projects/`, `queries/` → `.gitkeep`
  - `content/`, `_archive/`, `projects/` 신규
- **SCHEMA.md v2.4** (7561 bytes):
  - SoT 명확화 표 (markdown = SoT / SQLite = Query Index)
  - Directory structure v2.4 (content/ 통합, _meta/ 정책)
  - Type taxonomy + outbound 강제 규칙
  - Tag taxonomy: **core + custom 분리**
  - wikilink intent: `[[link]]!` broken / `[[link]]?` missing
  - Lint 룰 9개 (broken_link / missing_link / weak connection)
  - Slug rename 정책 (aliases)
  - MCP 권한 모델 (read-only 기본)
- **RULES.md 신규** (2621 bytes):
  - commit/ingest/lint 절차
  - 금지 사항 6개
  - 백업 정책 (git push 우선, wiki.db 보조)
  - Slug rename 절차
- **index.md 갱신**: v2.4 경로 (`content/...`)로 wikilink 모두 수정
- **log.md 갱신**: W1 완료 기록
- **git init** + 첫 commit 완료 (commit 2c8d62c)

## [2026-06-24] fix | W1 dangling wikilinks (B안: prefix 유지)
- 문제: 4건 critical
  - 잘못된 slug로 SCHEMA 참조 (6 files)
  - 잘못된 slug로 mvp-prd 참조 (4 files)
  - 존재하지 않는 `_meta/ai-roadmap` 링크 (1 file)
  - content/ 미프리픽스 wikilink (5 cases)
- 결정: B안 — wikilink = slug = vault-relative path (예: `[[content/llm-wiki]]`, `[[_meta/system-design]]`, `[[SCHEMA]]`)
- SCHEMA.md L110 규약 문구 갱신
- RULES.md L83 v2.2 → v2.4
- agent role wikilink (wiki-architect 등) → 백틱 (W4에서 페이지 생성 시 복원)
- `_meta/ai-roadmap` → 링크 제거 (W5에서 파일 생성 예정)
- `content/beyond-karpathy-llm-wiki.md` outbound ≥ 2 보강
- 검증: dangling wikilink grep → 0건

## [2026-06-25] M1 W2 | build_db.py (TDD, SQLite v2.4 schema)
- **구조**:
  - `scripts/build_db.py` — vault scan → `wiki.db` 빌드
  - `scripts/pyproject.toml` — `python-frontmatter` 의존, dev=`pytest`
  - `scripts/README.md` — 사용법
  - `scripts/tests/__init__.py` (빈 파일), `conftest.py` (SYS_PATH)
  - `scripts/tests/fixtures/sample-vault/` — 6 content/*.md + 1 _meta/rules.md
  - `scripts/tests/test_build_db.py` — 16 pytest (TDD)
- **TDD 사이클**:
  - [RED] 초기 pytest: 16개 모두 실패 (build_db.py 없음)
  - [GREEN] 구현 후 pytest: **16 passed**
- **SQLite v2.4 schema**:
  - tables: `pages`, `tags`, `links`, `pages_fts` (FTS5)
  - views: `v_backlinks`, `v_pages_with_tags`
  - triggers: pages_ai/ad/au + tags_ai (FTS5 동기화)
  - indexes: `idx_tags_tag`, `idx_links_target`
- **구현 디테일**:
  - slug 전략 v2.2 (frontmatter slug 우선 → path fallback → content/ prefix 제거 → _meta/ 유지)
  - wikilink intent v2.3 (`[[link]]` auto / `[[!]]` broken / `[[?]]` missing)
  - context 추출 (링크 주변 ±50자)
  - 제외 경로: raw/, _archive/, scripts/, node_modules/, .venv/, .git/
  - frontmatter 없는 페이지는 default (type=rule, 오늘 날짜)로 인덱싱
  - FTS5: 비-contentless 패턴 사용 (tags 동적 재계산 위해 GROUP_CONCAT 서브쿼리)
- **실제 vault 실행 결과**:
  - `~/wiki/wiki.db` 348 KB
  - **11 pages** (3 content + 4 _meta + 4 root: SCHEMA/RULES/index/log)
  - **80 links** (55 auto + 3 missing — SCHEMA/RULES/log에 `[[link]]?` syntax 문서화)
  - **34 tags** (top: system=9, meta=6, llm-wiki=3)
- **FTS5 BM25 검증**:
  - `MATCH 'karpathy'` → llm-wiki 1st, beyond-karpathy 2nd ✅
  - `MATCH 'cognit*'` → beyond-karpathy 1st ✅
  - `MATCH 'rag'` → rag-vs-llm-wiki 1st ✅
- **v_backlinks 검증**:
  - SCHEMA 페이지에 6개 inbound (RULES, index, mvp-prd, system-design, wiki-scenario, beyond-karpathy, _meta/system-design)
- **부가**: `.gitignore`에 `*.egg-info/` 추가 (pip install -e 부산물)
- **commit**: `3689df9` feat(scripts): build_db.py (SQLite v2.4 schema + TDD)
- **다음 (W3)**: lint.py — wiki.db 읽어서 🔴 broken / 🟡 orphan / 🟡 200줄 / 🔵 weak connection / 🔵 tag-not-core / 🔵 contested 등 룰 9개 자동 탐지

## [2026-06-25] M1 W3 | lint.py (TDD, 9 lint rules, wiki.db read-only)
- **구조**:
  - `scripts/lint.py` — `lint_db(db_path, vault_root=None)` + `main()` CLI (345 lines)
  - `scripts/tests/test_lint.py` — **18 pytest** (TDD; in-memory schema, deterministic timestamps)
  - `scripts/tests/fixtures/sample-vault/content/` — 8 lint fixtures (orphan-young/old, big, short-concept, bad-frontmatter, broken-explicit, missing-explicit, custom-tag)
  - `scripts/pyproject.toml` — `py-modules = ["build_db", "lint"]`
  - `scripts/README.md` — lint 사용법 + 9 룰 표 추가
  - `scripts/tests/test_build_db.py` — `test_pages_indexed` expected set 확장 (7 → 15 pages)
- **TDD 사이클**:
  - [RED] 초기 pytest: collection error (`ModuleNotFoundError: No module named 'lint'`)
  - [GREEN] 구현 후 pytest: **34 passed** (16 build_db + 18 lint)
- **구현 디테일**:
  - **읽기 전용** — `wiki.db`만 SELECT; markdown re-parse ❌
  - `Issue` dataclass + `format()` (🔴/🟡/🔵 emoji prefix) + `summarize()` (📊 N crit/M warn/K info/T total)
  - `lint_db()`: pages fetch 1회 + inbound/outbound/tags pre-aggregation 3회 → 9 룰은 모두 in-memory 평가 (총 5 SELECT)
  - `stale` 룰은 `vault_root` 받아 `raw/<stem>.md` mtime 확인 (재렌더 후 자동 OK 처리)
  - `_parse_date()`: ISO-8601 YYYY-MM-DD; NULL/garbage → None (lint skip)
  - `CORE_TAGS` frozenset (29개 — 시스템 8 + 컨텐츠 7 + 도메인 8 + 상태 5 + 비교 1)
  - `WEAK_CONN_EXEMPT_TYPES` = `{"comparison"}` (비교 페이지는 단일 대상 OK)
  - 임계값: `ORPHAN_GRACE_DAYS=7`, `OVERSIZED_LINES=200`, `STALE_DAYS=90`, `WEAK_CONNECTION_MIN_OUTBOUND=2`
  - CLI exit code: critical 0건 → 0, 1건+ → 1, DB 없음 → 2
- **실제 vault 실행 결과** (`cd ~/wiki && python3 scripts/lint.py`):
  ```
  🟡 [warning] SCHEMA.md: 216 lines (>200)
  🟡 [warning] _meta/system-design.md: 412 lines (>200)
  🔵 [info] RULES.md: tag not in core taxonomy: meta
  🔵 [info] RULES.md: placeholder wikilink [[link]]? - intentional TODO
  🔵 [info] SCHEMA.md: tag not in core taxonomy: meta
  🔵 [info] SCHEMA.md: placeholder wikilink [[link]]? - intentional TODO
  🔵 [info] _meta/mvp-prd.md: tag not in core taxonomy: harumoa, meta, prd
  🔵 [info] _meta/system-design.md: tag not in core taxonomy: architecture, meta, prd
  🔵 [info] _meta/wiki-persona.md: tag not in core taxonomy: meta, persona
  🔵 [info] _meta/wiki-scenario.md: tag not in core taxonomy: harumoa, meta, scenario
  🔵 [info] content/beyond-karpathy-llm-wiki.md: tag not in core taxonomy: criticism, governance
  🔵 [info] content/rag-vs-llm-wiki.md: tag not in core taxonomy: rag
  🔵 [info] log.md: placeholder wikilink [[link]]? - intentional TODO
  📊 0 critical, 2 warning, 11 info, 13 total
  ```
  exit=0 ✅
- **룰별 발견 (실제 vault, 11 pages)**:
  - broken_link: 0건 ✅
  - missing frontmatter: 0건 ✅
  - missing_link (`[[?]]`): 3건 (RULES, SCHEMA, log — 문서 내 syntax 예시)
  - orphan (7d+): 0건 (모든 페이지가 어제 생성)
  - 200줄 초과: 2건 (SCHEMA 216줄, system-design 412줄) 🟡
  - weak connection: 0건 (각 페이지 outbound ≥ 2)
  - custom tag: 8건 (meta, prd, scenario, persona, architecture, harumoa, criticism, governance, rag)
  - contested: 0건
  - stale: 0건
- **lint 통과**: 🔴 0건 ✅
- **발견한 이슈** (W4에서 fix 권장):
  - `meta` 태그 6건 — `CORE_TAGS`에 추가할지 결정 필요 (project-level vs taxonomy-level)
  - `prd`, `persona`, `scenario` 1건씩 — `_meta/` 페이지의 `type:` 필드를 태그로 중복 사용 중 → type과 tag 분리 검토
  - `harumoa` (기고자명) — 태그로 부적절; frontmatter `author:` 필드로 이동 검토
  - SCHEMA.md 216줄 — 분리 후보 (개념 / 빌드 원칙 / lint 규칙 3개 파일로)
  - system-design.md 412줄 — 분리 강력 권장 (요구사항 / 5-layer / 결정)
- **다음 (W4 wiki-writer) 알림**:
  - 현재 vault: **0 critical, 2 warning, 11 info** — lint OK 상태에서 시작 가능
  - `meta` 태그가 6건 → W4에서 taxonomy 합의 시 `CORE_TAGS`에 포함 여부 결정
  - `broken` / `missing` 룰 intent (W2에서 `[[!]]`, `[[?]]` syntax 도입) — W4 작성자 가이드에 명시 필요
- commit: (W3 작업분)

## 2026-06-25 (M1 W4 wiki-writer)

### 작업: content/ 15페이지 작성

**위임**: `wiki-writer` 프로필 (MiniMax-M3)

**작성한 페이지 (15개)**:

| type | 파일 | outbound | 라인 |
|---|---|---|---|
| concept | `content/mcp-server.md` | 6 | 80 |
| concept | `content/tailscale-mesh.md` | 3 | 86 |
| concept | `content/bm25-search.md` | 4 | 89 |
| concept | `content/react-spa-architecture.md` | 4 | 98 |
| tool | `content/hermes-agent.md` | 5 | 78 |
| tool | `content/minimax-m3.md` | 3 | 70 |
| person | `content/andrej-karpathy.md` | 4 | 62 |
| person | `content/jonadas-techio.md` | 4 | 70 |
| comparison | `content/ssg-vs-spa.md` | 2 | 86 |
| comparison | `content/mcp-vs-rest-api.md` | 4 | 95 |
| comparison | `content/sqlite-vs-postgres.md` | 3 | 100 |
| project | `content/harumoa-overview.md` | 5 | 65 |
| project | `content/_template.md` | 7 | 122 |
| query | `content/search-result-2026-06-24.md` | 5 | 86 |
| journal | `content/how-to-start-vault.md` | 8 | 159 |

### 빌드/lint 결과
- **build_db**: 11 → 26 페이지 (+15), 90 → 286 링크 (+196), 34 → 90 태그 (+56)
- **lint** (최종): 🔴 0 / 🟡 4 / 🔵 16 / total 20
  - critical 0 ✅
  - warning 4: SCHEMA 216줄, system-design 412줄, log 208줄, how-to-start-vault 235줄
  - info 16: custom tag (governance, rag, security, template, onboarding, criticism, meta, prd, scenario, persona, architecture, harumoa) + placeholder wikilink 예시 (RULES, SCHEMA, log, _template)

### outbound ≥ 2 강제 검증 (concept/person/tool)
- 모든 대상 페이지가 ≥ 3 outbound (최소: tailscale-mesh 3) ✅
- 강제 규칙 위반: **0건** 🔴

### 발견한 이슈 (W5 wiki-architect 알림)
- `_meta/system-design.md` 412줄 — 분리 **강력 권장** (요구사항 / 5-layer / 결정 3개로)
  - 분리안: `_meta/requirements.md` (니즈+제약), `_meta/architecture.md` (5-layer + 데이터 플로우), `_meta/decisions.md` (D1-D6)
- `SCHEMA.md` 216줄 — 분리 후보 (개념 / 빌드 원칙 / lint 규칙)
- `how-to-start-vault.md` 235줄 — 페이지당 100줄 권장 초과 (warning이지만 lint 통과)
  - 권장 분리: `content/how-to-start-vault/{overview, setup, common-mistakes, next-steps}.md`
- `meta` 태그 — `CORE_TAGS`에 포함할지 결정 필요 (W3에서 8건, W4 종료 시점에 동일)
- `prd`, `persona`, `scenario`, `harumoa`, `architecture` 태그 — type과 중복; frontmatter `author:`, `category:` 필드로 분리 검토

### 다음 (W5 wiki-architect) 알림
- `_meta/` 3개 문서 작성 필요:
  1. `_meta/dr-runbook.md` (재해 복구 절차)
  2. `_meta/deployment.md` (VPS 배포 + Tailscale + systemd)
  3. `_meta/ai-roadmap.md` (M3-M6 상세)
- `_meta/system-design.md` 분리 결정 (412줄 → 3개 파일? 또는 외부 보관?)
- `meta` 태그 `CORE_TAGS` 포함 여부 결정
- `_template.md`의 custom tag `template` → `CORE_TAGS` 승격 후보

### commit
- `git commit -m "feat(content): add 15 wiki pages (concept/tool/person/comparison/project/query)"`

## 2026-06-25 (M1 W5 wiki-architect)

### 작업: `_meta/` 6개 문서 (분할 3 + 신규 3)

**원본**: `_meta/system-design.md` 412줄 (lint 🟡 warning: 200줄 초과)

### system-design.md 분리 (412줄 → 3개)

| 신규 파일 | 줄 | 내용 |
|---|---|---|
| `_meta/requirements.md` | 69 | 니즈 N1-N6 / 제약 C1-C5 / 사용자 인용 / 비-목표 |
| `_meta/architecture-5layer.md` | 195 | 5개 레이어 / 데이터 플로우 (ingest/query/MCP) / 비용 분석 |
| `_meta/decisions-d1-d6.md` | 157 | 결정 매트릭스 / D1-D6 근거 / 리스크 R1-R6 / M0-M6 마일스톤 / K1-K7 성공지표 |

### 신규 문서 3개

| 파일 | 줄 | 내용 |
|---|---|---|
| `_meta/dr-runbook.md` | 186 | RPO 1h / RTO 30m / 3-2-1 / S1-S4 시나리오 + 복구 명령어 / 분기 훈련 일정 |
| `_meta/deployment.md` | 197 | VPS + Tailscale + docker-compose + Caddyfile + GitHub webhook + systemd |
| `_meta/ai-roadmap.md` | 194 | M3-M6 단계 / Vector Search (sqlite-vec) / 관련 문서 추천 / RAG Q&A / 자동 태깅 |

### 빌드 / lint 결과

- **build_db**: 26 → 31 pages (+5: 분할 3 + 신규 3, system-design 제거로 순 +5) / 286 → 337 links / 90 → 108 tags
- **lint (최종)**: 🔴 0 / 🟡 3 / 🔵 21 / total 24
  - critical 0 ✅ (요구사항: 0 유지)
  - warning 3 (모두 기존): SCHEMA 216줄, content/how-to-start-vault 235줄, log 266줄
  - info 21: custom tag (meta, requirements, architecture, decisions, deployment, dr, backup, roadmap, prd, scenario, persona, harumoa, template, criticism, governance, onboarding, rag, security) + placeholder wikilink 예시
- **system-design 412줄 경고 제거**: warning 4 → 3 (split으로 해결)

### 분리 효과 (200줄 룰)

- 분할 전: SCHEMA 216, system-design 412, log 266, how-to-start-vault 235 (4건)
- 분할 후: SCHEMA 216, how-to-start-vault 235, log 266 (3건, 모두 기존) — system-design 분할로 1건 해결 ✅

### index.md 갱신

- 6개 항목 추가 (3개 분할 + 3개 신규)
- `[[_meta/system-design]]` 제거 (분할로 대체)
- 페이지 카운트 갱신: 15 content + 9 _meta

### git status (commit 직전)

```
M  index.md
M  log.md
D  _meta/system-design.md
A  _meta/requirements.md
A  _meta/architecture-5layer.md
A  _meta/decisions-d1-d6.md
A  _meta/dr-runbook.md
A  _meta/deployment.md
A  _meta/ai-roadmap.md
```

### 발견한 이슈

- `meta` 태그 9건 (W3: 6건 → W5: +3 신규) — `CORE_TAGS` 포함 결정 계속 보류. 9건은 threshold 넘었으니 다음 단계에서 결정 권장
- `harumoa` (기고자명) 태그 — 여전히 부적절; frontmatter `author:` 필드로 이동 검토
- `_template.md`의 custom tag `template` — `CORE_TAGS` 승격 후보 (W6)
- SCHEMA 216줄 분리 후보 (개념 / 빌드 원칙 / lint 규칙 3개 파일로) — W6 작업 권장
- `how-to-start-vault.md` 235줄 — 페이지당 100줄 권장 초과, 분리는 사용자 판단 보류
- `log.md` 266줄 — 자체 분리 (예: `log-2026-06.md`) 검토 (W6)

### commit
- `refactor(meta): split system-design.md into 3 files + add DR/deployment/ai-roadmap`

## [2026-06-25] M2 | MCP Server (FastMCP)
- `mcp/` 디렉토리 신규 (11 files)
- 7 tools (read 5 + write 2 + admin 2)
- 5 resources (`wiki://index`, `page/{slug}`, `graph`, `log/recent`, `schema`)
- 권한 모델: read (default) / --write / --admin
- transport: stdio (Hermes) + HTTP (Tailscale, 8765)
- **cli.py 명명**: `mcp/server.py`는 SDK `mcp.server` namespace와 충돌 → 우회
- `_load_sdk_fastmcp()`: sys.modules + sys.path scrub으로 SDK 보호
- stdio handshake 검증: initialize/tools/list 정상 (mode별 5/7/9 도구 노출)
- pytest: 32 passed / 3 failed (write.py 사전 버그, M3 fix 예정)
- commit `c74877d`
- 누적 10 commits, lint 0 critical 유지

### 발견 (M3 작업 대상)
- `tools/write.py:46` `wiki_update`가 top-level slug 거부
- `tools/write.py:94` `wiki_ingest`가 str vault로 TypeError
- admin tools (delete/rename)은 stub만 (`{ok:false, "M3 stub"}`)
- `wiki_lint` 이중 subprocess 호출

## [2026-06-25] M3 | Dashboard (React 19 SPA) + M2 admin tools
- **M2 write.py 3건 fix** 완료 (top-level slug, str vault, admin tools stub → 실제 구현)
  - `wiki_delete(slug)`: `_archive/<stem>-YYYYMMDD-HHMMSS.md`로 이동 + DB 재빌드
  - `wiki_rename(old, new)`: frontmatter slug+aliases 갱신 + 모든 wikilink 자동 리라이트 + DB 재빌드
- MCP tests: 32p/3f → **39 passed** (UUID suffix로 idempotent)
- **dashboard/ 디렉토리 신규** (17 파일)
  - React 19 + Vite + TypeScript + Tailwind 4 + PWA
  - 5 라우트 (Home / PageView / Search / Graph / Settings)
  - 6 컴포넌트 (Layout / Sidebar / SearchBar / MarkdownView / GraphCanvas / BacklinksPanel)
  - 3 lib (search / wikilink / types)
  - wikilink `[[link]]` → `/page/<slug>` 자동 변환 (remark plugin, intent !/? 보존)
  - React Flow 그래프 (MiniMap + Controls + fitView)
  - PWA (service worker + manifest + offline cache)
- **scripts/export_static.py** 신규: vault → `dashboard/public/api/*.json`
  - 35 pages + index.json + graph.json + page-<slug>.json 일괄 export
- `npm run build`: ✅ 성공 (695 modules, PWA SW 생성)
- commit `285d64d`
- 누적 12 commits, lint 0 critical 유지

## [2026-06-25] M5 | 설치형 배포 (macOS+Linux 듀얼)
- **`install.sh`** (루트): OS 자동 감지 (darwin* / linux*) → `install/{macos,linux}.sh` 분기 호출
  - env vars: `VAULT`, `REPO`, `SERVICE_USER`
  - `SCRIPT_DIR` 자체 해결 (curl-pipe 호출 호환)
- **`install/macos.sh`**: Homebrew 확인 → `brew install python@3.11 node git` + Tailscale cask → vault clone → venv 생성 → dashboard 빌드 → build_db + export_static → backup_db 초기 실행 → `com.wiki.dashboard.plist`를 `{{VAULT}}` 치환 후 `~/Library/LaunchAgents/` 등록
- **`install/linux.sh`**: apt/dnf 자동 감지 → 시스템 패키지 → Tailscale → vault clone → venv → dashboard 빌드 → 빌드/export → 백업 → systemd 4개 unit 복사 + `daemon-reload` + `enable --now`
- **`deploy/launchd/com.wiki.dashboard.plist`**:
  - vite preview on 127.0.0.1:5173
  - `RunAtLoad=true`, `KeepAlive={Crashed:true}` (크래시 시만 재시작)
  - `StandardOutPath=/StandardErrorPath` → `{{VAULT}}/logs/`
  - `EnvironmentVariables.PATH` 에 homebrew 경로 포함
- **`deploy/systemd/wiki-dashboard.service`** (`%i` 템플릿):
  - `vite preview --port 5173 --host 127.0.0.1` (외부 노출 X)
  - `Restart=always`, `RestartSec=10`, `journal` 로깅
- **`deploy/systemd/wiki-mcp.service`**:
  - `python -m mcp.cli --transport http --host 127.0.0.1 --port 8765`
- **`deploy/systemd/wiki-backup.timer`**:
  - `OnCalendar=*-*-* 18:00:00 UTC` (한국 시간 03:00)
  - `Persistent=true` (다운 후 복귀 시 누락 실행)
  - `RandomizedDelaySec=300` (동시 백업 방지)
- **`deploy/systemd/wiki-backup.service`** (`Type=oneshot`):
  - `backup_db.py --keep 7` 호출
- **`scripts/backup_db.py`** 신규 (M1부터 미구현 해결):
  - `--vault PATH`, `--keep N` (기본 7), `--quiet`
  - 두 종류 백업: `backups/wiki-YYYYMMDD.db` (일자별) + `wiki.db.backup` (최신 1개)
  - rotation: glob sort + 오래된 것부터 삭제
  - idempotent: 오늘 일자별 백업 이미 존재 시 skip
- **`scripts/deploy.sh`** 신규:
  - `VPS=user@host ./scripts/deploy.sh` 사용법
  - 로컬 `git push` → ssh 원격 heredoc → `git pull --ff-only` → `pip install -e` → `npm install && npm run build` → build_db + export_static → backup_db → `systemctl restart wiki-dashboard wiki-mcp`
  - `SKIP_PUSH=1` 옵션 (로컬 변경 없이 강제 배포)
  - 환경에 `systemctl` 없으면 안내 메시지만 출력 (개발 머신 호환)
- **`README.md`** (루트, 신규 — 기존 wiki README는 별도):
  - 빠른 시작 (로컬) / 처음 설치 (macOS, Linux VPS, Windows WSL2) / 일상 운영
  - 5 Layer 아키텍처 표 + ASCII 다이어그램
  - systemd + LaunchAgent 관리 명령어
  - 보안 (Tailscale + 127.0.0.1 바인딩) / 비용 ($5/월) / 트러블슈팅
- **검증**:
  - `bash -n`: install.sh / macos.sh / linux.sh / deploy.sh ✅
  - `xmllint` + `plutil -lint`: plist XML ✅
  - Python configparser: 3 service + 1 timer ✅
  - `backup_db.py --help`: ✅
  - 실 백업 실행: 27MB → `backups/wiki-20260625.db` + `wiki.db.backup` ✅
- 누적 **14 commits** (M3 → M5, 2 commits), lint 0 critical 유지

### 발견 (다음 작업 대상)
- macOS LaunchAgent에 `--keep N` 옵션으로 백업 등록 미포함 → `deploy/launchd/com.wiki.backup.plist` 별도 추가 검토
- `install.sh` 가 sudo 권한 상승 시 `$HOME` 변경 문제 → 향후 `--user` 플래그 또는 `$SUDO_USER` 활용 강화
- 백업 retention 정책 (7일) 외에 weekly/monthly 별도 보관은 미구현 (필요 시 추가)
- deploy.sh 에서 git conflict 발생 시 수동 해결 필요 — 자동 stash/rebase 옵션 검토

## [2026-07-03] update | WorkspacePage LeftTab Split (v0.7.64)
- WorkspacePage.tsx의 우측 패널 탭(activeTab)을 제거하고 좌측 패널 탭(activeLeftTab: "workspace" | "changes")으로 이전
- [🌳 워크스페이스] 선택 시: 좌측에 파일 트리 노출, 파일 클릭 시 우측에 미리보기 노출
- [📋 변경사항] 선택 시: 좌측에 Git 변경 파일 목록 노출, 클릭 시 우측에 Git Diff 노출
- 파일 클릭/디렉토리 이동 등 액션 발생 시 해당 좌측 탭이 자동으로 active 되도록 싱크 처리
- activeTab 누락으로 발생하던 TypeScript 컴파일 에러 17건 해결 및 npm run build, npm test 통과 검증

## [2026-07-08] fix | Prevent GraphCanvas runtime crash on initialization & backend test fixes (v0.7.129)
- 문제:
  1. React Flow가 완전히 초기화되기 전에 `flowToScreenPosition`이 호출되어 런타임 `TypeError`로 그래프 탭이 크래시되는 현상 방지.
  2. 백엔드 테스트 스위트의 flaky 에러 (중복 디렉토리 생성 에러, log append 도중 rotate 시 락 데드락 에러, test whitelist 불일치)로 인한 빌드 에러 해결.
- 해결:
  1. `flowToScreenPosition` 호출을 try-catch로 감싸 안전하게 처리하는 `safeFlowToScreenPosition` 헬퍼를 도입하여 에러를 방어하고, 적절한 fallback을 적용.
  2. `test_tier_boundary.py` whitelist에 `CURATION.md` 추가, `test_mcp_check_freshness.py`에 `exist_ok=True` 추가.
  3. `log.py` 내 `rotate`를 lock 바깥에서 실행하도록 변경 및 `test_lint_log_size.py` 내 rotation threshold mock 처리.
- 파일: `dashboard/src/components/GraphCanvas.tsx`, `raven/core/log.py`, `tests/`
- 검증: `npm run build` 및 `vitest` 통과, `make test` (730 passed) 통과 ✅

## [2026-07-09] UI/UX | all-vault graph UI/UX improvements & vault labels (v0.7.132)
- 문제: 
  1. 전체 볼트(all-vault) 그래프 뷰에서 각 vault 영역을 구분하는 Halo만 보이고 해당 구역이 어떤 vault인지 직관적으로 보여주는 라벨이 누락되어 인지가 어려움.
  2. 고밀도(dense) 모드에서 화면의 깔끔함을 위해 문서 텍스트 라벨을 일괄 차단하여 줌인을 해도 문서 제목을 확인할 수 없는 UX적 답답함 유발.
  3. cross-vault edge의 투명도(opacity=0.08)가 너무 낮아 vault 간 지식의 상호 연결성을 발견하기 어려움.
  4. Centroid 계산 시 필터 전의 그래프를 사용하여 검색/타입 필터 적용 시 캔버스의 실제 노드 위치와 Centroid가 불일치하는 버그.
  5. 고밀도 모드에서 노드가 가득 차면 캔버스 빈 곳을 터치/클릭할 수 없어 노드 자체가 뷰포트 드래그(Pan) 및 핀치 줌 이벤트를 가로채 캔버스 조작이 마비되는 현상.
- 해결:
  1. `GraphCanvas.tsx`에 `graph-vault-centroid-label` 엘리먼트를 추가하여 각 vault 구역의 중앙에 이름을 상시 텍스트로 노출(줌 비율에 맞춰 투명도/크기 동적 보간).
  2. `zoom > 0.55` 조건일 때 노드 라벨(`showLabel`)이 활성화되도록 개선하여 줌인 시 문서 제목이 보이도록 수정.
  3. dense 모드에서 cross-vault edge의 opacity를 `0.15`로, intra-vault edge opacity를 `0.24`로 올려 연결 시인성 회복.
  4. Centroid 계산 기준을 `filteredGraph`로 정합하고, `cluster_compaction = 0.78`을 도입하여 all-vault 레이아웃 시 Vault 간 분리감을 명확히 함.
  5. Figma/Miro 스타일의 `이동 모드(Hand Mode)` 및 `Space 단축키` 메커니즘을 전격 도입하여, Hand 모드 시 모든 노드의 `pointerEvents`를 `none`으로 강제하고 `touchAction`을 완화해 제스처 간섭을 원천 해결 (dense 진입 시 자동 활성화).
- 파일: `dashboard/src/components/GraphCanvas.tsx`, `dashboard/src/routes/GraphPage.tsx`, `dashboard/tests/GraphPage.all-vault-scope.test.tsx`, `raven/api/server.py`, `log.md`
- 검증: `make typecheck` 통과, vitest 11 passed, pytest 730 passed ✅

