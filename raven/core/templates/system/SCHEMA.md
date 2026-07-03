---
title: Vault Schema
created: 2026-06-30
updated: 2026-06-30
type: rule
tags: [system, schema, meta]
audience: user
confidence: high
---

# Vault Schema

> 이 vault의 **데이터 구조 매니페스트**. 사람 운영자가 따르며, 도구(Raven)가
> 자동 검증합니다. 도구 내부 정책 ❌, 도메인 가정 ❌ — 순수 vault 구조만.

## SoT (Source of Truth)

| 역할 | 무엇 | 추적 |
|---|---|---|
| **SoT** | **markdown 파일** | **git** |
| **Query Index** | **`wiki.db`** (SQLite) | **gitignore** |
| **Working Log** | **`log.md`** (vault 루트) | **git** |

→ `raven build`로 wiki.db 재빌드 가능. 손상되어도 마크다운에서 복구됨.

## Directory Structure

```
<vault>/
├── .vault.json         # vault 메타 (name, path)
├── log.md              # 작업 이력 (chronological, append-only)
├── content/            # ⭐ 사용자 컨텐츠 (slug = vault-relative path)
│   ├── index.md        # 자동 카탈로그 (type별 _index/ 페이지로 링크)
│   ├── _index/         # 자동 생성: type별 카탈로그 (content/_index/{type}.md)
│   └── *.md
├── _meta/              # vault 운영 문서 (type: rule)
│   └── system/
│       ├── SCHEMA.md   # 이 문서
│       ├── RULES.md    # 편집 규칙
│       └── README.md   # vault 사용자 가이드
├── _archive/           # retired 페이지
└── wiki.db             # SQLite Query Index (gitignore)
```

## Frontmatter 규약

```yaml
---
title: 페이지 제목         # 필수
type: concept             # 필수: concept | person | comparison | project | tool | rule | query | journal | issue | index
tags: [core, custom]      # 권장: core = lint 대상
created: YYYY-MM-DD       # 자동
updated: YYYY-MM-DD       # 자동
sources: [path/x]         # 선택: 인용된 1차 소스
confidence: high          # 선택: high | medium | low
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

## Wikilink 규약

```markdown
[[content/foo]]           # 자동 (target 존재해야)
[[content/foo]]!          # 의도적 broken (CRITICAL if target 존재)
[[content/foo]]?          # placeholder (INFO if target missing)
```

→ `raven link check`로 검증.

## Tag Taxonomy

### Core Tags (lint 대상)
**SCHEMA에 명시된 태그만 사용**:
- 시스템: `system`, `tool`, `ui`, `search`, `viewer`, `schema`, `mcp`, `dashboard`
- 컨텐츠: `concept`, `person`, `comparison`, `project`, `rule`, `query`, `journal`, `issue`, `index`
- 상태: `draft`, `review`, `final`, `deprecated`, `orphan`

**lint 동작**: core에 없으면 🟡 warning ("not in core taxonomy")

### Custom Tags (자유, lint 면제)
`kotlin`, `android`, `kubernetes`, `react-19`, 자기 도메인 태그, ...

**lint 동작**: 자유 허용.

### Tag 승격 절차
- lint가 같은 tag가 3+ 페이지에서 사용 시 → "core 승격 추천" 알림
- 사용자가 SCHEMA.md에 한 줄 추가 → 승격 완료

## log.md 운영 규칙

**`log.md`는 vault 루트에 둡니다**.

```markdown
# Vault Log

> Chronological record of all vault actions. Append-only.
> Format: `## [YYYY-MM-DD] action | subject`
> Actions: ingest, update, create, archive, delete, lint, build, migrate

## [2026-06-30] create | hello-world
- files: [content/hello-world]
- reason: 첫 페이지
```

### 운영 규칙

- **append-only**: 절대 수정 ❌, 추가만 ✅
- **500 entries 초과 시 rotate**: `log.md` → `log-YYYY.md`, 새로 시작
- **자동 append 시점**: 페이지 CRUD / build / lint / archive (CLI가 자동)
- **grep parseable**: `grep "^## \[" log.md | tail -5` → 최근 5개

→ `raven log list --tail 5` / `raven log append` / `raven log rotate`.

## Lint 운영 (14개)

`raven build` 또는 `raven lint run` 실행 시 자동 검증:

| # | 항목 | 심각도 |
|---|---|---|
| 1 | broken wikilinks | 🔴 critical |
| 2 | broken-intent false positive | 🔴 critical |
| 3 | missing wikilinks | 🔵 info |
| 4 | orphan pages (inbound 0) | 🟡 warning (7일 grace) |
| 5 | contradictions | 🟡 warning |
| 6 | confidence: low 페이지 | 🔵 info |
| 7 | stale pages (updated > 90일) | 🔵 info |
| 8 | page size > 200줄 | 🔵 info |
| 9 | tag not in core taxonomy | 🟡 warning |
| 10 | frontmatter 완전성 | 🔵 info |
| 11 | index 완전성 (FS vs DB) | 🟡 warning |
| 12 | log size > 500 entries | 🔵 info |
| 13 | cognitive governance | 🔵 info |
| 14 | tier integrity | 🔴 critical / 🟡 warning |

### 면제 규칙

- **200줄 초과 면제**: `_meta/` 안 페이지
- **stale (90일+) 면제**: `type: rule` + `_meta/` 안
- **orphan 면제**: `_meta/` 안 (운영 문서)
- **#13 cognitive governance 면제**: `type: rule`, `journal`, `query`, `_meta/` 안
- **#14 tier integrity 강등**: `allow_tier1_leak: true`면 critical → warning

### Cognitive Governance (#13)

> **모든 페이지 작성 시 다음 4가지 신호 권장** (없으면 sterile wiki):
>
> 1. **Why it matters** — 페이지 첫 문단에 "왜 중요한가" 1-2줄
> 2. **Fights against** — 반대/대안 입장 1개 이상 (`## 반대 입장` 헤딩)
> 3. **Cross-disciplinary links** — 본문에 wikilink ≥ 1
> 4. **confidence 등급** — frontmatter `confidence: high|medium|low`. single-source = low/medium

## 다음 단계

```bash
# 첫 페이지 만들기
raven page new content/hello-world --title "Hello, Vault" --type concept

# 작업 (자동으로 log.md append)
raven build                              # DB 재빌드 + lint

# 작업 이력 조회
raven log list --tail 10
raven log append "manual note" --action chore

# wikilink 검사
raven link check
```

> 💡 자세한 vault 운영 가이드는 `README.md` 참조. LLM Wiki +α 패턴은 `docs/vault-patterns.md` 참조.
