---
title: Project Workflow — 사용자 정의 작업 흐름
created: 2026-06-30
updated: 2026-07-01
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
- **필수 섹션은 최소화**: 보통 `요약`, `내용`, `관련` 정도의 최소 공통 뼈대만 사용하고, 각 타입별 상세 섹션은 선택 사항(Optional)입니다.
- **빈 섹션 생성 금지 (Anti-Placeholder)**: 템플릿에 명시된 상세 섹션이라도, 작성할 내용이 없을 경우 `TBD`, `N/A`, `없음` 등으로 채우지 말고 **해당 섹션 자체를 삭제**하여 문서의 노이즈를 줄입니다.
- **사람이 먼저 읽는 제목 사용**: 제목에 날짜(`YYYY-MM-DD`)나 기계적 분류 접두사(`Decision:`, `Question:`, `Project:`)를 포함하지 않습니다. 프런트매터의 `created`와 `type`이 이미 구조적 정보를 담고 있습니다.

### 2.2 맥락이 있는 위키링크 (Contextualization)

- 단순히 하단에 `[[link]]` 목록만 나열하는 포맷을 지양합니다.
- 각 위키링크 옆에는 **이 링크가 본문과 어떤 관계가 있는지 1줄의 맥락적 설명**을 동반하여 작성합니다.
  - ✅ 예: `- [[content/concept-mcp]] — Raven과 에이전트 간의 통신 프로토콜 표준`
  - ❌ 예: `- [[content/concept-mcp]]`

### 2.3 본문 내 출처 표기 (Citation)

- 에이전트가 합성한 정보의 사실 여부 검증을 위해, 핵심 주장이나 세부 사실 옆에 `raw/` 1차 출처 각주 마커를 표시합니다.
  - ✅ 예: `Raven은 v0.7.3에서 Lite bootstrap 5종을 표준 규격으로 확립했습니다^[raw/articles/release-v0.7.3.md].`

### 2.4 본문에 과하게 노출하지 말 것

- ❌ `actor`, `run_id`, `tool`, `idempotency_key` 같은 운영 메타를 본문에 쓰기
- ❌ JSON, 체크리스트, 내부 추론 흔적을 본문 상단에 노출
- ❌ "에이전트가 판단했다" 같은 기계 중심 문장 반복
- ✅ 한 줄 요약 → 설명 → 관련 링크 순서 유지

### 2.5 최소 공통 뼈대

모든 타입에 완전 고정 템플릿을 강제하지 말고, 아래 3개 정도를 기본으로 삼습니다:

```
# {제목}

> {BLUF: 이 문서가 말하는 핵심 1문장}

## 내용
{사람이 읽기 쉬운 설명}

## 관련
- [[related-page]] — 이 페이지가 참조하는 관련 리소스
```

---

## 📝 3. 페이지 작성 템플릿 (Type 8종)

> 📝 **사람**: vault 자유지만 권장 구조.
> 🤖 **Agent**: 섹션 자동 생성 시 이 템플릿을 따르되, **적을 내용이 없는 상세 섹션은 생성하지 말고 삭제**하십시오.

### 📝 3.1 `concept` (Concept)

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

### 📝 3.2 `decision` (Decision)

```
# {Title}

> {BLUF: 1-line decision}

> [!NOTE] (선택 - 이 결정이 폐기/대체된 경우에만 작성)
> ⚠️ **대체됨**: 이 결정은 [[decision-new-slug]]에 의해 대체되었습니다.

## 맥락
{결정이 필요하게 된 배경과 문제 상황.}

## 결정
{최종 선택과 핵심 논거. 결론을 먼저 제시하고 근거를 붙입니다.}

## 영향 (Optional)
{이 결정으로 인해 시스템이나 프로젝트에 미치는 영향.}

## 관련
- [[related-page]] — 관련 설계 문서 또는 후속 작업 페이지
```

### 📝 3.3 `journal` (Journal / Daily Note)

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
> 🤖 **Agent Note**: 저널에 작성된 내용 중 영구적으로 보존 및 누적될 가치가 있는 핵심 지식(새 개념, 결정, 규칙 등)은 별도의 `concept`, `decision` 페이지로 컴파일하여 추출하고, 저널에는 링크만 남겨 지식을 정제하십시오.

### 📝 3.5 `person` (Person)

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

### 📝 3.6 `tool` (Tool)

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

### 📝 3.7 `comparison` (Comparison)

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

### 📝 3.8 `query` (Question)

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
> 🤖 **Agent Note**: 질문이 명확히 해결되는 경우, 해당 내용을 바탕으로 `concept` 또는 `rule` 문서로 리팩토링하거나 최종 지식 문서를 생성하고, 이 query 문서는 아카이브(혹은 해결 완료 링크를 남김) 처리하여 위키의 정합성을 유지하십시오.

### 📝 3.9 `project` (Project)

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

---

## ✅ 4. 일관성 체크리스트 (Consistency Checklist)

페이지 작성 후 다음 6개 확인:

- [ ] **첫 줄이 결론/결정 1문장** (BLUF)
- [ ] **frontmatter**: `title`, `type`, `created`, `updated` 채워짐
- [ ] **type이 8종 중 하나** (`concept`, `person`, `comparison`, `project`, `tool`, `rule`, `query`, `journal`)
- [ ] **wikilink ≥ 1** (관련 페이지 연결) 및 링크 옆 **맥락적 설명** 추가됨
- [ ] **본문이 사람 문장으로 읽힘** (운영 메타 / JSON / 내부 추론 흔적 / 빈 TBD 플레이스홀더 ❌)
- [ ] **저장 신호 4가지 통과** (재사용 가능성, 인수인계 필요성, 결정 근거, 실패/리스크)

---

## 🔗 5. 참고 (References)

- 📝 vault 운영 일반 규칙: `_meta/system/README.md` ("Vault User Guide")
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
