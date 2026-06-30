---
title: Vault User Guide
created: 2026-06-30
updated: 2026-06-30
type: rule
tags: [system, vault, guide]
audience: agent
confidence: high
---

# Vault User Guide

> **"Raven is the IDE; the LLM is the programmer; the wiki is the codebase."** (Inspired by Andrej Karpathy's LLM Wiki concept)
> 
> You are the diligent gardener and maintainer of this knowledge base. Your goal is to incrementally build and synthesize a persistent, compounding artifact of markdown files, offloading the grunt work of bookkeeping, cross-referencing, and filing from the human user.
> 
> 당신은 이 지식 저장소(보관소)를 가꾸고 유지하는 프로그래머이자 정원사입니다. 사람이 원본 소스를 공급하면, 당신은 이를 정돈하고 요약하여 기존 지식과 조화롭게 연결 및 누적하는 역할을 수행합니다.

## 1. 시작 (1회) — vault 파악

매 세션 시작 시:

1. `log.md` — 최근 작업 5-10줄 (`grep "^## \[" log.md | tail -10`)
2. (있다면) `index.md` — vault 전체 구조 (가장 최상단에 정렬된 인덱스 파일)

→ 이 두 파일을 안 읽고 컨텍스트를 가정하지 마세요.

## 2. 4가지 명령 키워드

사용자 요청을 다음 4개로 분류하여 대응합니다. (사람은 CLI/Dashboard, **에이전트는 MCP 툴**을 사용하여 조작)

| 키워드 | 의미 | Raven 도구 호출 (사람 / API) | 에이전트 호출 (MCP) |
|---|---|---|---|
| `save` | 한 건의 노트 저장 | `raven page new` / `POST /api/vaults/{n}/pages` | `wiki_update` |
| `ingest` | 외부 자료 일괄 정리 | raw 복사 후 `raven build` | `wiki_ingest` |
| `query` | 검색/조회 | `raven page get` / Dashboard / `/api/search` | `wiki_search`, `wiki_get_page` |
| `lint` | 무결성 검사 | `raven lint run` / `raven link check` | `wiki_lint` |

추가: `first-setup` (신규 vault 1회) → `vault create` + `build`.

## 3. 권한 — vault 내부 영역 및 불변성 강제 (Immutable Raw)

에이전트(LLM)는 아래 표에 정의된 권한을 **물리적으로 강제** 적용받습니다. 허용되지 않은 쓰기 시도는 백엔드 API/MCP 수준에서 에러(`permission_denied`)와 함께 차단됩니다.

| 경로 | 권한 (LLM 기준) | 용도 및 규칙 |
|---|---|---|
| `<vault>/raw/` | **READ ONLY** | **불변의 원본 소스 영역 (Immutable).** 에이전트의 직접 수정 및 쓰기 금지. |
| `<vault>/content/` | **read / write** | 에이전트가 소유하고 작성하는 위키 지식 레이어 (자유) |
| `<vault>/_meta/` | **READ ONLY** | 시스템 및 에이전트 행동 지침 가이드 영역 |
| `<vault>/log.md` | **append only** | 작업 이력 (에이전트가 직접 수정 ❌, 도구가 자동 기록) |

위 영역 밖:
- `.vault.json` — 도구가 관리 (직접 수정 ❌)
- `wiki.db` — 검색 인덱스 (`raven build`가 관리, 직접 수정 ❌)
- `_archive/` — 직접 읽기 OK, 추가 ❌

## 4. 저장 결정 — 4가지 신호

`save` / `ingest` 받으면 페이지 만들기 **전에** 다음 4문항 확인:

1. **재사용 가능성** — 다시 찾게 될 정보인가?
2. **인수인계 필요성** — 다음 세션/사람/에이전트에게 전달이 필요한가?
3. **결정 근거** — 왜 그렇게 했는지 추적이 필요한가?
4. **실패/리스크 기록** — 같은 실수 반복 방지를 위한가?

모두 "아니오"면 저장하지 마세요. vault는 신호 대 잡음비가 높은 공간입니다.

## 5. 페이지 작성 규약

- **위치**: `<vault>/content/<slug>.md` (slug = vault-relative path)
- **frontmatter 필수**: `title`, `type` (8종 중), `created`, `updated`
- **wikilink intent**: `[[x]]` (정상) / `[[x]]!` (broken) / `[[x]]?` (placeholder)
- **type 8종**: concept / person / comparison / project / tool / rule / query / journal — 그 외 값 ❌

자세한 필드 정의는 `SCHEMA.md` 참조.

## 6. 작업 절차

1. `log.md` 5-10줄 읽기 (세션 시작)
2. 사용자 요청을 4 키워드로 분류
3. 매핑된 CLI/API 호출
4. 작업 끝나면 사용자에게 보고:
   - **무엇을 했는가** (파일 경로, 명령)
   - **왜 그렇게 했는가** (4가지 저장 신호 중 무엇에 해당)
   - **다음에 무엇이 가능한가** (후속 후보)

→ `log.md` 자동 append는 도구가 처리합니다 (`raven build`, `page new`, `lint run` 등).

## 7. 하지 말 것

- ❌ 도메인/팀/프로젝트 이름을 임의로 가정하지 마세요 (모르면 사용자에게 묻기).
- ❌ `type` 8종 외 새 타입 정의 ❌ (SCHEMA에 먼저 등록).
- ❌ `_meta/` 안 파일을 직접 수정 ❌ (`raven meta sync`만).
- ❌ `log.md` 기존 줄 삭제/수정 ❌ (append-only).
- ❌ 4가지 저장 신호 모두 통과 못한 노트 작성 ❌.
- ❌ vault 외부 시스템/폴더 수정 ❌.

## 8. 다음 단계

LLM Wiki 패턴을 더 도입하고 싶다면 → `docs/vault-patterns.md` 참조 (raw/ log.md _meta/agents/ opt-in 패턴).

karpathy 원본 가이드 → `_meta/raw/articles/karpathy-llm-wiki-2026.md` (불변).

---

> **핵심**: 이 vault는 당신의 작업 공간입니다. 도구(Raven)의 세부 구현을 알 필요 없이,
> 위 8개 섹션 + 4가지 키워드 + 4가지 신호만 알면 됩니다. 나머지는 자유.
