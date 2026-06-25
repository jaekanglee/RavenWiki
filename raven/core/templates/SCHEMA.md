---
title: Vault Schema
created: 2026-06-25
updated: 2026-06-26
type: rule
tags: [system, schema, meta]
confidence: high
---

# Vault Schema

> 이 vault의 **규약 매니페스트**. LLM 에이전트와 사용자 모두 따릅니다.
> 글로벌 SCHEMA는 `~/Desktop/Dev/Project/Wiki/_meta/SCHEMA.md` 참조 (이 문서는 슬림 사본).
> 운영 규칙은 `RULES.md`, 작업 이력은 `log.md` 참조.

## SoT (Source of Truth)

| 역할 | 무엇 | 추적 |
|---|---|---|
| **SoT** | **markdown 파일** | **git** |
| **Query Index** | **`wiki.db`** (SQLite) | **gitignore** |
| **Working Log** | **`log.md`** (vault 루트) | **git** |

→ `raven build` 로 wiki.db 재빌드 가능. 손상되어도 마크다운에서 복구됨.
→ `raven log` 로 작업 이력 조회/추가.

## Directory Structure

```
<vault>/
├── .vault.json         # vault 메타 (name, mode, owner)
├── SCHEMA.md           # 이 문서 (규약 매니페스트)
├── RULES.md            # 편집 규칙 (5가지)
├── log.md              # 작업 이력 (chronological, append-only)
├── raven-policy.md   # vault 운영정책 (카파시 가이드 통합)
├── content/            # ⭐ 모든 컨텐츠 (slug = vault-relative path)
│   └── *.md
├── _meta/              # vault 운영 문서 (type: rule)
├── _archive/           # retired 페이지
└── wiki.db             # SQLite Query Index (gitignore)
```

## Frontmatter 규약

```yaml
---
title: 페이지 제목         # 필수
type: concept             # 필수: concept | person | comparison | project | tool | rule | query | journal
tags: [core, ai]          # 권장: core = lint 대상
created: 2026-06-25       # 자동 (merge 시 보존)
updated: 2026-06-25       # 자동
sources: [raw/articles/x] # 선택: 인용된 1차 소스
confidence: high          # 선택: high | medium | low (단일 출처면 low 권장)
contested: true           # 선택: 모순 발견 시
contradictions: [slug-a]  # 선택: 모순인 다른 페이지 slug
slug: explicit-slug       # 선택 (v2.2: slug 전략)
aliases: [old-slug-1]     # 선택 (v2.3: rename 정책)
---
```

### Frontmatter 신호 (카파시 LLM Wiki 차용)

| 필드 | 의미 | lint 동작 |
|---|---|---|
| `confidence: high` | 다중 출처로 뒷받침 | (정상) |
| `confidence: medium` | 단일 출처지만 검증됨 | (정상) |
| `confidence: low` | 단일 출처, 미검증 | 🔵 info (weak claim 후보) |
| `contested: true` | 모순 발견된 페이지 | 🔵 info (검토 대상) |
| `contradictions: [a,b]` | 모순인 다른 페이지 | 🟡 warning (a/b 미존재 시) |

→ **기존 페이지는 손대지 않음.** 위 필드는 SCHEMA에 명시만, lint는 "필드 없음 = info" (강제 ❌).

## Wikilink 규약

```markdown
[[content/foo]]           # 자동 (target 존재해야)
[[content/foo]]!          # 의도적 broken (CRITICAL if target 존재)
[[content/foo]]?          # placeholder (INFO if target missing)
```

→ `raven link check` 로 검증.

## Tag Taxonomy (core + custom, v0.5.3+)

### Core Tags (lint 대상 — SCHEMA에 명시)
**새 태그 추가 시 SCHEMA에 먼저 등록**:
- 시스템: `system`, `tool`, `ui`, `search`, `viewer`, `schema`, `mcp`, `dashboard`
- 컨텐츠: `concept`, `person`, `comparison`, `project`, `rule`, `query`, `journal`
- 도메인: `ai`, `wiki`, `karpathy`, `llm-wiki`, `tailscale`, `react`, `python`, `docker`
- 상태: `draft`, `review`, `final`, `deprecated`, `orphan`
- **v0.5.3 승격** (Q3, 3+ 페이지 사용):
  - `meta`
  - `raven`
  - `governance`

**lint 동작**: core에 없으면 🟡 warning ("not in core taxonomy")

### Custom Tags (자유, lint 면제)
`kotlin`, `android`, `jetpack-compose`, `kubernetes`, `react-19`, ...

**lint 동작**: 자유 허용. tag cloud에 자동 등장.

## Tag 승격 절차 (M5)

- lint가 같은 tag가 3+ 페이지에서 사용 시 → "core 승격 추천" 알림
- 사용자가 SCHEMA.md에 한 줄 추가 → 승격 완료

## log.md 운영 규칙 (카파시 가이드)

**`log.md`는 vault 루트에 둡니다** (카파시 LLM Wiki 패턴).

```markdown
# Vault Log

> Chronological record of all vault actions. Append-only.
> Format: `## [YYYY-MM-DD] action | subject`
> Actions: ingest, update, create, archive, delete, lint, build, migrate

## [2026-06-26] create | hello-world
- files: [content/hello-world]
- reason: 첫 페이지
```

### 운영 규칙

- **append-only**: 절대 수정 ❌, 추가만 ✅
- **500 entries 초과 시 rotate**: `log.md` → `log-YYYY.md`, 새로 시작
- **자동 append 시점**: 페이지 CRUD / build / lint / archive (CLI가 자동)
- **grep parseable**: `grep "^## \[" log.md | tail -5` → 최근 5개

→ `raven log list --tail 5` / `raven log append` / `raven log rotate`.

## Lint 운영 규칙 (12개 풀세트, v0.5.1+ 자동화)

`raven build` 또는 `raven lint` 실행 시 자동 검증:

| # | 항목 | 심각도 | 비고 |
|---|---|---|---|
| 1 | broken wikilinks (`[[x]]` 인데 target 없음) | 🔴 critical | |
| 2 | broken-intent false positive (`[[x]]!` 인데 target 존재) | 🔴 critical | |
| 3 | missing wikilinks (`[[x]]?` 인데 target 없음) | 🔵 info | 의도적 OK |
| 4 | orphan pages (inbound 0) | 🟡 warning | 7일 grace 후 |
| 5 | contradictions (frontmatter.contradictions 미존재) | 🟡 warning | |
| 6 | confidence: low 페이지 목록 | 🔵 info | |
| 7 | stale pages (updated > 90일 + 새 source) | 🔵 info | |
| 8 | page size > 200줄 | 🔵 info | |
| 9 | tag not in core taxonomy | 🟡 warning | |
| 10 | frontmatter 완전성 (title/type/created/updated) | 🔵 info | |
| 11 | index 완전성 (filesystem vs DB) | 🟡 warning | build 후 |
| 12 | log size > 500 entries | 🔵 info | rotate 권장 |

### 면제 규칙 (v0.5.2.1+)

- **200줄 초과 면제**: `_meta/` 안 페이지 (rule/reference, 운영 문서)
- **stale (90일+) 면제**: `type: rule` + `_meta/` 안
- **orphan 면제**: `_meta/` 안 (운영 문서는 inbound 0이 정상)

## 다음 단계

```bash
# 첫 페이지 만들기
raven page new hello-world --title "Hello, Vault"

# 작업 (자동으로 log.md append)
raven build                              # DB 재빌드 + lint

# 작업 이력 조회
raven log list --tail 10
raven log append "manual note" --action chore

# wikilink 검사
raven link check
```

→ 자세한 사용법은 `raven-guide.md` (vault에 자동 생성) 또는
  `~/Desktop/Dev/Project/Wiki/_meta/raven-guide.md` 참조.

## §X. Cognitive Governance (카파시 LLM Wiki 차용)

> 모든 페이지 작성 시 다음 4가지 신호를 권장 (lint #13 🔵 info):
> 없으면 sterile wiki (백과사전 풍 중립) 됨.

1. **Why it matters** — 페이지 첫 문단에 "왜 중요한가" 1-2줄. 단순 정의 ❌.
2. **반대 입장 (Fights against)** — 단일 진영 주장 ❌. 반대/대안 입장 1개 이상 명시.
   - 헤딩: `## 반대 입장` / `## Fights against` / `## Alternatives` 중 1.
3. **Cross-disciplinary links** — 본문에 wikilink ≥ 1 (기술 외 분야: 인문/예술/생물/역사/철학).
4. **confidence 등급** — frontmatter `confidence: high|medium|low`. single-source = low/medium 강제.

→ v0.5.x: lint #13은 **info**. 페이지 lint 통과 = 무관. 부재 시 §X 명시.
→ v0.6.x 후보: warning 격상 (사용자 결정 시).

### raw/ 출처 frontmatter (ingest 파이프라인, Phase 4.5+)

`raw/articles/*.md` 등 1차 소스 파일 frontmatter:

```yaml
source_url: https://example.com/article
ingested: 2026-06-25
sha256: a1b2c3d4e5f6...
```

### 면제

- `type: rule`, `type: journal`, `type: query` 페이지.
- `_meta/` 안 페이지.
