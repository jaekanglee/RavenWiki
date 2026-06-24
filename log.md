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
