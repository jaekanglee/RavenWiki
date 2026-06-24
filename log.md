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
