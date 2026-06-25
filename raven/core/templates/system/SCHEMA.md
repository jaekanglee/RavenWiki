---
title: Vault Schema
created: 2026-06-26
updated: 2026-06-26
revision: Lite bootstrap 슬림화 (2-tier 모델 v2026-06-26)
type: rule
tags: [system, schema, meta]
audience: user
confidence: high
---

# Vault Schema

> 이 vault의 **사용자 규약 매니페스트**. 사람 운영자 + raven 코드(lint/build)가 따릅니다.
> 편집 규칙은 `RULES.md`, 작업 이력은 `log.md` 참조.

## 2-Tier Boundary (Lite bootstrap 정책)

- **Tier 1 — raven 패키지**: 빌드, lint, 운영 매뉴얼. `raven docs` 명령으로 접근.
- **Tier 2 — 이 vault**: 사용자 runtime 데이터. markdown + wiki.db.
- Tier 1 문서(OPERATIONS, agent/*, raven-policy)는 **사용자 vault에 복사되지 않음**.

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
├── log.md              # 작업 이력 (chronological, append-only)
├── content/            # ⭐ 사용자 컨텐츠 (slug = vault-relative path)
│   └── *.md
├── _meta/              # vault 운영 문서 (type: rule)
│   └── system/
│       ├── SCHEMA.md   # 이 문서
│       └── RULES.md    # 편집 5규칙
├── _archive/           # retired 페이지
└── wiki.db             # SQLite Query Index (gitignore)
```

## Frontmatter 규약

```yaml
---
title: 페이지 제목         # 필수
type: concept             # 필수: concept | person | comparison | project | tool | rule | query | journal
tags: [core, ai]          # 권장: core = lint 대상
created: 2026-06-26       # 자동 (merge 시 보존)
updated: 2026-06-26       # 자동
sources: [raw/articles/x] # 선택: 인용된 1차 소스
confidence: high          # 선택: high | medium | low (단일 출처면 low 권장)
contested: true           # 선택: 모순 발견 시
contradictions: [slug-a]  # 선택: 모순인 다른 페이지 slug
slug: explicit-slug       # 선택
aliases: [old-slug-1]     # 선택
---
```

### Frontmatter 신호 (lint 동작)

| 필드 | 의미 | lint |
|---|---|---|
| `confidence: low` | 단일 출처, 미검증 | 🔵 info |
| `contested: true` | 모순 발견된 페이지 | 🔵 info |
| `contradictions: [a,b]` | 모순인 다른 페이지 | 🟡 warning (a/b 미존재 시) |

→ **기존 페이지는 손대지 않음.** 위 필드는 SCHEMA에 명시만, lint는 "필드 없음 = info".

## Wikilink 규약

```markdown
[[content/foo]]           # 자동 (target 존재해야)
[[content/foo]]!          # 의도적 broken (CRITICAL if target 존재)
[[content/foo]]?          # placeholder (INFO if target missing)
```

→ `raven link check` 로 검증.

## Tag Taxonomy

### Core Tags (lint 대상 — SCHEMA에 명시)
**새 태그 추가 시 SCHEMA에 먼저 등록**:
- 시스템: `system`, `tool`, `ui`, `search`, `viewer`, `schema`, `mcp`, `dashboard`
- 컨텐츠: `concept`, `person`, `comparison`, `project`, `rule`, `query`, `journal`
- 도메인: `ai`, `wiki`, `karpathy`, `llm-wiki`, `tailscale`, `react`, `python`, `docker`
- 상태: `draft`, `review`, `final`, `deprecated`, `orphan`

**lint 동작**: core에 없으면 🟡 warning ("not in core taxonomy")

### Custom Tags (자유, lint 면제)
`kotlin`, `android`, `jetpack-compose`, `kubernetes`, `react-19`, ...

**lint 동작**: 자유 허용. tag cloud에 자동 등장.

### Tag 승격 절차
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

## Lint 운영 규칙 (12개 풀세트)

`raven build` 또는 `raven lint run` 실행 시 자동 검증:

| # | 항목 | 심각도 |
|---|---|---|
| 1 | broken wikilinks (`[[x]]` 인데 target 없음) | 🔴 critical |
| 2 | broken-intent false positive (`[[x]]!` 인데 target 존재) | 🔴 critical |
| 3 | missing wikilinks (`[[x]]?` 인데 target 없음) | 🔵 info |
| 4 | orphan pages (inbound 0) | 🟡 warning (7일 grace 후) |
| 5 | contradictions (frontmatter.contradictions 미존재) | 🟡 warning |
| 6 | confidence: low 페이지 목록 | 🔵 info |
| 7 | stale pages (updated > 90일 + 새 source) | 🔵 info |
| 8 | page size > 200줄 | 🔵 info |
| 9 | tag not in core taxonomy | 🟡 warning |
| 10 | frontmatter 완전성 (title/type/created/updated) | 🔵 info |
| 11 | index 완전성 (filesystem vs DB) | 🟡 warning |
| 12 | log size > 500 entries | 🔵 info |

### 면제 규칙

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

# raven 내부 문서 읽기 (Tier 1, vault에 복사 안 됨)
raven docs operations
raven docs agent
raven docs policy
```