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
- 시스템: `system`, `tool`, `ui`, `search`, `viewer`, `schema`, `mcp`, `dashboard`, `meta`, `workflow`
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
# {Rule Name / Decision Title}

> {BLUF: What this rule/decision is, 1 line}

## 맥락 (Optional)
{결정이 필요하게 된 배경과 문제 상황 — 결정 기록(decision record)일 때 작성.}

## 규칙 / 결정
{구체적인 규칙 세부사항, 또는 최종 선택과 핵심 논거. 결론을 먼저 제시하고 근거를 붙입니다.}

## 적용 범위 / 영향 (Optional)
{규칙이 적용되는 대상과 예외, 또는 이 결정이 시스템/프로젝트에 미치는 영향.}

## 관련
- [[related-page]] — 관련 설계 문서 또는 후속 작업 페이지
```

> 결정 기록(decision record)은 별도 type이 아니라 이 `rule` 템플릿의 흔한 사용 패턴입니다.

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
- [[alternative-tool]] — 대체 가능한 다른 도구
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
