---
title: Vault Agent Operations
created: 2026-06-27
updated: 2026-06-27
type: rule
tags: [system, agents, meta]
audience: agent
confidence: high
---

# Vault Agent Operations

> AI 에이전트 (사람 보조자든 자동화든)가 **이 vault를 다룰 때** 따라야 하는 규약.
> 사람 운영자 규칙은 `RULES.md`, vault 스키마는 `SCHEMA.md`, 작업 이력은 `log.md` 참조.
>
> Raven 운영 코드 자체의 문서는 아닙니다 — 그건 `raven docs show <topic>` (Tier 1).

## 1. 작업 시작 전 — 읽을 것

매 세션 시작 시 (가능하면):

1. `log.md` — 최근 작업 5-10줄 (`grep "^## \[" log.md | tail -10`)
2. `index.md` — vault 전체 구조와 핵심 페이지 (있으면)

→ 이 두 파일을 안 읽고 컨텍스트를 가정하지 마세요.

## 2. 4가지 명령 키워드 (vendor-agnostic)

사용자 요청을 다음 4개로 분류:

| 키워드 | 의미 | Raven CLI/API 호출 |
|---|---|---|
| `save` | 한 건의 노트 저장 | `POST /api/vaults/{n}/pages` 또는 `raven page new` |
| `ingest` | 외부 자료 일괄 정리 | `POST` 반복 + `POST /api/vaults/{n}/build` |
| `query` | 검색/조회 | `GET /api/vaults/{n}/search?q=...` 또는 `raven page get` |
| `lint` | 무결성 검사 | `GET /api/vaults/{n}/link-check` 또는 `raven lint run` |

추가: `first-setup` (신규 vault 1회) → `POST /api/vaults/create` + `build`.

> 위 키워드는 어떤 도구/AI 서비스에서 호출되든 동일 해석. **도구명을 노트 본문에 박지 마세요** (vendor-agnostic 유지).

## 3. 권한 — vault 내부 3개 영역만

| 경로 | 권한 | 용도 |
|---|---|---|
| `<vault>/content/` | **read / write** | 사용자 노트 |
| `<vault>/_meta/` | **read** | 운영 문서 (직접 수정 ❌, `raven meta sync`만) |
| `<vault>/log.md` | **append only** | 작업 이력 (기존 줄 수정 ❌) |

위 영역을 벗어나는 건 **읽기 전용 또는 무시**:
- `.vault.json` — 직접 수정 ❌ (raven CLI만)
- `wiki.db` — 직접 수정 ❌ (검색 인덱스, `raven build`가 관리)
- `_archive/` — 직접 읽기 OK, 추가 ❌
- vault 외부 시스템 설정 — 절대 건드리지 마세요

## 4. 저장 결정 — 4가지 신호

`save` / `ingest` 받으면 페이지 만들기 **전에** 다음 4문항 확인:

1. **재사용 가능성** — 다시 찾게 될 정보인가?
2. **인수인계 필요성** — 다음 세션/에이전트/사람에게 전달이 필요한가?
3. **결정 근거** — 왜 그렇게 했는지 추적이 필요한가?
4. **실패/리스크 기록** — 같은 실수 반복 방지를 위한가?

모두 "아니오"면 저장하지 마세요. vault는 신호 대 잡음비가 높은 공간입니다.

→ 자세한 인지 거버넌스(cognitive governance: Why / Fights against / cross-link / confidence)는 `SCHEMA.md` §Cognitive Governance 참조.

## 5. 페이지 작성 규약 (요약)

- **위치**: `<vault>/content/<slug>.md` (slug = vault-relative path)
- **frontmatter 필수**: `title`, `type` (8종 중), `created`, `updated`
- **wikilink intent**: `[[x]]` (정상) / `[[x]]!` (broken) / `[[x]]?` (placeholder)
- **type 8종**: concept / person / comparison / project / tool / rule / query / journal — 그 외 값 ❌

→ 자세한 필드 정의는 `SCHEMA.md` §Frontmatter 규약.

## 6. 작업 절차

1. `log.md` 5-10줄 읽기 (세션 시작 시)
2. 사용자 요청을 4 키워드로 분류 (first-setup 별도)
3. 매핑된 CLI/API 호출
4. 작업 끝나면 사용자에게 보고:
   - **무엇을 했는가** (파일 경로, 명령)
   - **왜 그렇게 했는가** (4가지 저장 신호 중 무엇에 해당했나)
   - **다음에 무엇이 가능한가** (후속 후보)

→ log.md append는 raven CLI/API가 자동으로 처리합니다 (`raven build`, `page new`, `lint run` 등).

## 7. 하지 말 것

- ❌ 도메인/프로젝트 이름을 임의로 가정하지 마세요.
- ❌ `type` 8종 외 새 타입 정의 ❌ (SCHEMA에 먼저 등록).
- ❌ `_meta/`, `.vault.json`, `wiki.db`를 직접 수정 ❌.
- ❌ `log.md` 기존 줄 삭제/수정 ❌ (append-only).
- ❌ 4가지 저장 신호 모두 통과 못한 노트 작성 ❌.
- ❌ raven 운영 코드(OPERATIONS, agent/*, raven-policy)를 vault에 복사 ❌ (Tier 1 정책).
- ❌ vault 외부 시스템(다른 프로젝트, 시스템 설정 등) 수정 ❌.

## 8. 예외: 다른 도구/AI에서의 호출

이 규칙은 **도구 vendor에 종속되지 않습니다**. Codex CLI든, Claude Code든, Cursor든, 자동화 스크립트든, 동일하게 해석됩니다.

- 도구 호출 어댑터만 바꾸면 됩니다 (CLI / HTTP API / MCP).
- raven의 4 진입점: **CLI** (`raven ...`), **HTTP API** (`POST /api/...`), **MCP** (read-only 기본), **Dashboard** (read-only).
- MCP 도구 호출 시 → `wiki_search`, `wiki_get_page`, `wiki_lint` (MCP 서버가 라우팅).