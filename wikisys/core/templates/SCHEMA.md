---
title: Vault Schema
created: 2026-06-25
updated: 2026-06-25
type: rule
tags: [system, schema, meta]
confidence: high
---

# Vault Schema

> 이 vault의 **규약 매니페스트**. LLM 에이전트와 사용자 모두 따릅니다.
> 글로벌 SCHEMA는 `~/Desktop/Dev/Project/Wiki/_meta/SCHEMA.md` 참조 (이 문서는 슬림 사본).

## SoT (Source of Truth)

| 역할 | 무엇 | 추적 |
|---|---|---|
| **SoT** | **markdown 파일** | **git** |
| **Query Index** | **`wiki.db`** (SQLite) | **gitignore** |

→ `wikisys build` 로 wiki.db 재빌드 가능. 손상되어도 마크다운에서 복구됨.

## Directory Structure

```
<vault>/
├── .vault.json         # vault 메타 (name, mode, owner)
├── content/            # ⭐ 모든 컨텐츠 (slug = vault-relative path)
│   └── *.md
├── _meta/              # vault 운영 문서 (type: rule)
│   ├── SCHEMA.md       # 이 문서
│   └── RULES.md        # 편집 규칙
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
---
```

## Wikilink 규약

```markdown
[[content/foo]]           # 자동 (target 존재해야)
[[content/foo]]!          # 의도적 broken
[[content/foo]]?          # placeholder (나중에 만들 예정)
```

→ `wikisys link check` 로 검증.

## 다음 단계

```bash
# 첫 페이지 만들기
wikisys page new hello-world --title "Hello, Vault"

# DB 빌드 + lint
wikisys build

# wikilink 검사
wikisys link check
```

→ 자세한 사용법은 `wikisys-guide.md` (vault에 자동 생성) 또는
  `~/Desktop/Dev/Project/Wiki/_meta/wikisys-guide.md` 참조.
