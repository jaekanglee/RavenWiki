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
| `aliases: [old-slug]` | 페이지 개명/병합 시 옛 slug 보존 | — |

**모순 발견 시 절차**: 어느 쪽도 덮어쓰지 말고, 양쪽 페이지에 `contested: true` +
`contradictions`로 상호 링크한 뒤 원인을 log.md에서 역추적한다.

**aliases 사용 시점**: 페이지를 개명하거나 중복 페이지를 병합할 때, 남는 페이지의
`aliases`에 사라지는 slug를 기록한다 (링크 추적성 보존).

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

## Status Taxonomy (4종) — ADR-2026-07-06 §1.1

> **사용자 north star (2026-07-06 확인)**: "사람이 최초 작성한 문서를, 에이전트가 스테일/모순/링크깨짐을
> 발견하여 갱신(부분 overwrite + provenance) 또는 격리(archive 이동) 액션으로 vault를 최신 정합화
> 상태로 유지한다." 본 상태 머신은 그 실행 기반.

모든 vault 페이지는 frontmatter `status:` 필드로 다음 4상태 중 하나를 갖는다 (생략 시 `current`).

| status | 의미 | 진입 트리거 | 검색·링크 노출 |
|---|---|---|---|
| `current` | 사실 검증됨, 권위 있음 | 사람 최초 작성, 또는 에이전트 갱신 완료 | ✅ 정상 |
| `stale` | 90일+ 미검증 또는 사실 변경 의심 | `wiki_stale_detect` (MCP) / lint #7 | ⚠️ 헤더 경고 |
| `contested` | 다른 페이지와 모순 발견 | lint #5 (모순 룰) 자동 감지 | ⚠️ 헤더 경고, 양쪽 cross-link |
| `archived` | 격리됨, 더 이상 활성 페이지 아님 | `wiki_archive` (MCP) / 사람 CLI | ❌ 검색·그래프 제외, 전문은 `archive/<YYYY-MM-DD>/<slug>.md` 보존 |

### 전이 규칙

- `current ↔ stale`: 검증 결과에 따라 양방향. `evidence` 필수.
- `stale → archived`: 사람 승인 또는 자동 격리 정책 만족 시.
- `current ↔ contested`: 모순 발견/해소 시. **자동 전환 금지** — 사람이 명시적으로 `contested: true` 박거나 lint #5가 cross-link 증거 제시 시에만.
- `archived → current`: **사람 승인 필수** (에이전트 자율 복귀 ❌).

### 전이 기록

모든 상태 전이는 frontmatter `agents:` 리스트에 `{actor, action, at, evidence}` 1줄 append.

### 보조 필드 (선택)

```yaml
status: stale
last_verified: 2026-04-06T00:00:00Z   # ISO 8601 (stale 감지용)
archived_at: 2026-07-06T12:00:00Z     # archived 시 자동 stamp
archive_reason: stale_over_threshold  # 또는 user_request / factual_obsolete
```

### MCP 도구 (ADR §1.3)

- `wiki_stale_detect` (read): 후보 + evidence + suggested_action 반환
- `wiki_archive` (write/admin): `archive/<YYYY-MM-DD>/<slug>.md`로 이동 + frontmatter stamp
- `wiki_update` 확장: `revalidate=true` 시 `stale → current` 전이 + evidence 기록

### 본문 50%+ 재작성 가드 (ADR §1.3)

`wiki_update`는 본문 길이가 기존 본문의 1.5배 초과 시 거부 (`large_rewrite_blocked`).
north star "원문 보존 + 증분 누적"의 실행 가드. 신규 생성은 가드 우회.

### 가드 / 결정 위치

- **결정 문서**: `_meta/decisions/adr-2026-07-06-stale-update-isolate-loop.md` (ADR-2026-07-06)
- **구현**: `raven/mcp/tools/stale.py` + `raven/mcp/tools/write.py` (1.5배 가드)
- **시나리오 테스트**: `tests/scenarios/test_stale_loop.py` (13 시나리오 pass)

9종 외 새 타입 정의 금지.

## Tag Taxonomy

### Core (lint 대상 — 이 문서에 명시된 태그만)
- 시스템: `system`, `tool`, `ui`, `search`, `viewer`, `schema`, `mcp`, `dashboard`, `meta`, `workflow`, `index`, `home`
- 컨텐츠: `concept`, `person`, `comparison`, `project`, `rule`, `query`, `journal`, `issue`
- 상태: `draft`, `review`, `final`, `deprecated`, `orphan`

**lint 동작**: core에 없으면 🟡 warning ("not in core taxonomy").

### Custom (자유, lint 면제)
자기 도메인 태그 자유 사용.

### 승격 절차
같은 custom 태그가 3+ 페이지에서 쓰이면 lint #9가 "core 승격 추천"을 알린다.
에이전트는 이 문서를 직접 수정하지 말고(협업 규칙 §8) `type: issue` 문서로
승격을 발의한다 → 사람 승인 시 이 문서 Core 목록에 한 줄 추가.

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
| 8 | page size > 200줄 — 분할: 하위 주제를 새 페이지로 떼어내고 원 페이지에 wikilink, 병합 흔적은 `aliases`에 | 🔵 info |
| 9 | tag not in core taxonomy (custom 허용) + 3+ 사용 시 승격 추천 | 🔵 info |
| 10 | frontmatter 완전성 | 🔵 info |
| 11 | index 완전성 (FS vs DB) | 🟡 warning |
| 12 | log size > 500 entries | 🔵 info |
| 13 | cognitive governance | 🔵 info |
| 14 | tier integrity | 🔴 critical / 🟡 warning |

### System Areas (type 면제)

다음 경로는 시스템 자동 생성 영역으로, type 9종 면제 (lint #10 통과):

- `<vault>/_meta/**` — vault 운영 문서 (Tier 2 bootstrap)
- `<vault>/raw/**` — 사람 1차 운영 영역 (raw/ 정책 §7)
- `<vault>/content/_index/**` — 자동 카탈로그 (graph hub fan-out 방지, ADR-2026-07-04)
- `<vault>/content/index.md` — root 자동 카탈로그

→ 위 경로 페이지는 type 필드 없이도 lint #10 통과. 9종 정책은 사람이 작성하는 일반 페이지에 한정.

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
