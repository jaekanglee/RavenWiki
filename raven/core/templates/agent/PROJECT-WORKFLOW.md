---
title: Project Workflow — 사용자 정의 작업 흐름
created: 2026-06-30
updated: 2026-06-30
type: rule
tags: [system, workflow, meta]
audience: human, agent
confidence: high
---

# Project Workflow — 사용자 정의 작업 흐름

> 📌 **사람 + 에이전트 공통 가이드.** 이 vault에서 일할 때 (사람/에이전트 누구든) 다음을 따르세요.
>
> 🔧 **Tool note.** Raven은 이 문서의 내용을 강제하지 않습니다 — 사용자가 직접 작성/유지합니다.
> 다만 **에이전트에게 "이 vault에서 작업할 때 따라야 할 규칙"**을 알려주는 표준 위치입니다.

---

## 📌 1. 작성 가이드 — BLUF (Bottom Line Up First)

> 📝 **사람**: 모든 페이지 첫 줄에 결론/결정 1문장.
> 🤖 **Agent**: BLUF가 없으면 페이지 quality 떨어짐 → vault 노이즈 증가.

### 1.1 결론 (Conclusion)

> 📝 **사람**: 페이지 첫 줄에 무엇인지 1줄.
> 🤖 **Agent**: `[BLUF] {결론 1문장}` 패턴 권장.

- ✅ 예: `# harumoa 제품 백엔드 = Spring Boot 3.2 + Kotlin`
- ✅ 예: `# 2026-06-30 결정: API rate limit 100/min/user로 변경`
- ❌ 반: `# 메모` (무엇에 대한 메모?)

### 1.2 분업 (Division of Labor)

> 📝 **사람**: 사람/에이전트 각각 무엇을 하는지 결정.
> 🤖 **Agent**: 사람 review 영역 vs 자동 영역 구분 명확히.

- 사람: 결정(rule), 컨셉(concept), 사람(person) — 사람 review 후
- 에이전트: 저널(journal), 빌드/링크체크 — 자동 가능
- 자동화 스크립트: 마이그레이션, 백업, lint

### 1.3 트리거 (Triggers)

> 📝 **사람**: 어떤 신호 → 어떤 동작. 본인이 외울 수 있게.
> 🤖 **Agent**: 트리거 목록은 자동화 가능.

- 사용자 "X 정리해줘" → journal/concept 자동 작성 (사람 confirm)
- 새 raw/ 파일 → 자동 compile (raw → content/compiled)
- 12시간 idle → 자동 build + lint
- 새 결정 → 관련 concept/journal 페이지에 wikilink 자동 추가

### 1.4 금지 (Forbidden)

> 📝 **사람**: 이 팀/프로젝트에서 절대 안 되는 것.
> 🤖 **Agent**: 자기 검증 (lint가 catch 못 하는 것).

- ❌ 도메인 추측 (모르면 사용자에게 묻기)
- ❌ raw/ 자동 수정
- ❌ vault 외부 write
- ❌ 특정 vendor/tool 강요 (vendor-neutral)
- ❌ user vault 데이터 write (운영자 영역)

---

## 📝 2. 사람 우선 문서 원칙 (Human-First Writing)

> 📝 **사람**: 문서는 위키처럼 자연스럽게 읽혀야 합니다. 에이전트 운영 메타가 본문에 튀어나오면 읽기 어려워집니다.
> 🤖 **Agent**: 구조는 frontmatter와 얇은 섹션으로 확보하고, 본문은 자연어 중심으로 씁니다.

### 2.1 기본 원칙

- **frontmatter는 구조화**, 본문은 자연스러운 문장으로 작성
- **필수 섹션은 적게**: 보통 `요약`, `내용`, `관련` 정도면 충분
- **type마다 최소 차이만** 두고, 모든 문서를 ADR처럼 딱딱하게 만들지 말 것
- **사람이 먼저 읽는 제목** 사용, 영문 ID는 헤더 괄호나 frontmatter에서만 보조

### 2.2 본문에 과하게 노출하지 말 것

- ❌ `actor`, `run_id`, `tool`, `idempotency_key` 같은 운영 메타를 본문에 쓰기
- ❌ JSON, 체크리스트, 내부 추론 흔적을 본문 상단에 노출
- ❌ "에이전트가 판단했다" 같은 기계 중심 문장 반복
- ✅ 한 줄 요약 → 설명 → 관련 링크 순서 유지

### 2.3 최소 공통 뼈대

모든 타입에 완전 고정 템플릿을 강제하지 말고, 아래 3개 정도를 기본으로 삼습니다:

```
# {제목}

> {BLUF: 이 문서가 말하는 핵심 1문장}

## 내용
{사람이 읽기 쉬운 설명}

## 관련
- [[related-page]]
```

---

## 📝 3. 페이지 작성 템플릿 (Type 8종)

> 📝 **사람**: vault 자유지만 권장 구조.
> 🤖 **Agent**: 섹션 자동 생성 시 이 템플릿 따라.

### 📝 3.1 `concept` (Concept)

```
# {Concept Name}

> {BLUF: 1-line definition}

## 내용
{핵심 설명. 다른 개념과 연결되면 wikilink 추가.}

## 왜 중요한가
{2-3 lines. 이 개념이 왜 필요한지.}

## 반대 입장 / 한계
{필요할 때만. 항상 길게 쓸 필요 없음.}

## 관련
- [[related-concept-1]]
- [[related-concept-2]]
```

### 📝 3.2 `decision` (Decision)

```
# Decision: {Title}

> {BLUF: 1-line decision}

## 맥락
{Why this decision was needed.}

## 결정
{Final choice + reason. Pyramid principle — conclusion → rationale.}

## 영향
{What changed as a result.}

## 관련
{Next steps. wikilink to relevant pages.}
```

### 📝 3.3 `journal` (Journal / Daily Note)

```
# {YYYY-MM-DD} {Title}

> {BLUF: What happened today, 1 line}

## 한 일
- ...

## 메모
- 필요한 관찰 / 결정 / 이슈만 짧게

## 다음
- ...
```

### 📝 3.4 `rule` (Rule / Policy)

```
# {Rule Name}

> {BLUF: What this rule is, 1 line}

## 적용 범위
{Where it applies. Exceptions if any.}

## 규칙
{Detailed. wikilink to related pages.}

## 예외
{If any.}
```

### 📝 3.5 `person` (Person)

```
# {Name}

> {BLUF: Who they are, 1 line}

## 역할

## 주요 작업

## 관련
- [[project-x]]
- [[meeting-yyyy-mm-dd]]
```

### 📝 3.6 `tool` (Tool)

```
# {Tool Name}

> {BLUF: What this tool is, 1 line}

## 용도

## 사용법

## 대안

## 관련
```

### 📝 3.7 `comparison` (Comparison)

```
# {A} vs {B}

> {BLUF: Conclusion — which is better, 1 line}

## 기준
{Comparison axes.}

## Comparison
| Criteria | {A} | {B} |
|---|---|---|
| ... | ... | ... |

## 결론
{Which and why.}
```

### 📝 3.8 `query` (Question)

```
# Question: {Title}

> {BLUF: Core of the question, 1 line}

## 맥락
{Why this question arose.}

## 후보 답
- Candidate 1: ...
- Candidate 2: ...

## 열린 이슈
{Unresolved parts.}

## 관련
- [[related-page]]
```

### 📝 3.9 `project` (Project)

```
# Project: {Name}

> {BLUF: What this project is, 1 line}

## 목표

## 현재 상태

## 범위 / 비범위

## 관련
- [[decision-or-issue-page]]
```

---

## ✅ 4. 일관성 체크리스트 (Consistency Checklist)

페이지 작성 후 다음 5개 확인:

- [ ] **첫 줄이 결론/결정 1문장** (BLUF)
- [ ] **frontmatter**: `title`, `type`, `created`, `updated` 채워짐
- [ ] **type이 8종 중 하나** (`concept`, `person`, `comparison`, `project`, `tool`, `rule`, `query`, `journal`)
- [ ] **wikilink ≥ 1** (관련 페이지 연결)
- [ ] **본문이 사람 문장으로 읽힘** (운영 메타 / JSON / 내부 추론 흔적 노출 ❌)
- [ ] **저장 신호 4가지 통과** (재사용 가능성, 인수인계 필요성, 결정 근거, 실패/리스크)

→ 4가지 저장 신호 모두 "아니오"면 **저장하지 말 것** (vault = 신호 대 잡음비가 높은 공간).

---

## 🔗 5. 참고 (References)

- 📝 vault 운영 일반 규칙: `_meta/system/AGENTS.md` ("Vault User Guide")
- 🤖 데이터 구조: `_meta/system/SCHEMA.md`
- 🤖 편집 규칙: `_meta/system/RULES.md`
- 🤖 LLM Wiki +α 가이드: `docs/vault-patterns.md`

---

## 💡 6. 예시 (참고용, 사용자 팀에 맞게 수정)

```
# harumoa팀 워크플로우

## 결론
- 사람은 결정/원칙만
- 에이전트는 compile/journal/raw 정리
- 도메인 추측 ❌ (사용자에게 묻기)

## 분업
- 사람: 결정(rule), 컨셉(concept) 페이지
- 에이전트: 저널(journal) 자동, raw/ → content/ 컴파일

## 트리거
- 사용자: "X 정리해줘" → journal/concept 자동 작성
- 새 raw/ 파일 → 자동 compile (사람 confirm 후)

## 금지
- 도메인 추측 ❌
- raw/ 자동 수정 ❌
- vault 외부 write ❌
```

---

## 📌 7. 작성자 가이드 — 순수 자연어 헤더

> 📝 **사람**: 섹션 제목은 사람이 바로 읽히는 자연어를 우선합니다.
> 🤖 **Agent**: 영문 ID를 헤더에 노출하지 말고, 한글 제목과 문맥으로 구조를 따릅니다.

권장:

```
## 결론
## 분업
## 트리거
```

비권장:

```
## 결론 (BLUF)
## 분업 (Division)
```

→ 기계 식별용 영어 괄호는 시각적 노이즈가 되므로 문서 본문에서 제거합니다.

---

## ⚠️ 8. 폴더 구조 권장 (vault 자유지만 일관성)

- `content/` — 자유 (사용자)
- `content/decisions/` — 결정 페이지
- `content/concepts/` — 컨셉 페이지
- `content/journal/` — 저널/일지
- `content/issues/` — 이슈 분석
- `content/projects/` — 프로젝트별
- `content/people/` — 사람별
- `raw/` — source material (LLM Wiki +α 켠 경우)

→ vault가 이미 다른 구조면 **그 구조 따르기** (강제 ❌).
