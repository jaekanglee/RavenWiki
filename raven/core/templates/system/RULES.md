---
title: Vault Editing Rules
created: 2026-06-25
updated: 2026-07-01
type: rule
tags: [system, rules, meta]
audience: system
confidence: high
---

# Vault Editing Rules

> 이 vault를 편집할 때 따라야 할 5가지 규칙.
> 어기면 lint가 경고/오류 발생.

## R1. 모든 페이지는 frontmatter 필수

```yaml
---
title: ...
type: concept   # 9개 중 하나
---
```

→ `raven page new <slug> --title X --type Y` 사용 (자동 추가).

## R2. slug = vault-relative path

- `raven page new foo` → `content/foo` (자동 prefix)
- `raven page new meta/welcome` → `_meta/welcome` (명시)
- 절대 ❌: `~`, `/`, `..`

## R3. type taxonomy (9개)

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
| `issue` | 문제 분석 / 장애 / 추적 |

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

## R6. raw/ 폴더 권한 (v0.7.50+, ADR-2026-07-02)

**raw/ 는 사람 1차 운영 영역, 에이전트는 read-only.**

| 주체 | 권한 | 인터페이스 |
|---|---|---|
| **사람** (개발자 / 운영자) | **full CRUD** (조회 / 작성 / 수정 / 삭제 / 이동) | Dashboard `/raw` panel, `raven raw ...` CLI, OS 파일관리자 (직접) |
| **단일 에이전트** (LLM client) | **read-only** | MCP `wiki_read` (raw slug 조회). 쓰기는 `wiki_ingest`로만 가능하며 **사람 명시 명령 필요** |
| **멀티 에이전트** | **read-only** (단일 에이전트와 동일) | 동시성 보호 없음 — 사용자 책임 |

### 규칙

- **에이전트는 raw/ 에 자율 쓰기 금지**. `wiki_ingest` 호출은 사람 운영자의 명시 명령으로만.
- **에이전트가 raw/ 를 수정하려 하면**: `wiki_update` 등 다른 도구는 raw/ 경로를 거부 (HTTP 400 / read-only).
- **사람이 raw/ 를 직접 수정** (`vim`, Finder, Dashboard) 가능. OS 파일관리자 백업/복원으로 undo 가능.
- **에이전트가 만든 wiki 페이지가 raw/ 를 참조**: `<vault>/content/...`에 작성, `[[raw/<slug>]]`로 wikilink만 가능.

### 의도 (왜 사람 1차인가)

`raw/` 는 **source of truth** — 외부 자료(논문, 웹클리핑, dump)의 원본. 에이전트가 자율로 변조하면 컴파일 결과(content/)의 신뢰성 붕괴. **사람이 검증한 자료만 raw/ 에 들어가야** 안전.

## R7. 파일명(slug) — title과 언어까지 1:1 대응

- 물리 파일명(확장자 제외)은 frontmatter `title`을 그대로 슬러그화한 형태여야 합니다: 공백/특수문자는 하이픈(`-`)으로 치환, 영문은 소문자화.
- **언어 보존 (필수)**: `title`의 언어를 파일명에서 임의로 번역하거나 로마자로 음차하지 않습니다. 한글 `title` → 한글 파일명, 영문 `title` → 영문 파일명.
  - ✅ `title: 볼트 동기화 설정` → `볼트-동기화-설정.md`
  - ❌ `title: 볼트 동기화 설정` → `vault-sync-setup.md` (영문 번역 금지)
- 타이틀과 무관한 임의/기계적 파일명(예: `note-1234.md`)은 금지합니다.
