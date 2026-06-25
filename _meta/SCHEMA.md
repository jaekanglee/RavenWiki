---
created: 2026-06-24
sources: []
tags:
- system
- schema
- meta
title: Wiki Schema
type: rule
updated: '2026-06-25'
---

# Wiki Schema

> 이 문서는 vault의 **규약 매니페스트**입니다.
> LLM 에이전트(wiki-architect / wiki-curator / wiki-writer / wiki-dashboard)와 인간 사용자 모두 이 규약을 따릅니다.

## Domain

**자기구축 위키 시스템** — Obsidian 의존 없이 markdown + git + 자체 뷰어로 동작하는 개인/팀 지식 베이스. LLM Wiki(Karpathy) 패턴을 차용하되, Obsidian·Sync·유료 플러그인을 사용하지 않고 자체 도구로 대체.

## Architecture: SoT 명확화

| 역할 | 무엇 | 추적 | 비고 |
|---|---|---|---|
| **Source of Truth (SoT)** | **markdown 파일** | **git** | 인간이 작성, 진짜 진실 |
| **Query Index** | **`wiki.db` (SQLite)** | **gitignore** | 빌드 산출물, 검색/조회용 |

## Directory Structure (v2.4)

```
wiki/
├── SCHEMA.md, RULES.md, log.md     # 운영 문서
├── content/                        # ⭐ 모든 컨텐츠 (단일 디렉토리)
│   └── *.md (type: frontmatter로 분류)
├── raw/                            # 불변 1차 소스
├── _meta/                          # vault 운영 문서 (frontmatter 면제 X, type: rule)
├── _archive/                       # retired 페이지
├── scripts/                        # W2에서 생성 (build_db.py, lint.py, backup_db.py)
└── wiki.db                         # ⭐ SQLite Query Index (gitignore)
```

### `_meta/` 정책 (v2.4)

- `_meta/*.md`는 vault 운영 문서 (PRD, DR runbook, deployment, ai-roadmap 등)
- 일반적으로 **`type: rule`** 사용
- **frontmatter는 권장이지만 면제 (없으면 default)**
  - 검색/정렬/최근수정일에 활용하려면 frontmatter가 있는 게 편함
  - lint는 면제 (운영 문서에서 missing frontmatter는 skip)
- build_db가 frontmatter 없는 `_meta/` 페이지는 default 값으로 인덱싱

### v1 → v2.4 변경

- ❌ `concepts/`, `entities/`, `comparisons/`, `projects/` 분리
- ✅ `content/` 1개 + `type:` frontmatter로 분류 (유연성)
- ✅ `_meta/` 운영 문서 vs content 구분 (모두 type: rule 가능)

## Frontmatter (필수 — content/ 안)

```yaml
---
title: Page Title
created: YYYY-MM-DD
updated: YYYY-MM-DD
type: concept | person | comparison | project | tool | rule | query | journal
tags: [from taxonomy]
sources: [raw/articles/source.md]
confidence: high | medium | low   # 선택
contested: true                     # 선택
slug: explicit-slug                 # 선택 (v2.2: slug 전략)
aliases: [old-slug-1, old-slug-2]   # 선택 (v2.3: rename 정책)
---
```

## Type Taxonomy

| type | 용도 | outbound ≥ 2 강제 | 예시 |
|---|---|---|---|
| `concept` | 개념/아이디어 | ✅ 강제 | llm-wiki, mcp-server |
| `person` | 인물 | ✅ 강제 | andrej-karpathy |
| `tool` | 도구/소프트웨어 | ✅ 강제 | hermes-agent |
| `comparison` | 비교 분석 | ❌ 면제 | rag-vs-llm-wiki |
| `project` | 프로젝트 | ❌ 면제 | harumoa-overview |
| `rule` | 규칙/정책 | ❌ 면제 | (SCHEMA 자체) |
| `query` | Q&A 결과 | ❌ 면제 | search-result |
| `journal` | 일기/메모 | ❌ 면제 | daily-2026-06-24 |

## Tag Taxonomy (v2.4: core + custom)

### Core Tags (lint 대상 — SCHEMA에 명시)
**새 태그 추가 시 SCHEMA에 먼저 등록**:
- 시스템: `system`, `tool`, `ui`, `search`, `viewer`, `schema`, `mcp`, `dashboard`
- 컨텐츠: `concept`, `person`, `comparison`, `project`, `rule`, `query`, `journal`
- 도메인: `ai`, `wiki`, `karpathy`, `llm-wiki`, `tailscale`, `react`, `python`, `docker`
- 상태: `draft`, `review`, `final`, `deprecated`, `orphan`
- **v0.5.3 승격** (Q3, 3+ 페이지 사용):
  - `meta`
  - `wikisys`
  - `governance`

**lint 동작**: core에 없으면 🔵 info ("not in core taxonomy")

### Custom Tags (자유, lint 면제)
`kotlin`, `android`, `jetpack-compose`, `kubernetes`, `react-19`, ...

**lint 동작**: 자유 허용. tag cloud에 자동 등장.

**승격 절차 (M5)**:
- lint가 같은 tag가 10+ 페이지에서 사용 시 → "core 승격 추천" 알림
- 사용자가 SCHEMA.md에 한 줄 추가 → 승격 완료

## Conventions

- **파일명**: lowercase, hyphens, no spaces (예: `wiki-architect.md`, `rag-vs-llm-wiki.md`)
- **인코딩**: UTF-8
- **줄바꿈**: LF
- **위키링크**: `[[wikilinks]]` (slug = vault-relative path, 예: `[[content/llm-wiki]]`, `[[_meta/system-design]]`, `[[SCHEMA]]`)
- **wikilink intent (v2.3)**:
  - `[[link]]` — auto (target 존재하면 ok, 없으면 info)
  - `[[link]]!` — broken (CRITICAL)
  - `[[link]]?` — missing placeholder (INFO)
- **교차참조**: outbound ≥ 2 = concept/person/tool 만
- **업데이트**: `updated` 갱신
- **새 페이지**: `log.md`에 append
- **근거 마커**: 3+ 소스 종합 시 `^[raw/articles/source.md]`

## Governance (Cognitive Governance)

> LLM의 자연스러운 중력은 합의/평균. governance는 저항.
> 출처: [[content/beyond-karpathy-llm-wiki]]

### 작성 규칙 (wiki-writer)

- outbound `[[wikilinks]]` ≥ 2 (concept/person/tool 한정)
- 모순 발견 시 `contested: true` + `contradictions: [slug]`
- 단일 출처 = `confidence: medium` 또는 `low`
- 개념 페이지는 "왜 중요한가" 섹션 강제
- 책 뒷면 요약 ❌ (반박/한계/적대자 ≥ 1)

### 분리/아카이브

- 200줄 초과 → 분리 대상 (lint warning)
  - **면제**: `type: rule` (운영 문서, reference 페이지) — `_meta/` 안 페이지
  - **면제**: 1,000줄 미만의 reference/FAQ/guide 류
- 90일 미갱신 + 새 출처 → stale
  - **면제**: `type: rule` (변경 빈도 낮음)
- 365일 미갱신 → `_archive/` 후보

### Lint 자동 탐지

1. 🔴 frontmatter 누락/오류
2. 🔴 broken_link (`[[target!]]` 명시 OR target 존재하면 안 됨)
3. 🔵 missing_link (`[[target?]]` 명시 OR target 미존재)
4. 🟡 orphan (>7일 + inbound 0) — **즉시 ❌, 7일 후 ✅**
   - **면제**: `_meta/` 안 페이지 (rule/reference)
5. 🟡 200줄 초과 — **type: rule 면제** (v0.5.2+)
6. 🔵 weak connection (concept/person/tool 중 outbound < 2)
7. 🔵 tag not in core taxonomy
8. 🔵 `contested: true` 페이지 목록
9. 🔵 90일+ 미갱신 + 새 출처 — **type: rule 면제** (v0.5.2+)

## 빌드 원칙

- **markdown = git 추적 (SoT)**
- **wiki.db = 빌드 산출물 (gitignore)**
- **wiki.db.backup = 일 1회 cron (gitignore)**
- **dashboard/MCP = wiki.db 직접 쿼리** (JSON export ❌)

## Slug Rename 정책 (v2.3)

slug 변경 시 (예: `docker-deploy` → `deployment/docker`) 기존 `[[docker-deploy]]` 링크가 모두 깨짐.

**자동 리라이트 정책**:

```yaml
---
slug: deployment/docker          # 새 slug
aliases: [docker-deploy, docker] # 옛 slug alias
---
```

```sql
-- DB lookup: slug 또는 alias로 페이지 찾기
SELECT * FROM pages WHERE slug = ? OR ? IN (
  SELECT value FROM json_each(aliases)
);
```

## MCP 권한 모델 (v2.3)

**기본 = read-only**, write는 명시적 opt-in.

```bash
# 기본 (read-only)
python3 -m wiki_mcp.server
# 사용 가능: search, get_page, lint, graph, log
# 사용 불가: update, ingest

# Write 활성화
python3 -m wiki_mcp.server --write
# 사용 가능: 모두

# Admin (위험: delete, rename)
python3 -m wiki_mcp.server --admin
```

## AI 활용 로드맵 (요약)

| 단계 | 기능 | 시점 |
|---|---|---|
| M1 | 인덱싱 자동화 (curator) | M1 ✅ |
| M2 | MCP server (외부 AI 접근, read-only 기본) | M2 |
| M3 | Vector Search (`sqlite-vec` 1차) | M3 |
| M3 | 관련 문서 추천 (co-citation) | M3 |
| M4 | 문서 Q&A (RAG over vault) | M4 |
| M5 | 자동 태깅 / 모순 강화 탐지 | M5 |
| M6 | 작성 도우미 (초안) | M6 |
| ❌ | AI 채팅 (실시간 대화) | OUT |

## 관련

- [[RULES]] — 운영 정책
- [[content/llm-wiki]] — Karpathy 패턴
- [[content/beyond-karpathy-llm-wiki]] — governance 동기
- [[content/rag-vs-llm-wiki]] — RAG와 비교
- (W5에서 `_meta/ai-roadmap.md` 생성 예정 — M3-M6 상세 로드맵)
