# Vault Lite Bootstrap Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Collapse the `llm-wiki` profile's 5-file Lite bootstrap (`_meta/system/{SCHEMA,RULES,README}.md` + `_meta/agents/PROJECT-WORKFLOW.md` + `log.md`) into 2 files (`_meta/agents/SCHEMA.md`, `_meta/agents/PROJECT-WORKFLOW.md`) + `log.md`, per the approved spec at `docs/superpowers/specs/2026-07-03-vault-bootstrap-redesign-design.md`.

**Architecture:** `_meta/system/SCHEMA.md` + `_meta/system/RULES.md` + the type-template section of `agent/PROJECT-WORKFLOW.md` merge into one new `templates/agent/SCHEMA.md` (data contract). `_meta/system/README.md` merges into a rewritten `templates/agent/PROJECT-WORKFLOW.md` (operating facts), which also drops all "agent soul" content (self-eval criteria referencing another agent profile's constitution, writing-philosophy justification prose) and gains an explicit "not covered here" boundary section. All code/docs/tests that hardcode the old 5-path set get updated to the new 3-path set.

**Tech Stack:** Python (raven.core, pytest), FastAPI, React/TypeScript (dashboard), Markdown templates.

---

## Task 1: Write the new merged `templates/agent/SCHEMA.md`

**Files:**
- Create: `raven/core/templates/agent/SCHEMA.md`

- [ ] **Step 1: Write the file**

```markdown
---
title: Vault Schema — 데이터 계약
created: 2026-07-03
updated: 2026-07-03
type: rule
tags: [system, schema, meta]
audience: agent
confidence: high
---

# Vault Schema — 데이터 계약

> 이 문서는 이 vault의 데이터 구조 계약입니다. 여기 정의된 형태를 벗어나면
> `raven lint` / `raven build`가 경고 또는 오류를 냅니다.

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
│   ├── index.md        # 자동 카탈로그
│   └── *.md
├── _meta/
│   └── agents/
│       ├── SCHEMA.md            # 이 문서
│       └── PROJECT-WORKFLOW.md  # 운영 사실
├── _archive/           # retired 페이지
└── wiki.db             # SQLite Query Index (gitignore)
```

## Frontmatter 규약

```yaml
---
title: 페이지 제목         # 필수
type: concept             # 필수: concept | person | comparison | project | tool | rule | query | journal | issue
tags: [core, custom]      # 권장: core = lint 대상
created: YYYY-MM-DD       # 자동
updated: YYYY-MM-DD       # 자동
sources: [path/x]         # 선택: 인용된 1차 소스
confidence: high          # 선택: high | medium | low
contested: true           # 선택: 모순 발견 시
contradictions: [slug-a]  # 선택: 모순인 다른 페이지 slug
aliases: [old-slug-1]     # 선택
---
```

`raven page new <slug> --title X --type Y`로 자동 추가.

### Frontmatter 신호 (lint 동작)

| 필드 | 의미 | lint |
|---|---|---|
| `confidence: low` | 단일 출처, 미검증 | 🔵 info |
| `contested: true` | 모순 발견된 페이지 | 🔵 info |
| `contradictions: [a,b]` | 모순인 다른 페이지 | 🟡 warning (a/b 미존재 시) |

## Slug / 파일명 규칙

- slug = vault-relative path. `raven page new foo` → `content/foo`. `raven page new meta/x` → `_meta/x` (명시).
- 절대 금지: `~`, `/` 시작, `..`
- 물리 파일명(확장자 제외)은 frontmatter `title`을 그대로 슬러그화: 공백/특수문자는 하이픈(`-`), 영문은 소문자화.
- **언어 보존 (필수)**: `title`의 언어를 파일명에서 임의로 번역/음차하지 않습니다. 한글 `title` → 한글 파일명, 영문 `title` → 영문 파일명.
  - ✅ `title: 볼트 동기화 설정` → `볼트-동기화-설정.md`
  - ❌ `title: 볼트 동기화 설정` → `vault-sync-setup.md`
- 타이틀과 무관한 임의/기계적 파일명(예: `note-1234.md`) 금지.

## Type Taxonomy (9종)

| type | 용도 |
|---|---|
| `concept` | 추상 개념 |
| `person` | 인물 |
| `comparison` | 비교 |
| `project` | 프로젝트 |
| `tool` | 도구/시스템 |
| `rule` | 규칙 |
| `query` | 검색 결과 / 질문 페이지 |
| `journal` | 일지/메모 |
| `issue` | 문제 분석 / 장애 / 추적 |

9종 외 새 타입 정의 금지.

## Tag Taxonomy

### Core (lint 대상 — 이 문서에 명시된 태그만)
- 시스템: `system`, `tool`, `ui`, `search`, `viewer`, `schema`, `mcp`, `dashboard`
- 컨텐츠: `concept`, `person`, `comparison`, `project`, `rule`, `query`, `journal`, `issue`
- 상태: `draft`, `review`, `final`, `deprecated`, `orphan`

**lint 동작**: core에 없으면 🟡 warning ("not in core taxonomy").

### Custom (자유, lint 면제)
자기 도메인 태그 자유 사용.

### 승격 절차
같은 태그가 3+ 페이지에서 쓰이면 lint가 "core 승격 추천" 알림 → 이 문서에 한 줄 추가.

## Wikilink 규약

```markdown
[[content/foo]]           # 정상 (target 존재해야)
[[content/foo]]!          # 의도적 broken (CRITICAL if target 존재)
[[content/foo]]?          # placeholder (INFO if target missing)
```

→ `raven link check`로 검증.

## raw/ 권한 모델

**raw/ 는 사람 1차 운영 영역, 에이전트는 read-only.**

| 주체 | 권한 | 인터페이스 |
|---|---|---|
| **사람** | full CRUD | Dashboard `/raw` panel, `raven raw ...` CLI, OS 파일관리자 |
| **단일 에이전트** | read-only | MCP `wiki_read` (조회). 쓰기는 `wiki_ingest`로만, **사람 명시 명령 필요** |
| **멀티 에이전트** | read-only | 동시성 보호 없음 — 사용자 책임 |

- 에이전트는 raw/ 에 자율 쓰기 금지. `wiki_ingest` 호출은 사람 운영자의 명시 명령으로만.
- `wiki_update` 등 다른 도구는 raw/ 경로를 거부 (HTTP 400 / read-only).
- 에이전트가 만든 페이지가 raw/를 참조할 땐 `<vault>/content/...`에 작성하고 `[[raw/<slug>]]`로 wikilink만.
- 이유: `raw/`는 source of truth — 에이전트가 자율 변조하면 컴파일 결과(content/)의 신뢰성이 붕괴.

## log.md 운영 규칙

```markdown
# Vault Log

> Chronological record of all vault actions. Append-only.
> Format: `## [YYYY-MM-DD] action | subject`

## [2026-06-30] create | hello-world
- files: [content/hello-world]
- reason: 첫 페이지
```

- append-only — 기존 줄 수정 금지, 추가만
- 500 entries 초과 시 rotate: `raven log rotate` (`log.md` → `log-YYYY.md`, 새로 시작)
- 자동 append 시점: 페이지 CRUD / build / lint / archive (CLI가 자동 처리)
- `grep "^## \[" log.md | tail -5`로 최근 5개 확인

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

### Cognitive Governance (#13) — 페이지 품질 4신호

1. **Why it matters** — 첫 문단에 "왜 중요한가" 1-2줄
2. **Fights against** — 반대/대안 입장 1개 이상 (`## 반대 입장` 헤딩)
3. **Cross-disciplinary links** — 본문에 wikilink ≥ 1
4. **confidence 등급** — frontmatter `confidence: high|medium|low`. single-source = low/medium

## 페이지 템플릿 (Type 9종)

### `concept`

```
# {Concept Name}

> {BLUF: 1-line definition}

## 내용
{핵심 설명. 다른 개념과 연결되면 wikilink 및 맥락 추가.}

## 왜 중요한가 (Optional)
{이 개념이 왜 필요한지 2-3줄 요약.}

## 반대 입장 / 한계 (Optional)
{이 개념이나 기술의 한계점. 필요할 때만 작성.}

## 관련
- [[related-concept-1]] — 연관 개념에 대한 맥락 설명
```

### 결정 기록 (Decision Record, 보통 `type: rule`)

```
# {Title}

---
type: rule
---

> {BLUF: 1-line decision}

## 맥락
{결정이 필요하게 된 배경과 문제 상황.}

## 결정
{최종 선택과 핵심 논거. 결론을 먼저 제시하고 근거를 붙입니다.}

## 영향 (Optional)
{이 결정으로 인해 시스템이나 프로젝트에 미치는 영향.}

## 관련
- [[related-page]] — 관련 설계 문서 또는 후속 작업 페이지
```

### `journal`

```
# {Title}

> {BLUF: What happened today, 1 line}

## 한 일
- 작업 내용 요약 및 1차 출처 링크

## 메모 (Optional)
- 필요한 관찰 / 결정 / 이슈 사항

## 관련 / 다음
- [[related-project]] — 진행 중인 프로젝트 페이지
```

### `rule`

```
# {Rule Name}

> {BLUF: What this rule is, 1 line}

## 적용 범위
{규칙이 적용되는 대상 및 예외 대상.}

## 규칙
{구체적인 규칙 세부사항 및 가이드.}

## 예외 (Optional)
{규칙이 적용되지 않는 특수 사례.}
```

### `person`

```
# {Name}

> {BLUF: Who they are, 1 line}

## 역할
{담당하는 역할 및 전문 분야.}

## 주요 작업 (Optional)
{해당 인물이 진행한/진행 중인 주요 태스크.}

## 관련
- [[project-x]] — 참여 중인 프로젝트
```

### `tool`

```
# {Tool Name}

> {BLUF: What this tool is, 1 line}

## 용도
{도구의 핵심 목적 및 특징.}

## 사용법 (Optional)
{간단한 셋업 및 실행 명령어.}

## 대안 (Optional)
{대체할 수 있는 다른 도구들과의 차이점.}

## 관련
```

### `comparison`

```
# {A} vs {B}

> {BLUF: Conclusion — which is better, 1 line}

## 기준
{비교를 수행하는 주요 평가 축 설명.}

## Comparison
| Criteria | {A} | {B} |
|---|---|---|
| ... | ... | ... |

## 결론
{평가 결과를 바탕으로 한 최종 제안 및 추천.}
```

### `query`

```
# {Title}

> {BLUF: Core of the question, 1 line}

## 맥락
{이 질문이 발생하게 된 배경과 필요성.}

## 후보 답 (Optional)
- Candidate 1: ...
- Candidate 2: ...

## 열린 이슈 (Optional)
{아직 해결되지 않고 남아 있는 쟁점.}

## 관련
- [[related-page]] — 질문과 관련된 다른 참고 페이지
```

### `project`

```
# {Name}

> {BLUF: What this project is, 1 line}

## 목표
{프로젝트의 최종 마일스톤 및 성공 기준.}

## 현재 상태 (Optional)
{현재 진행 상황 및 핵심 병목 지점.}

## 범위 / 비범위 (Optional)
- **In Scope**: 포함 영역
- **Out of Scope**: 제외 영역

## 관련
- [[decision-or-issue-page]] — 관련 의사결정 문서 및 이슈 트래커
```

### `issue`

```
# {Issue Title}

> {BLUF: 이 이슈의 핵심 원인 및 상태 1줄 요약}

## 상태
{열림(Open) / 진행중(In Progress) / 해결됨(Resolved)}

## 문제 상황
{발생한 문제의 현상 및 재현 경로.}

## 원인 분석
{문제의 근본 원인(Root Cause) 분석.}

## 해결 방안 (Optional)
{적용했거나 고려 중인 패치/해결책.}

## 관련
- [[project-x]] — 관련된 프로젝트
```

## 검증

```bash
raven link check       # wikilink 깨진 거
raven build            # DB 재빌드 + lint
```
```

- [ ] **Step 2: Verify the file has no leftover vendor/domain terms**

Run: `grep -inE "codex|claude code|cursor|antigravity|karpathy" raven/core/templates/agent/SCHEMA.md`
Expected: no output (empty)

---

## Task 2: Write the rewritten `templates/agent/PROJECT-WORKFLOW.md`

**Files:**
- Modify (full rewrite): `raven/core/templates/agent/PROJECT-WORKFLOW.md`

- [ ] **Step 1: Replace the entire file content**

```markdown
---
title: Project Workflow — 운영 사실
created: 2026-06-30
updated: 2026-07-03
type: rule
tags: [system, workflow, meta]
audience: agent
confidence: high
---

# Project Workflow — 운영 사실

> "Raven is the IDE; the LLM is the programmer; the wiki is the codebase."
> 사람이 원본 소스를 공급하면, 당신은 이를 정돈하고 요약해 기존 지식과
> 연결·누적합니다. 아래는 이 vault/도구를 다룰 때 필요한 사실입니다.

## 0. 이 vault를 맡았을 때 읽는 순서 (고정)

1. `log.md` 최근 5-10줄 (`grep "^## \[" log.md | tail -10`)
2. (있다면) `content/index.md` — vault 전체 구조 카탈로그
3. 요청과 직접 관련된 폴더/페이지 3-5개 (`project`, `issue`, 결정 기록(`type: rule`), 최근 `journal`)
4. `_meta/agents/SCHEMA.md` — 데이터 계약

→ 이 순서를 건너뛰고 컨텍스트를 가정하지 마세요. 폴더명만 보고 도메인을
추측하지 말고, 이미 쓰이는 용어/분류/구조를 이 vault 기준으로 재사용하세요.
기준이 모호하면 새 구조를 만들기 전에 사용자에게 확인합니다.

### 파악 완료 기준

"파악했다"고 말하기 전에 최소한 다음은 설명 가능해야 합니다:
- 이 vault/프로젝트의 현재 목표
- 최근 무엇이 바뀌었는지
- 어떤 폴더/페이지를 source of truth로 봤는지
- 바로 수정해도 되는지, 먼저 물어야 하는지

## 1. 4가지 명령 키워드 → MCP 도구 매핑

| 키워드 | 의미 | MCP 도구 |
|---|---|---|
| `save` | 한 건의 노트 저장 | `wiki_update` |
| `ingest` | 외부 자료 일괄 정리 | `wiki_ingest` |
| `query` | 검색/조회 | `wiki_search`, `wiki_get_page` |
| `lint` | 무결성 검사 | `wiki_lint` |

MCP 연결 정보(엔드포인트/포트)와 전체 도구 목록은 `raven docs show agent-tools` 참고.

## 2. 권한 — vault 내부 영역

| 경로 | 주체 | 권한 |
|---|---|---|
| `raw/` | 사람 | full CRUD |
| `raw/` | 에이전트 | read-only (`wiki_ingest`는 사람 명시 명령 시에만) |
| `content/` | 에이전트 | read/write (자유) |
| `_meta/` | 에이전트 | read-only (직접 수정 금지 — `raven meta sync`만) |
| `log.md` | 에이전트 | append만 (도구가 자동 기록, 직접 수정 금지) |

허용되지 않은 쓰기 시도는 API/MCP 수준에서 `permission_denied`로 차단됩니다.
상세 데이터 계약은 `SCHEMA.md` 참조.

## 3. 저장 결정 — 4가지 신호

`save`/`ingest` 받으면 페이지 만들기 **전에** 다음 4문항 확인:

1. **재사용 가능성** — 다시 찾게 될 정보인가?
2. **인수인계 필요성** — 다음 세션/사람/에이전트에게 전달이 필요한가?
3. **결정 근거** — 왜 그렇게 했는지 추적이 필요한가?
4. **실패/리스크 기록** — 같은 실수 반복 방지를 위한가?

모두 "아니오"면 저장하지 마세요. vault는 신호 대 잡음비가 높은 공간입니다.

## 4. 분업 / 트리거 (사실)

- 사람: 결정(rule), 컨셉(concept), 사람(person) — 사람 review 후
- 에이전트: 저널(journal), 빌드/링크체크 — 자동 가능
- 트리거: 사용자 "X 정리해줘" → journal/concept 작성(사람 confirm) / 새 raw/ 파일 → 사람 명시 명령 시 compile / 새 결정 → 관련 페이지에 wikilink 추가

## 5. 형식 요구사항

- **BLUF**: 페이지 첫 줄에 결론/결정 1문장
- frontmatter는 구조화, 본문은 자연스러운 문장으로 작성
- 필수 섹션 최소화(`요약`/`내용`/`관련` 정도), 타입별 상세 섹션은 선택
- **빈 섹션 생성 금지**: 채울 내용 없으면 섹션 자체를 삭제 (`TBD`/`N/A` 금지)
- 본문에 `actor`/`run_id`/`tool`/`idempotency_key` 같은 운영 메타 노출 금지
- 헤더는 순수 자연어 (`## 결론`, 영문 괄호 병기 금지)
- 위키링크는 맥락 설명과 함께: `- [[content/x]] — 이 링크가 본문과 어떤 관계인지 1줄`

## 6. 폴더 구조 권장

- `content/decisions/`, `content/concepts/`, `content/journal/`, `content/issues/`, `content/projects/`, `content/people/`
- `raw/` — source material (LLM Wiki +α 켠 경우)
- vault가 이미 다른 구조면 그 구조를 따르세요 (강제 아님)

## 7. 일관성 체크리스트

페이지 작성 후 확인:

- [ ] 첫 줄이 결론/결정 1문장 (BLUF)
- [ ] frontmatter: `title`/`type`/`created`/`updated` 채워짐
- [ ] type이 9종 중 하나
- [ ] wikilink ≥ 1 + 맥락 설명
- [ ] 본문이 사람 문장으로 읽힘 (운영 메타/JSON/빈 TBD 금지)
- [ ] §3 저장 신호 4가지 통과

## 8. 멀티 에이전트 협업 규칙

- **폴더 분리**: 프로필별 `content/{profile_name}/` 전용 서브폴더 내에서만 작성. 타 프로필 영역 수정 필요 시 사용자 승인 또는 `_meta/`에 교차 참조.
- **락/재시도**: MCP 쓰기 도구의 락 획득 상태/에러 반환을 확인하고, 실패 시 백오프 후 재시도. 병렬 작업이 빈번하면 프로필별 독립 브랜치/워크트리 후 순차 통합.
- **log.md**: 액션 뒤에 프로필 식별자 접두사 (`## [YYYY-MM-DD] create | slug [profile-name]`). 동시 대량 작업 시 기록 시점을 미세하게 엇갈리게.
- **wiki.db**: 직접 SQL 수정 금지 — 반드시 `raven build`로 마크다운에서 재컴파일.
- **`_meta/index.md`**: 직접 파싱/수정 금지 — `raven build`의 index builder만 갱신 가능.
- **`SCHEMA.md`**: 에이전트가 임의 수정 금지 — 변경 필요 시 사용자 승인 또는 `type: issue` 문서로 발의.
- **`_meta/collections.yaml`**: 변경 전 `raven collection validate` 필수.

## 9. 하지 말 것

- ❌ 도메인/팀/프로젝트를 임의로 가정 (모르면 사용자에게 묻기)
- ❌ raw/ 자율 쓰기
- ❌ `_meta/` 직접 수정 (`raven meta sync`만)
- ❌ `log.md` 기존 줄 삭제/수정
- ❌ type 9종 외 새 타입 정의
- ❌ §3 저장 신호 모두 미통과 노트 작성
- ❌ vault 외부 시스템/폴더 수정
- ❌ 한글 title 문서를 영문/로마자 파일명으로 저장

## 10. 다음 단계

LLM Wiki 패턴을 더 켜고 싶다면 → `docs/vault-patterns.md` (raw/log.md/_meta/agents opt-in 확장).

## 이 문서에 없는 것 — 에이전트 스스로 판단/기억할 영역

아래는 이 vault 문서가 의도적으로 다루지 않는 영역입니다. Raven은 "무엇이
있는지(사실)"까지만 알려주고, "언제/어떻게 판단할지"는 당신 자신의 운영
원칙(soul) 또는 메모리 시스템에 있어야 합니다. 그런 판단 기준이 아직
없다면, 이 vault가 아니라 당신 자신의 메모리에 저장하십시오.

- **검색 판단**: `wiki_search`가 있다는 사실은 여기 있지만, "새 페이지
  쓰기 전에 중복을 확인할지"는 당신의 판단입니다.
- **정리/폐기 판단**: `raven garden --stale/--orphan`, `raven curator run`이
  있다는 사실은 여기 있지만, "언제 돌릴지"는 당신의 판단입니다.
- **글쓰기 품질 판단**: 이 vault는 BLUF로 시작하는 형식을 요구하지만,
  "왜 그게 좋은 글쓰기인가"는 여기서 가르치지 않습니다.
- 이 vault를 반복해서 다루며 얻은 **이 vault 특유의 교훈**은 문서를
  직접 고치지 말고 당신의 메모리에 쌓으십시오.
```

- [ ] **Step 2: Verify no vendor names or Hermes Constitution content survive**

Run: `grep -inE "codex|claude code|cursor|antigravity|hermes|자가.?평가" raven/core/templates/agent/PROJECT-WORKFLOW.md`
Expected: no output (empty)

---

## Task 3: Delete the old `templates/system/{SCHEMA,RULES,README}.md`

**Files:**
- Delete: `raven/core/templates/system/SCHEMA.md`
- Delete: `raven/core/templates/system/RULES.md`
- Delete: `raven/core/templates/system/README.md`

- [ ] **Step 1: Delete the files**

```bash
git rm raven/core/templates/system/SCHEMA.md raven/core/templates/system/RULES.md raven/core/templates/system/README.md
```

- [ ] **Step 2: Confirm `templates/system/` now only has `OPERATIONS.md` and `WELCOME.md`**

Run: `ls raven/core/templates/system/`
Expected: `OPERATIONS.md` and `WELCOME.md` only

---

## Task 4: Update `raven/core/vault.py` bootstrap logic

**Files:**
- Modify: `raven/core/vault.py:37-46` (`_LITE_BOOTSTRAP_FILES`)
- Modify: `raven/core/vault.py:167-174` (docstring, already partially updated in a prior session — verify)
- Modify: `raven/core/vault.py:306-358` (`_bootstrap_lite`)
- Modify: `raven/core/vault.py:360-431` (`sync_meta`)

- [ ] **Step 1: Update `_LITE_BOOTSTRAP_FILES`**

Old:
```python
_LITE_BOOTSTRAP_FILES = (
    "_meta/system/SCHEMA.md",
    "_meta/system/RULES.md",
    "_meta/system/README.md",
    "_meta/agents/PROJECT-WORKFLOW.md",
    "log.md",
)
```

New:
```python
_LITE_BOOTSTRAP_FILES = (
    "_meta/agents/SCHEMA.md",
    "_meta/agents/PROJECT-WORKFLOW.md",
    "log.md",
)
```

- [ ] **Step 2: Update `_bootstrap_lite()` docstring + template_map + dir setup**

Old (docstring + body):
```python
    @classmethod
    def _bootstrap_lite(cls, path: Path) -> None:
        """Lite bootstrap (v2026-06-26): copy ONLY the user-facing essentials.

        Creates:
            content/                     (empty)
            _meta/system/SCHEMA.md          (frontmatter/type/tag/wikilink 규약)
            _meta/system/RULES.md           (편집 규칙)
            _meta/system/README.md          (vault 사용자 가이드)
            _meta/agents/PROJECT-WORKFLOW.md (프로젝트 작업 에이전트 공통 워크플로우)
            log.md                          (빈 로그 헤더)

        Does NOT copy:
            OPERATIONS.md  → raven internal docs, use `raven docs operations`
            agent/*        → raven LLM agent behavior, use `raven docs agent`
            raven-policy.md → raven internal policy, use `raven docs policy`

        Idempotent: existing files are NOT overwritten. To refresh templates
        after raven upgrade, use `raven meta sync --lite`.
        """
        from importlib import resources

        content_dir = path / "content"
        meta_dir = path / "_meta"
        system_dir = meta_dir / "system"

        content_dir.mkdir(parents=True, exist_ok=True)
        meta_dir.mkdir(parents=True, exist_ok=True)
        system_dir.mkdir(parents=True, exist_ok=True)

        # Map: target relative path → template resource path
        template_map = {
            "_meta/system/SCHEMA.md":          "templates/system/SCHEMA.md",
            "_meta/system/RULES.md":           "templates/system/RULES.md",
            "_meta/system/README.md":          "templates/system/README.md",
            "_meta/agents/PROJECT-WORKFLOW.md": "templates/agent/PROJECT-WORKFLOW.md",
            "log.md":                          "templates/log.md",
        }
```

New:
```python
    @classmethod
    def _bootstrap_lite(cls, path: Path) -> None:
        """Lite bootstrap (v0.7.65+: agent-only 2-file set): copy ONLY the
        agent-facing operational essentials.

        Creates:
            content/                          (empty)
            _meta/agents/SCHEMA.md            (데이터 계약: frontmatter/type/tag/wikilink/raw 권한/lint)
            _meta/agents/PROJECT-WORKFLOW.md  (운영 사실: 읽기순서/MCP매핑/권한/저장신호/협업규칙)
            log.md                            (빈 로그 헤더)

        Does NOT copy:
            OPERATIONS.md  → raven internal docs, use `raven docs operations`
            agent/*        → raven LLM agent behavior, use `raven docs agent`
            raven-policy.md → raven internal policy, use `raven docs policy`

        v0.7.65+: dropped `_meta/system/{SCHEMA,RULES,README}.md` — merged into
        the 2 files above. No human-manual content is injected into the vault;
        only facts an agent needs to operate this vault/tool correctly.

        Idempotent: existing files are NOT overwritten. To refresh templates
        after raven upgrade, use `raven meta sync --lite`.
        """
        from importlib import resources

        content_dir = path / "content"
        meta_dir = path / "_meta"
        agents_dir = meta_dir / "agents"

        content_dir.mkdir(parents=True, exist_ok=True)
        meta_dir.mkdir(parents=True, exist_ok=True)
        agents_dir.mkdir(parents=True, exist_ok=True)

        # Map: target relative path → template resource path
        template_map = {
            "_meta/agents/SCHEMA.md":            "templates/agent/SCHEMA.md",
            "_meta/agents/PROJECT-WORKFLOW.md":  "templates/agent/PROJECT-WORKFLOW.md",
            "log.md":                            "templates/log.md",
        }
```

- [ ] **Step 3: Update `sync_meta()`'s two duplicated `file_map` dicts and dir setup**

Old:
```python
        # Determine target files based on lite flag
        if lite:
            file_map = {
                "_meta/system/SCHEMA.md":          "templates/system/SCHEMA.md",
                "_meta/system/RULES.md":           "templates/system/RULES.md",
                "_meta/system/README.md":          "templates/system/README.md",
                "_meta/agents/PROJECT-WORKFLOW.md": "templates/agent/PROJECT-WORKFLOW.md",
                "log.md":                          "templates/log.md",
            }
        else:
            # v0.7.6+: full set = lite 5종 + Tier 1 internal docs.
            # ⚠️ Tier 1 문서 (OPERATIONS, raven-policy, agent/*) 복사 시
            # Tier 1 leak 발생 → v0.6.39+ allow_tier1_leak=False면 critical.
            # 현재 정책 (v0.7.1+): 사용자 vault는 도구 표면만, Tier 1 leak ❌.
            # → full 옵션은 deprecated, lite와 동일하게 처리.
            file_map = {
                "_meta/system/SCHEMA.md":          "templates/system/SCHEMA.md",
                "_meta/system/RULES.md":           "templates/system/RULES.md",
                "_meta/system/README.md":          "templates/system/README.md",
                "_meta/agents/PROJECT-WORKFLOW.md": "templates/agent/PROJECT-WORKFLOW.md",
                "log.md":                          "templates/log.md",
            }
            if not force:
                # Safety: full set without force could overwrite user-edited
                # raven-internal files. Refuse unless force=True.
                for rel_target in file_map:
                    target = self.root / rel_target
                    if target.exists():
                        raise ValueError(
                            f"sync_meta(full): target exists at {target}. "
                            f"Refusing to overwrite without force=True. "
                            f"This protects user-edited raven-internal docs."
                        )

        system_dir = self.meta_root / "system"
        agent_dir = self.meta_root / "agent"
        system_dir.mkdir(parents=True, exist_ok=True)
        if not lite:
            agent_dir.mkdir(parents=True, exist_ok=True)
```

New:
```python
        # Determine target files based on lite flag
        # v0.7.65+: lite and full are now identical (2-file agent-only set) —
        # `full` no longer adds Tier 1 internal docs (that policy predates
        # v0.7.1's Tier 1 leak ban and was already dead code).
        file_map = {
            "_meta/agents/SCHEMA.md":            "templates/agent/SCHEMA.md",
            "_meta/agents/PROJECT-WORKFLOW.md":  "templates/agent/PROJECT-WORKFLOW.md",
            "log.md":                            "templates/log.md",
        }
        if not lite and not force:
            # Safety: full set without force could overwrite user-edited files.
            for rel_target in file_map:
                target = self.root / rel_target
                if target.exists():
                    raise ValueError(
                        f"sync_meta(full): target exists at {target}. "
                        f"Refusing to overwrite without force=True. "
                        f"This protects user-edited raven-internal docs."
                    )

        agents_dir = self.meta_root / "agents"
        agents_dir.mkdir(parents=True, exist_ok=True)
```

- [ ] **Step 4: Verify `Vault.create()` docstring already says `llm-wiki` copies "5-file Lite bootstrap"**

Read `raven/core/vault.py:167-174`. If it still says "5-file Lite bootstrap (SCHEMA + RULES + README + PROJECT-WORKFLOW + log.md)", update to:

```python
            profile: v0.6.38+ bootstrap profile selector. Default is "llm-wiki".
                - "llm-wiki" (default): project/agent-ready vault. Copies 2-file
                  Lite bootstrap (SCHEMA + PROJECT-WORKFLOW) + log.md.
                - "basic": Obsidian-style human-first vault. Only copies
                  WELCOME.md (1 file). No SCHEMA/RULES/agent workflow — user
                  opts in later if they want LLM Wiki patterns.
```

- [ ] **Step 5: Syntax check**

Run: `python3 -m py_compile raven/core/vault.py`
Expected: no output (success)

---

## Task 5: Update `raven/core/verify.py`

**Files:**
- Modify: `raven/core/verify.py:36-55`

- [ ] **Step 1: Update `LITE_BOOTSTRAP_FILES` and `TEMPLATE_MAP`**

Old:
```python
LITE_BOOTSTRAP_FILES: tuple[str, ...] = (
    "_meta/system/SCHEMA.md",
    "_meta/system/RULES.md",
    "_meta/system/README.md",
    "_meta/agents/PROJECT-WORKFLOW.md",
    "log.md",
)

# Template source paths inside `raven.core` package.
TEMPLATE_MAP: dict[str, str] = {
    "_meta/system/SCHEMA.md": "templates/system/SCHEMA.md",
    "_meta/system/RULES.md":  "templates/system/RULES.md",
    "_meta/system/README.md": "templates/system/README.md",
    "_meta/agents/PROJECT-WORKFLOW.md": "templates/agent/PROJECT-WORKFLOW.md",
    "log.md": "templates/log.md",
}
```

New:
```python
LITE_BOOTSTRAP_FILES: tuple[str, ...] = (
    "_meta/agents/SCHEMA.md",
    "_meta/agents/PROJECT-WORKFLOW.md",
    "log.md",
)

# Template source paths inside `raven.core` package.
TEMPLATE_MAP: dict[str, str] = {
    "_meta/agents/SCHEMA.md": "templates/agent/SCHEMA.md",
    "_meta/agents/PROJECT-WORKFLOW.md": "templates/agent/PROJECT-WORKFLOW.md",
    "log.md": "templates/log.md",
}
```

- [ ] **Step 2: Update the module docstring and `verify_bootstrap()` docstring**

In the module docstring (`verify.py:6`), change `"Each of the 5 Lite bootstrap files exists"` to `"Each of the 3 Lite bootstrap files exists"`, and `verify.py:7-8` change `"The 4 *template* files (SCHEMA.md, RULES.md, README.md, PROJECT-WORKFLOW.md)"` to `"The 2 *template* files (SCHEMA.md, PROJECT-WORKFLOW.md)"`.

In `verify_bootstrap()`'s docstring (`verify.py:164`), change:
```python
      - Static templates (SCHEMA, RULES, README, PROJECT-WORKFLOW): must exist AND be
```
to:
```python
      - Static templates (SCHEMA, PROJECT-WORKFLOW): must exist AND be
```

- [ ] **Step 3: Syntax check**

Run: `python3 -m py_compile raven/core/verify.py`
Expected: no output (success)

---

## Task 6: Update `tests/test_vault_create.py`

**Files:**
- Modify: `tests/test_vault_create.py`

- [ ] **Step 1: Update the module docstring (L1-5)**

Replace any mention of `"_meta/system/SCHEMA.md, _meta/system/RULES.md, log.md"` with `"_meta/agents/SCHEMA.md, _meta/agents/PROJECT-WORKFLOW.md, log.md"`.

- [ ] **Step 2: Apply this literal path replacement across the whole file**

Every occurrence of the old paths below no longer exists on disk. Replace each with the new path per this table (do a file-wide find of the old string and replace with the new one; where a test asserted BOTH `SCHEMA.md` and `RULES.md` exist/not-exist, keep only the `SCHEMA.md`-equivalent assertion since RULES content is merged into it — drop the now-redundant `RULES.md`/`README.md` line):

| Old literal | New literal |
|---|---|
| `_meta/system/SCHEMA.md` | `_meta/agents/SCHEMA.md` |
| `_meta/system/RULES.md` | `_meta/agents/SCHEMA.md` (merged — if a test already checks SCHEMA.md in the same function, delete this duplicate line instead) |
| `_meta/system/README.md` | `_meta/agents/PROJECT-WORKFLOW.md` (merged — if a test already checks PROJECT-WORKFLOW.md in the same function, delete this duplicate line instead) |

Apply this to: `test_bootstrap_copies_lite_templates` (L52-65, also re-verify the `"Source of Truth" in schema` / `"wikilink" in schema.lower()` assertions still hold — they do, both phrases exist in the new `templates/agent/SCHEMA.md` from Task 1), `test_bootstrap_lite_idempotent_does_not_overwrite` (L81-87, retarget the edited file to `_meta/agents/SCHEMA.md`), `test_no_bootstrap_creates_empty_dirs_but_no_template_files` (L93-115), `test_sync_meta_lite_default` (L129-148, the `result["copied"]` list should now only expect `["_meta/agents/SCHEMA.md", "_meta/agents/PROJECT-WORKFLOW.md", "log.md"]`), `test_sync_meta_lite_no_op_when_already_bootstrapped` (L151-163, same 3-item list in `skipped`), `test_sync_meta_does_not_overwrite_by_default` (L166-175, retarget edited file to `_meta/agents/SCHEMA.md`), `test_sync_meta_full_copies_raven_internals` (L178-200, same 3-item `copied` list — per Task 4 Step 3, `full` now equals `lite`), `test_sync_meta_full_refuses_to_overwrite_without_force` (L203-215, retarget to `_meta/agents/SCHEMA.md`), `test_clone_copies_content_only_with_data_only` (L265-285, retarget to `_meta/agents/SCHEMA.md`), `test_clone_copies_meta_by_default` (L288-301, retarget to `_meta/agents/SCHEMA.md`, drop the RULES.md line).

- [ ] **Step 3: Run the file**

Run: `scripts/.venv/bin/python -m pytest tests/test_vault_create.py -v`
Expected: all PASS

---

## Task 7: Update `tests/test_bootstrap_verify.py`

**Files:**
- Modify: `tests/test_bootstrap_verify.py`

- [ ] **Step 1: Fix the file-count and file-set assertions**

| Location | Old | New |
|---|---|---|
| `test_lite_bootstrap_files_constant_lists_5_files` (L61-72) | `assert set(LITE_BOOTSTRAP_FILES) == {"_meta/system/SCHEMA.md", "_meta/system/RULES.md", "_meta/system/README.md", "_meta/agents/PROJECT-WORKFLOW.md", "log.md"}` (rename test to `test_lite_bootstrap_files_constant_lists_3_files`) | `assert set(LITE_BOOTSTRAP_FILES) == {"_meta/agents/SCHEMA.md", "_meta/agents/PROJECT-WORKFLOW.md", "log.md"}` |
| `test_verify_bootstrap_fresh_vault_is_ok` (L109) | `assert len(result.checks) == 5` | `assert len(result.checks) == 3` |
| `test_verify_bootstrap_handles_missing_directory` (L182, L184) | `assert len(result.checks) == 5` | `assert len(result.checks) == 3` (L184's `assert result.missing == list(LITE_BOOTSTRAP_FILES)` needs no change — it already derives from the constant) |
| `test_cli_vault_verify_json_output` (L304) | `assert len(data["checks"]) == 5` | `assert len(data["checks"]) == 3` |
| `test_api_verify_vault_bootstrap_endpoint` (L321) | `assert len(payload["checks"]) == 5` | `assert len(payload["checks"]) == 3` |

- [ ] **Step 2: Retarget the file paths used to inject corruption/missing/mismatch**

| Test | Old path touched | New path |
|---|---|---|
| `test_verify_bootstrap_detects_missing_file` (L137) | `_meta/system/SCHEMA.md` | `_meta/agents/SCHEMA.md` |
| `test_verify_bootstrap_detects_content_mismatch` (L155) | `_meta/system/RULES.md` | `_meta/agents/PROJECT-WORKFLOW.md` |
| `test_verify_bootstrap_detects_corrupt_file` (L167) | `_meta/system/RULES.md` | `_meta/agents/PROJECT-WORKFLOW.md` |
| `test_vault_create_does_not_raise_on_corrupt_template` (L250) | `_meta/system/README.md` | `_meta/agents/PROJECT-WORKFLOW.md` |
| `test_cli_vault_verify_detects_corruption` (L285, L290) | `_meta/system/SCHEMA.md`, assert `"SCHEMA.md" in result.stdout` | `_meta/agents/SCHEMA.md`, assertion string unchanged (still `"SCHEMA.md" in result.stdout`) |
| `test_api_verify_returns_409_on_mismatch` (L330, L337) | `_meta/system/SCHEMA.md`, `bad["_meta/system/SCHEMA.md"]["status"]` | `_meta/agents/SCHEMA.md`, `bad["_meta/agents/SCHEMA.md"]["status"]` |

- [ ] **Step 3: Run the file**

Run: `scripts/.venv/bin/python -m pytest tests/test_bootstrap_verify.py -v`
Expected: all PASS

---

## Task 8: Rewrite `tests/test_v0_7_1_lite_bootstrap_surface.py`

**Files:**
- Modify: `tests/test_v0_7_1_lite_bootstrap_surface.py`

The old file's premise (a standalone "Vault User Guide" README.md + a separate SCHEMA.md) no longer holds — `README.md`'s content is absorbed into `PROJECT-WORKFLOW.md`. Replace the whole file.

- [ ] **Step 1: Replace the entire file content**

```python
"""v0.7.65+ — Lite bootstrap 2-file agent-only surface 회귀 가드.

v0.7.65 재설계: `_meta/system/{SCHEMA,RULES,README}.md` (3개) →
`_meta/agents/SCHEMA.md` (데이터 계약) + `_meta/agents/PROJECT-WORKFLOW.md`
(운영 사실) 2개로 병합. 사람 안내 톤 제거, 다른 에이전트 프로필의 자가평가
기준(Hermes Constitution) 제거, "이 문서에 없는 것" 경계 선언 추가.

회귀 가드:
  1. 옛 `_meta/system/{SCHEMA,RULES,README}.md` 템플릿 파일이 존재하지 않음
  2. 새 SCHEMA.md에 vendor 예시 / 도메인 가정(karpathy) 0회
  3. 새 SCHEMA.md가 데이터 계약 핵심 내용을 포함 (type 9종, wikilink, raw 권한)
  4. 새 PROJECT-WORKFLOW.md에 vendor 예시 / Hermes Constitution 0회
  5. 새 PROJECT-WORKFLOW.md가 운영 사실 핵심 내용을 포함 (MCP 매핑, 저장 신호 4가지, 체크리스트)
  6. 새 PROJECT-WORKFLOW.md에 "이 문서에 없는 것" 경계 선언 존재
  7. PROJECT-WORKFLOW.md는 templates/agent/ 한 곳에만 존재
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OLD_SYSTEM_SCHEMA = ROOT / "raven" / "core" / "templates" / "system" / "SCHEMA.md"
OLD_SYSTEM_RULES = ROOT / "raven" / "core" / "templates" / "system" / "RULES.md"
OLD_SYSTEM_README = ROOT / "raven" / "core" / "templates" / "system" / "README.md"
NEW_SCHEMA = ROOT / "raven" / "core" / "templates" / "agent" / "SCHEMA.md"
NEW_PROJECT_WORKFLOW = ROOT / "raven" / "core" / "templates" / "agent" / "PROJECT-WORKFLOW.md"

FORBIDDEN_VENDORS = ("Codex", "Claude Code", "Cursor", "Antigravity", "agy")
FORBIDDEN_AGENT_SOUL_TERMS = ("Hermes Constitution", "자가 평가 기준", "Self-Evaluation")


def _assert_no_terms(content: str, terms: tuple, file_label: str) -> None:
    for term in terms:
        assert term not in content, (
            f"{file_label} has forbidden term '{term}'"
        )


def test_old_system_lite_files_removed() -> None:
    assert not OLD_SYSTEM_SCHEMA.exists(), "old system/SCHEMA.md must be removed (merged into agent/SCHEMA.md)"
    assert not OLD_SYSTEM_RULES.exists(), "old system/RULES.md must be removed (merged into agent/SCHEMA.md)"
    assert not OLD_SYSTEM_README.exists(), "old system/README.md must be removed (merged into agent/PROJECT-WORKFLOW.md)"


def test_new_schema_no_vendor_or_domain_assumptions() -> None:
    content = NEW_SCHEMA.read_text(encoding="utf-8")
    _assert_no_terms(content, FORBIDDEN_VENDORS, "agent/SCHEMA.md")
    _assert_no_terms(content, ("karpathy", "Karpathy"), "agent/SCHEMA.md")


def test_new_schema_has_data_contract_content() -> None:
    content = NEW_SCHEMA.read_text(encoding="utf-8")
    assert "Type Taxonomy" in content
    for t in ("concept", "person", "comparison", "project", "tool", "rule", "query", "journal", "issue"):
        assert t in content
    assert "wikilink" in content.lower()
    assert "raw/ 권한" in content
    assert "페이지 템플릿" in content


def test_new_project_workflow_no_vendor_or_agent_soul_content() -> None:
    content = NEW_PROJECT_WORKFLOW.read_text(encoding="utf-8")
    _assert_no_terms(content, FORBIDDEN_VENDORS, "agent/PROJECT-WORKFLOW.md")
    _assert_no_terms(content, FORBIDDEN_AGENT_SOUL_TERMS, "agent/PROJECT-WORKFLOW.md")


def test_new_project_workflow_has_operating_facts() -> None:
    content = NEW_PROJECT_WORKFLOW.read_text(encoding="utf-8")
    assert "MCP 도구" in content
    assert "재사용 가능성" in content
    assert "인수인계 필요성" in content
    assert "결정 근거" in content
    assert "실패/리스크 기록" in content
    assert "체크리스트" in content
    assert "BLUF" in content


def test_new_project_workflow_has_boundary_declaration() -> None:
    content = NEW_PROJECT_WORKFLOW.read_text(encoding="utf-8")
    assert "이 문서에 없는 것" in content
    assert "검색 판단" in content
    assert "정리/폐기 판단" in content


def test_project_workflow_is_only_in_agent_template() -> None:
    agents_plural_dir = ROOT / "raven" / "core" / "templates" / "agents"  # 옛 오타 path
    assert NEW_PROJECT_WORKFLOW.exists(), f"{NEW_PROJECT_WORKFLOW} not found"
    assert not agents_plural_dir.exists(), f"{agents_plural_dir} should NOT exist (path consolidation)"
```

- [ ] **Step 2: Run the file**

Run: `scripts/.venv/bin/python -m pytest tests/test_v0_7_1_lite_bootstrap_surface.py -v`
Expected: all PASS

---

## Task 9: Update `tests/test_tier_boundary.py`

**Files:**
- Modify: `tests/test_tier_boundary.py`

- [ ] **Step 1: Update the two hardcoded whitelist sets**

`test_lite_bootstrap_files_size_matches_documented_whitelist` (L88-93) and `test_bootstrap_path_constants_use_user_surface_dirs` (L211-216) both hardcode:

Old:
```python
{
    "_meta/system/SCHEMA.md",
    "_meta/system/RULES.md",
    "_meta/system/README.md",
    "_meta/agents/PROJECT-WORKFLOW.md",
    "log.md",
}
```

New:
```python
{
    "_meta/agents/SCHEMA.md",
    "_meta/agents/PROJECT-WORKFLOW.md",
    "log.md",
}
```

- [ ] **Step 2: Update the docstring Tier 2 list (L8-13) to match**

- [ ] **Step 3: Run the file**

Run: `scripts/.venv/bin/python -m pytest tests/test_tier_boundary.py -v`
Expected: all PASS

---

## Task 10: Update `tests/test_cli.py`

**Files:**
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Apply path replacements**

| Test (line) | Old assertion target | New assertion target |
|---|---|---|
| `test_cli_vault_create_bootstrap` (L50-51) | `_meta/system/SCHEMA.md` and `_meta/system/RULES.md` exist | only assert `_meta/agents/SCHEMA.md` exists (drop the RULES.md line) |
| `test_cli_vault_create_no_bootstrap` (L67) | `_meta/system/SCHEMA.md` does not exist | `_meta/agents/SCHEMA.md` does not exist |
| meta-sync-exists test around L232-239 | `_meta/system/SCHEMA.md`, `RULES.md`, `README.md`, `_meta/agents/PROJECT-WORKFLOW.md` all exist | `_meta/agents/SCHEMA.md`, `_meta/agents/PROJECT-WORKFLOW.md` exist (drop the other two lines) |
| `test_cli_meta_sync_does_not_overwrite_by_default` (L247) | edits `_meta/system/RULES.md` | edits `_meta/agents/SCHEMA.md` |
| `test_cli_meta_sync_json_out` (L263-266) | asserts all 4 old paths `in data["copied"]` | asserts `["_meta/agents/SCHEMA.md", "_meta/agents/PROJECT-WORKFLOW.md", "log.md"]` all `in data["copied"]` |
| `test_cli_meta_sync_full_with_force` (L284-292) | asserts all 4 old paths exist | asserts `_meta/agents/SCHEMA.md` and `_meta/agents/PROJECT-WORKFLOW.md` exist |
| `test_cli_vault_clone_*` (L315, L333, L346, L360) | assert `_meta/system/SCHEMA.md` exists/not-exists | assert `_meta/agents/SCHEMA.md` exists/not-exists |

- [ ] **Step 2: Run the file**

Run: `scripts/.venv/bin/python -m pytest tests/test_cli.py -v`
Expected: all PASS

---

## Task 11: Update `tests/test_raven_root.py` and `tests/test_api.py`

**Files:**
- Modify: `tests/test_raven_root.py:69-71`
- Modify: `tests/test_api.py:55-56,68`

- [ ] **Step 1: `test_raven_root.py` — `test_create_vault_auto_creates_directory`**

Old: asserts `_meta/system/SCHEMA.md`, `_meta/system/RULES.md`, `_meta/system/README.md` all exist.
New: assert `_meta/agents/SCHEMA.md` and `_meta/agents/PROJECT-WORKFLOW.md` exist.

- [ ] **Step 2: `test_api.py` — `test_api_vault_create_with_bootstrap` and `test_api_vault_create_no_bootstrap`**

Old: asserts `_meta/system/SCHEMA.md` and `_meta/system/RULES.md` exist / do not exist.
New: assert `_meta/agents/SCHEMA.md` exists / does not exist.

- [ ] **Step 3: Run both files**

Run: `scripts/.venv/bin/python -m pytest tests/test_raven_root.py tests/test_api.py -v`
Expected: all PASS

---

## Task 12: Delete `tests/test_self_eval_criteria_sync.py`

**Files:**
- Delete: `tests/test_self_eval_criteria_sync.py`

This test's entire premise is that `AGENTS.md` §15 and `PROJECT-WORKFLOW.md` §10 ("에이전트 자가 평가 기준") stay in sync. Per the approved spec, `PROJECT-WORKFLOW.md` §10 (the Hermes-Constitution-referencing self-eval section) is deleted outright — it was agent-soul content that doesn't belong in vault-injected docs. `AGENTS.md` §15 is untouched (out of scope — it's Raven-codebase-internal, not vault content), so it becomes a standalone section with no vault-side counterpart. That's an intentional, accepted consequence of the approved design, not a bug.

- [ ] **Step 1: Delete the test file**

```bash
git rm tests/test_self_eval_criteria_sync.py
```

- [ ] **Step 2: Confirm no other test imports it**

Run: `grep -rl "test_self_eval_criteria_sync" tests/ raven/ 2>/dev/null`
Expected: no output (empty)

---

## Task 13: Update `tests/test_basic_profile_bootstrap.py` docstring (cosmetic)

**Files:**
- Modify: `tests/test_basic_profile_bootstrap.py:7`

- [ ] **Step 1: Update the stale comment**

Old: `"llm-wiki (project/agent-ready): SCHEMA+RULES+AGENTS+PROJECT-WORKFLOW+log.md (5종)"`
New: `"llm-wiki (project/agent-ready): SCHEMA+PROJECT-WORKFLOW+log.md (2종+log.md)"`

No test logic changes — this file's actual assertions don't touch the affected paths.

- [ ] **Step 2: Run the file**

Run: `scripts/.venv/bin/python -m pytest tests/test_basic_profile_bootstrap.py -v`
Expected: all PASS (unchanged)

---

## Task 14: Run the full test suite

**Files:** none (verification task)

- [ ] **Step 1: Run everything**

Run: `scripts/.venv/bin/python -m pytest tests/ -q`
Expected: all PASS, 0 failures. If anything outside the files touched in Tasks 6-13 fails, it means the grep sweep in the investigation phase missed a reference — grep for the failing literal path string across `tests/` and `raven/` and fix it the same way (retarget `_meta/system/{SCHEMA,RULES,README}.md` → `_meta/agents/{SCHEMA,PROJECT-WORKFLOW}.md`).

- [ ] **Step 2: Commit**

```bash
git add raven/core/vault.py raven/core/verify.py raven/core/templates/agent/SCHEMA.md raven/core/templates/agent/PROJECT-WORKFLOW.md
git add tests/test_vault_create.py tests/test_bootstrap_verify.py tests/test_v0_7_1_lite_bootstrap_surface.py tests/test_tier_boundary.py tests/test_cli.py tests/test_raven_root.py tests/test_api.py tests/test_basic_profile_bootstrap.py
git rm raven/core/templates/system/SCHEMA.md raven/core/templates/system/RULES.md raven/core/templates/system/README.md 2>/dev/null || true
git rm tests/test_self_eval_criteria_sync.py 2>/dev/null || true
git commit -m "$(cat <<'EOF'
refactor(vault): collapse Lite bootstrap to 2 agent-only files

Merge _meta/system/{SCHEMA,RULES,README}.md into _meta/agents/SCHEMA.md
(data contract) and _meta/agents/PROJECT-WORKFLOW.md (operating facts).
Drop human-manual framing and the Hermes-Constitution self-eval section
(agent-soul content); add an explicit boundary declaring what agents
should carry in their own memory instead of the vault.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 15: Update `templates/system/WELCOME.md` pointer text

**Files:**
- Modify: `raven/core/templates/system/WELCOME.md`

- [ ] **Step 1: Update the "want more structure" pointer**

Old:
```
If you want the full Lite bootstrap (SCHEMA.md / RULES.md / README.md /
PROJECT-WORKFLOW.md / log.md), re-create with `--profile llm-wiki`:
```

New:
```
If you want the full Lite bootstrap (SCHEMA.md / PROJECT-WORKFLOW.md /
log.md), re-create with `--profile llm-wiki`:
```

- [ ] **Step 2: Verify**

Run: `grep -n "RULES.md\|README.md" raven/core/templates/system/WELCOME.md`
Expected: no output (empty)

---

## Task 16: Fix `raven/mcp/resources.py` `wiki_schema` resource

**Files:**
- Modify: `raven/mcp/resources.py:80-88`

This resource currently reads `<vault>/SCHEMA.md` at the vault root, which never existed (dead code) — the real Lite bootstrap path was `_meta/system/SCHEMA.md`, now `_meta/agents/SCHEMA.md`. Fix the bug and the path in the same change.

- [ ] **Step 1: Fix the resource**

Old:
```python
    # ─── wiki://{vault}/schema ───
    @mcp.resource("wiki://{vault}/schema")
    def wiki_schema(vault: str) -> str:
        """Raw text of SCHEMA.md."""
        schema_path = resolve_vault_path(vault) / "SCHEMA.md"
        if not schema_path.exists():
            return "(no SCHEMA.md at vault root)"
        return schema_path.read_text(encoding="utf-8")
```

New:
```python
    # ─── wiki://{vault}/schema ───
    @mcp.resource("wiki://{vault}/schema")
    def wiki_schema(vault: str) -> str:
        """Raw text of _meta/agents/SCHEMA.md."""
        schema_path = resolve_vault_path(vault) / "_meta" / "agents" / "SCHEMA.md"
        if not schema_path.exists():
            return "(no _meta/agents/SCHEMA.md in this vault)"
        return schema_path.read_text(encoding="utf-8")
```

- [ ] **Step 2: Update the module docstring path reference (`resources.py:9`)**

Old: `    wiki://{vault}/schema             — SCHEMA.md text`
New: `    wiki://{vault}/schema             — _meta/agents/SCHEMA.md text`

- [ ] **Step 3: Manually verify against a real vault**

Run:
```bash
raven vault create /tmp/mcp-schema-check --path /tmp/mcp-schema-check-data 2>/dev/null || true
source scripts/.venv/bin/activate
python3 -c "
from raven.mcp.resources import register_resources
from mcp.server.fastmcp import FastMCP
mcp = FastMCP('wiki')
register_resources(mcp)
print('resource registered OK')
"
```
Expected: `resource registered OK`, no traceback. (Full end-to-end resource fetch is covered by Task 21's manual verification.)

---

## Task 17: Update `raven/api/server.py` bootstrap field description

**Files:**
- Modify: `raven/api/server.py:517-522`

- [ ] **Step 1: Update the Pydantic field description**

Old:
```python
            "Lite bootstrap policy: if True, copy ONLY user-facing essentials "
            "(SCHEMA, RULES, README, PROJECT-WORKFLOW, log.md). Tier 1 raven-internal "
            "docs (OPERATIONS, agent/*, raven-policy) are NEVER auto-copied. "
            "Use `raven docs` command to read raven-internal docs."
```

New:
```python
            "Lite bootstrap policy: if True, copy ONLY agent-facing essentials "
            "(SCHEMA, PROJECT-WORKFLOW, log.md). Tier 1 raven-internal "
            "docs (OPERATIONS, agent/*, raven-policy) are NEVER auto-copied. "
            "Use `raven docs` command to read raven-internal docs."
```

- [ ] **Step 2: Syntax check**

Run: `python3 -m py_compile raven/api/server.py`
Expected: no output (success)

---

## Task 18: Update `dashboard/src/routes/VaultManage.tsx` confirm dialog text

**Files:**
- Modify: `dashboard/src/routes/VaultManage.tsx:718`

- [ ] **Step 1: Update the file list in the confirm dialog copy**

Old:
```tsx
            <strong>{confirmBootstrap}</strong> 보관소의 지침 파일들(<code>SCHEMA.md</code>, <code>RULES.md</code>, <code>README.md</code>, <code>PROJECT-WORKFLOW.md</code>, <code>log.md</code>)을 Raven 소스코드에 포함된 최신 템플릿 원본으로 덮어씁니다.<br/>
```

New:
```tsx
            <strong>{confirmBootstrap}</strong> 보관소의 지침 파일들(<code>SCHEMA.md</code>, <code>PROJECT-WORKFLOW.md</code>, <code>log.md</code>)을 Raven 소스코드에 포함된 최신 템플릿 원본으로 덮어씁니다.<br/>
```

- [ ] **Step 2: Type-check the dashboard**

Run: `cd dashboard && npx tsc -b --noEmit`
Expected: no errors

---

## Task 19: Update root `README.md` Lite bootstrap table

**Files:**
- Modify: `README.md` (Lite bootstrap section, currently listing 5 files)

- [ ] **Step 1: Update the table**

Old:
```markdown
새 vault를 `--profile llm-wiki`로 만들면 다음 **5종**이 vault 폴더에 자동 복사됩니다:

| 파일 | 용도 |
|---|---|
| `_meta/system/SCHEMA.md` | frontmatter / type / tag / wikilink 규약 |
| `_meta/system/RULES.md` | 편집 5규칙 |
| `_meta/system/README.md` | vault 운영자 가이드 ("Vault User Guide", v0.7.35+ 리네임) |
| `_meta/agents/PROJECT-WORKFLOW.md` | 프로젝트 작업 에이전트 공통 워크플로우 |
| `log.md` | 작업 이력 (append-only) |
```

New:
```markdown
새 vault를 `--profile llm-wiki`(기본값)로 만들면 다음 **2종 + log.md**가
vault 폴더에 자동 복사됩니다. 사람 안내문은 없음 — 에이전트가 이 vault를
Raven의 LLM Wiki 방식으로 운영하는 데 필요한 사실만 담습니다 (v0.7.65+):

| 파일 | 용도 |
|---|---|
| `_meta/agents/SCHEMA.md` | 데이터 계약: frontmatter/type/tag/wikilink/slug/raw 권한/lint 14개 |
| `_meta/agents/PROJECT-WORKFLOW.md` | 운영 사실: 읽기 순서, MCP 도구 매핑, 권한 매트릭스, 저장 결정 4신호, 멀티 에이전트 협업 규칙 |
| `log.md` | 작업 이력 (append-only) |
```

- [ ] **Step 2: Verify no other README section still references the old 5-file set**

Run: `grep -n "system/SCHEMA.md\|system/RULES.md\|system/README.md" README.md`
Expected: no output (empty)

---

## Task 20: Update `AGENTS.md` §4 Tier 2 table

**Files:**
- Modify: `AGENTS.md:14` (intro line)
- Modify: `AGENTS.md:89-97` (Tier 2 table)

- [ ] **Step 1: Update the intro reference at L14**

Old: `> 사람 운영자 가이드는 \`README.md\`, vault 데이터 운영 규칙은 사용자 vault 내부 \`_meta/system/README.md\` 참조 (Lite bootstrap으로 자동 복사됨).`
New: `> 사람 운영자 가이드는 \`README.md\`. vault 데이터 운영 규칙(에이전트용)은 사용자 vault 내부 \`_meta/agents/PROJECT-WORKFLOW.md\` 참조 (Lite bootstrap으로 자동 복사됨). 사람 안내문은 vault에 주입하지 않음 (v0.7.65+).`

- [ ] **Step 2: Update the Tier 2 table**

Old:
```markdown
### Tier 2 — user vault (Lite bootstrap ✅, v0.7.3+: 5종 표면화)

```
| `_meta/system/SCHEMA.md`    → vault 데이터 구조 (frontmatter/type/tag/wikilink) — 사용자 표면
|_meta/system/RULES.md     → 편집 규칙 — 사용자 표면
|_meta/system/README.md    → "Vault User Guide" — 도구 표면 (v0.7.35+ 리네임, v0.7.1+ 재작성)
|_meta/agents/PROJECT-WORKFLOW.md → 프로젝트 작업 에이전트 공통 워크플로우 — 도구 표면
|log.md                    → 작업 이력 (append-only) — 사용자 표면
```

→ **v0.7.3+ Lite bootstrap 5종 모두 도구 표면만**. Raven 내부 정책 (Tier 1 leak, vendor 예시, OPERATIONS/agent/raven-policy 복사 금지) ❌. 사용자가 vault에서 자기 프로덕트를 자유롭게 문서화.
```

New:
```markdown
### Tier 2 — user vault (Lite bootstrap ✅, v0.7.65+: 2종 + log.md, agent-only)

```
|_meta/agents/SCHEMA.md            → 데이터 계약 (frontmatter/type/tag/wikilink/raw 권한/lint) — 에이전트 표면
|_meta/agents/PROJECT-WORKFLOW.md  → 운영 사실 (읽기순서/MCP매핑/권한/저장신호/협업규칙) — 에이전트 표면
|log.md                            → 작업 이력 (append-only) — 인프라
```

→ **v0.7.65+ Lite bootstrap은 사람 안내문 없음, 에이전트가 이 vault/도구를 운영하는 데 필요한 사실만**. "에이전트 스스로 판단/기억해야 할 영역"(검색 시점, 정리 시점, 글쓰기 철학)은 vault에 담지 않고 명시적으로 경계 선언만 함 — 에이전트 자신의 soul/memory에 있어야 함. Raven 내부 정책 (Tier 1 leak, vendor 예시, OPERATIONS/agent/raven-policy 복사 금지, 다른 에이전트 프로필의 constitution) ❌.
```

- [ ] **Step 3: Verify**

Run: `grep -n "system/SCHEMA.md\|system/RULES.md\|system/README.md" AGENTS.md`
Expected: no output (empty)

---

## Task 21: Manual end-to-end verification

**Files:** none (manual verification task)

- [ ] **Step 1: Create a fresh vault with the default profile**

```bash
source scripts/.venv/bin/activate
rm -rf /tmp/bootstrap-redesign-check
raven vault create bootstrap-redesign-check /tmp/bootstrap-redesign-check
find /tmp/bootstrap-redesign-check/_meta -type f
```

Expected: exactly `_meta/agents/SCHEMA.md` and `_meta/agents/PROJECT-WORKFLOW.md`. No `_meta/system/` directory at all.

- [ ] **Step 2: Verify bootstrap self-check passes**

```bash
raven vault verify bootstrap-redesign-check
```

Expected: `3/3 ok` (or equivalent "ok" summary), no missing/mismatch entries.

- [ ] **Step 3: Verify `raven build` still works against the new vault**

```bash
raven build --vault bootstrap-redesign-check
```

Expected: exits 0, no traceback.

- [ ] **Step 4: Verify the Dashboard "지침 당겨오기" button (manual, ask the user to check visually)**

Start the local stack (`make up` if not already running), open `http://localhost:5173/vault/manage`, click "지침 당겨오기" for `bootstrap-redesign-check`, confirm the dialog now lists only `SCHEMA.md`, `PROJECT-WORKFLOW.md`, `log.md` and the operation succeeds.

- [ ] **Step 5: Clean up the throwaway vault**

```bash
raven vault remove bootstrap-redesign-check --force
rm -rf /tmp/bootstrap-redesign-check
```

---

## Task 22: Final commit for docs/dashboard/mcp changes

**Files:** none (commit task — covers Tasks 15-20's changes; Task 14 already committed the core code+test changes)

- [ ] **Step 1: Review the diff**

```bash
git status --short
git diff -- raven/core/templates/system/WELCOME.md raven/mcp/resources.py raven/api/server.py dashboard/src/routes/VaultManage.tsx README.md AGENTS.md
```

- [ ] **Step 2: Commit**

```bash
git add raven/core/templates/system/WELCOME.md raven/mcp/resources.py raven/api/server.py dashboard/src/routes/VaultManage.tsx README.md AGENTS.md
git commit -m "$(cat <<'EOF'
docs: sync WELCOME.md, MCP schema resource, API/dashboard copy, README/AGENTS.md to 2-file bootstrap

Follow-up to the vault bootstrap redesign (2 agent-only files + log.md):
fixes the dead wiki_schema MCP resource path bug at the same time
(it was reading a vault-root path that never existed).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Self-Review Notes

- **Spec coverage**: §2.1/§2.2 file outlines → Tasks 1-2. §2.3 removals → verified absent via grep steps in Tasks 1, 2, 8. §3 boundary section → Task 2 + Task 8 regression test. §4 impact table → Tasks 3-20 cover every row (vault.py, verify.py, templates, WELCOME.md, api/server.py, mcp/resources.py, VaultManage.tsx, README.md, AGENTS.md, tests). §5 out-of-scope items (`basic` profile's WELCOME.md content itself, MCP `instructions=`, profile default) are explicitly NOT touched by any task. §6 verification criteria → Task 21.
- **New finding surfaced during planning, not in original spec**: `tests/test_self_eval_criteria_sync.py` existed solely to keep `AGENTS.md` §15 in sync with the vault-side self-eval section being deleted. Task 12 deletes it and documents why; `AGENTS.md` §15 itself is left untouched (out of spec scope) and becomes a standalone, no-longer-vault-synced section as an accepted side effect.
- **Placeholder scan**: no TBD/TODO; every step has literal file paths, literal old/new strings, or complete file content.
- **Type/name consistency check**: `_LITE_BOOTSTRAP_FILES` (vault.py) and `LITE_BOOTSTRAP_FILES`/`TEMPLATE_MAP` (verify.py) use the same 3 literal paths across Tasks 4-5; the merged file is called `SCHEMA.md` (not `CONTRACT.md` or similar) consistently across every task and test.
