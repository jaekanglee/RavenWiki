---
title: Vault Editing Rules
created: 2026-06-25
updated: 2026-06-25
type: rule
tags: [system, rules, meta]
confidence: high
---

# Vault Editing Rules

> 이 vault를 편집할 때 따라야 할 5가지 규칙.
> 어기면 lint가 경고/오류 발생.

## R1. 모든 페이지는 frontmatter 필수

```yaml
---
title: ...
type: concept   # 8개 중 하나
---
```

→ `raven page new <slug> --title X --type Y` 사용 (자동 추가).

## R2. slug = vault-relative path

- `raven page new foo` → `content/foo` (자동 prefix)
- `raven page new meta/welcome` → `_meta/welcome` (명시)
- 절대 ❌: `~`, `/`, `..`

## R3. type taxonomy (8개)

| type | 용도 |
|---|---|
| `concept` | 추상 개념 |
| `person` | 인물 |
| `comparison` | 비교 |
| `project` | 프로젝트 |
| `tool` | 도구/시스템 |
| `rule` | 규칙 (이 문서) |
| `query` | 검색 결과 페이지 |
| `journal` | 일지/메모 |

## R4. tags는 core/custom

- `core`: SCHEMA에 명시된 tag (lint 대상)
- `custom`: 자유

## R5. wikilink 의도 명시

- `[[x]]` — 정상 (target 필요)
- `[[x]]!` — 의도적 broken (CRITICAL if target exists)
- `[[x]]?` — placeholder (INFO if target missing)

## 검증

```bash
raven link check       # wikilink 깨진 거
raven build            # DB 재빌드 + lint
```
