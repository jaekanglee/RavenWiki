---
title: M1 완료 보고서
created: 2026-06-25
updated: 2026-06-25
type: rule
tags: [system, meta, m1, report]
---

# M1 완료 보고서

## 요약

- **M1 (Data Layer) 완료** — 2026-06-24 ~ 2026-06-25 (2일)
- **총 commit**: 7
- **핵심 산출물**: 31 pages · 210 links (deduped) · 108 tags · wiki.db (712 KB)
- **검증**: 0 critical, 3 warning, 21 info
- **TDD 커버리지**: build_db.py 16 tests / lint.py 18 tests

## 산출물

### 디렉토리 구조

```
~/wiki/
├── .gitignore              # wiki.db, .venv, .env, *.key, *.pem 등
├── RULES.md                # 71줄
├── SCHEMA.md               # 216줄
├── index.md                # 32줄
├── log.md                  # 334줄
├── wiki.db                 # 712 KB (gitignored)
├── wiki.db.backup          # 712 KB (gitignored)
├── _archive/               # .gitkeep (legacy v1)
├── _meta/                  # 9 pages (rule/scenario/prd/persona)
│   ├── ai-roadmap.md
│   ├── architecture-5layer.md
│   ├── architecture.html   # 25 KB (원본 보존)
│   ├── decisions-d1-d6.md
│   ├── deployment.md
│   ├── dr-runbook.md
│   ├── m1-completion-report.md   ← NEW (this file)
│   ├── mvp-prd.md
│   ├── requirements.md
│   ├── wiki-persona.md
│   └── wiki-scenario.md
├── content/                # 18 pages (concept/tool/person/comparison/project/query/journal)
│   ├── _template.md
│   ├── andrej-karpathy.md
│   ├── beyond-karpathy-llm-wiki.md
│   ├── bm25-search.md
│   ├── harumoa-overview.md
│   ├── hermes-agent.md
│   ├── how-to-start-vault.md
│   ├── jonadas-techio.md
│   ├── llm-wiki.md
│   ├── mcp-server.md
│   ├── mcp-vs-rest-api.md
│   ├── minimax-m3.md
│   ├── rag-vs-llm-wiki.md
│   ├── react-spa-architecture.md
│   ├── search-result-2026-06-24.md
│   ├── sqlite-vs-postgres.md
│   ├── ssg-vs-spa.md
│   └── tailscale-mesh.md
├── comparisons/            # .gitkeep (legacy v1 type-prefix, M2+ 정리)
├── concepts/               # .gitkeep
├── entities/               # .gitkeep
├── projects/               # .gitkeep
├── queries/                # .gitkeep
├── raw/articles/
│   └── karpathy-llm-wiki-2026.md  # 원본 (12 KB)
└── scripts/
    ├── README.md
    ├── build_db.py         # SQLite v2.4 빌더 (TDD 16 tests)
    ├── lint.py             # 9 lint rules (TDD 18 tests)
    ├── pyproject.toml
    └── tests/
        ├── conftest.py
        ├── test_build_db.py
        └── test_lint.py
```

### 페이지 통계

- **total**: 31

| location | n | breakdown (type) |
|----------|---|------------------|
| `content/` | 18 | concept:6 · comparison:4 · tool:2 · project:2 · person:2 · query:1 · journal:1 |
| `_meta/`   |  9 | rule:6 · scenario:1 · prd:1 · persona:1 |
| root       |  4 | rule:4 (RULES, SCHEMA, index, log) |

### 빌드/검증 도구

- **`scripts/build_db.py`** — SQLite v2.4 schema 파서
  - Frontmatter (YAML) + wikilink extractor
  - FTS5 virtual table (`pages_fts`)
  - 2 views (`v_backlinks`, `v_pages_with_tags`)
  - TDD 16 tests
- **`scripts/lint.py`** — 9 lint rules
  - 7 read-only rules on `wiki.db`
  - 2 text rules (placeholder detection)
  - TDD 18 tests
- **`wiki.db`** — 712 KB (W3 시작 348 KB → M1 종료 712 KB, 약 2배)

### SQLite 통계

- **pages**: 31
- **links**: 210 (unique source→target pairs; 206 auto + 4 missing-target flagged)
- **tags**: 108
- **FTS5**: `pages_fts` (BM25 ranking 동작 확인)
- **views**: `v_backlinks`, `v_pages_with_tags`
- **tables**: links · pages · pages_fts · pages_fts_config · pages_fts_content · pages_fts_data · pages_fts_docsize · pages_fts_idx · tags

### Top 10 태그

| tag | n |
|-----|---|
| system | 23 |
| meta | 11 |
| ai | 8 |
| concept | 6 |
| llm-wiki | 6 |
| comparison | 4 |
| karpathy | 3 |
| wiki | 3 |
| dashboard | 2 |
| governance | 2 |

### lint 결과

- 🔴 **critical: 0** ✅
- 🟡 **warning: 3** (모두 200줄 초과 — `_template` 예시 외 정상)
  - `SCHEMA.md`: 216 lines
  - `content/how-to-start-vault.md`: 235 lines
  - `log.md`: 334 lines
- 🔵 **info: 21**
  - 14× `tag not in core taxonomy` (meta, roadmap, architecture, decisions, deployment, dr, harumoa, prd, requirements, persona, scenario, template, criticism, governance, onboarding, rag, security — 17개 custom tag)
  - 4× `placeholder wikilink [[link]]?` (RULES.md, SCHEMA.md, _template.md, log.md — 모두 intentional TODO)

## Git history

```
de5964a 2026-06-25 refactor(meta): split system-design.md into 3 files + add DR/deployment/ai-roadmap
d433807 2026-06-25 feat(content): add 15 wiki pages (concept/tool/person/comparison/project/query)
8d92d56 2026-06-25 feat(scripts): lint.py — 9 lint rules on wiki.db (TDD, read-only)
d020eb8 2026-06-25 update(log): M1 W2 build_db.py 완료 기록
3689df9 2026-06-25 feat(scripts): build_db.py (SQLite v2.4 schema + TDD)
eb178fc 2026-06-25 fix(wikilinks): B안 prefix 유지, dangling 정리, outbound 보강
2c8d62c 2026-06-24 M1 W1: foundation (v1→v2.4 migration, SCHEMA/RULES v2.4)
```

| W | commit | 산출물 |
|---|--------|--------|
| W1 | `2c8d62c` | foundation (v1→v2.4, SCHEMA/RULES, 18 pages schema) |
| W1 fix | `eb178fc` | wikilinks B안 prefix, dangling 정리, outbound 보강 |
| W2 | `3689df9` `d020eb8` | build_db.py (TDD 16 tests) |
| W3 | `8d92d56` | lint.py (TDD 18 tests) |
| W4 | `d433807` | 15 content pages (concept/tool/person/comparison/project/query) |
| W5 | `de5964a` | _meta split (system-design.md → 3 files) + DR/deployment/ai-roadmap |

## 다음 마일스톤 (M2~M6)

### M2: MCP Server (FastMCP)
- FastMCP 서버 (Python) — 7 tools / 5 resources
- **tools**: `search`, `get_page`, `ingest`, `update`, `lint`, `graph`, `log`
- **resources**: `index`, `page`, `graph`, `log`, `schema`
- stdio (헤르메스용) + StreamableHTTP (원격) 듀얼 트랜스포트
- 기본 read-only, `--write` / `--admin` 플래그로 권한 상승
- TDD pytest, hermes MCP 통합

### M3: Dashboard (React 19 SPA)
- Vite + TypeScript
- 사이드바 / 검색 / 그래프 (React Flow) / 마크다운 렌더
- wiki.db 직접 쿼리 or MCP 경유 (결정은 M2 후)
- `.gitignore`에 `node_modules/`, `dist/` 이미 등록됨

### M4: VPS 배포
- Hetzner CAX11 ($5/월) or 동급
- Tailscale mesh
- docker-compose (wiki + dashboard + caddy)
- Caddy 자동 TLS

### M5: 백업/DR 자동화
- 백업 cron (M1은 수동, M2+ 자동)
- git push 자동화
- DR 훈련 (분기 1회, dr-runbook 기반)

### M6: 다른 프로젝트 추가
- `harumoa` 본격 시작 (M5 이후)
- 또는 새 프로젝트 (vault 시스템 검증)

## 결정 사항 (D1~D6)

- **D1**: React 19 + Vite + TypeScript (M3 stack)
- **D2**: Python (FastMCP) (M2 server)
- **D3**: docker-compose (M4 deploy)
- **D4**: Git (GitHub private 1차)
- **D5**: Tailscale only (no public port)
- **D6**: 자체 도메인 우선, MagicDNS 폴백
- **MVP 제외**: AI 채팅 (read-only 우선)

## 알려진 이슈 (M2+ 해결)

| # | 이슈 | 영향 | M2+ 작업 |
|---|------|------|---------|
| 1 | `SCHEMA.md` 216줄 분리 미실행 | lint warning 1 | M2 시작 시 개념/빌드/lint 규칙 분리 |
| 2 | `log.md` 334줄 분리 미실행 | lint warning 1 | M2~M3 사이 분기별 회고 시 분리 |
| 3 | `meta` 태그 CORE_TAGS 승격 결정 미완 | lint info 11 | M2에서 결정 (system-meta vs meta) |
| 4 | 17개 custom tag 미분류 | lint info 14 | M2 lint rule #8 (tag taxonomy) 구현 |
| 5 | `harumoa` 태그 → `author:` 필드 이동 미결 | lint info 2 | M2 schema v2.5에서 결정 |
| 6 | `how-to-start-vault.md` 235줄 사용자 판단 | lint warning 1 | 사용자가 분할 결정 (M2 이후) |
| 7 | `[[llm-wiki]]`로 직접 링크한 페이지 없음 | v_backlinks empty | M2 hub page 보강 또는 사용자가 결정 |
| 8 | type-prefix 빈 디렉토리 5개 (`.gitkeep`) | legacy v1 잔재 | M2에서 삭제 vs 유지 결정 |
| 9 | `backup_db.py` 스크립트 미구현 | M1은 수동 cp | M5 cron 자동화 시 구현 |

## M1 종합 평가

- ✅ **데이터 구조**: SCHEMA v2.4 — frontmatter + wikilink + tag
- ✅ **빌드 도구**: build_db.py (TDD 16 tests)
- ✅ **검증 도구**: lint.py (TDD 18 tests)
- ✅ **콘텐츠**: 31 pages (W1:3 root + W4:15 + W5:9 _meta + 기존 4)
- ✅ **메타 문서**: 9 _meta (ai-roadmap, architecture, decisions, deployment, dr-runbook, mvp-prd, requirements, persona, scenario)
- ✅ **lint 통과**: 0 critical
- ✅ **FTS5 검색**: 동작 확인 (`SELECT … FROM pages_fts WHERE MATCH 'karpathy'`)
- ✅ **v_backlinks view**: 동작 확인 (스키마/조인 OK, 데이터는 sparse)
- ✅ **v_pages_with_tags view**: 동작 확인
- ✅ **.gitignore**: wiki.db, .venv, .env, *.key, *.pem 등 전부 gitignore
- ✅ **secrets**: 0건
- ✅ **wiki.db 백업**: md5 일치 확인

## M2 시작 준비

- 모든 인프라 ✅
- 다음 단계: **MCP Server (FastMCP)** — 7 tools + 5 resources
- 백업 자동화는 M5까지 미루기로 결정
- type-prefix 빈 디렉토리 5개는 M2 시작 시 삭제 결정
