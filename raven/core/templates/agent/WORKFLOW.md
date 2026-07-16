---
title: Raven Agent Workflow — 트리거, Phase 게이트, 시나리오
created: 2026-06-25
updated: 2026-07-16
type: rule
tags: [system, meta, raven, agent, workflow, phase-gate]
audience: agent
confidence: high
---

# Raven Agent Workflow — 트리거 / Phase 게이트 / 시나리오

> **vault write는 "자발"이 아니라 "워크플로 트리거 시점에만" 합니다.**
> 이 문서는 **언제, 어디, 무엇을 write**할지 정의합니다.

---

## 1. 5가지 트리거 → write 시점

| 트리거 | type | 위치 | 자동/수동 | 빈도 |
|---|---|---|---|---|
| **결정** (사용자 컨펌) | `rule` | `content/<team>/decisions/` | 수동 | 주 1-2회 |
| **개념** (막힘 풀림) | `concept` | `content/<team>/concepts/` | 수동 | 주 1-2회 |
| **lesson** (실수/함정) | `rule` + `contradictions` | `content/<team>/lessons/` | 수동 | 사용자 지적 시 |
| **journal** (handoff) | `journal` | `content/<team>/journal/<YYYY-MM-DD>-<phase>` | 수동 | 매일 1 |
| **build/lint 결과** | `log.md` 자동 | `_meta/log.md` | **자동** | 매 write |

**❌ 안 함**: raw 진행 메모 · brainstorm · 토큰 단위 사고. **확정된 것만**.

### 1.5 문서 발행 프로토콜

새 문서를 발행할 때 나는 다음 순서로 처리합니다.

1. **검색**: 주제·핵심 용어·관련 규칙으로 vault를 먼저 검색해 중복과 기존 결정을 확인합니다.
2. **판정**: 기존 문서의 보강이면 새 페이지를 만들지 않고, 독립적으로 재사용·인수인계·근거 추적 가치가 있을 때만 발행합니다.
3. **메타데이터**: `title`, `type`, title 기반 slug, 최소 `tags`, 날짜를 설정합니다. 실제 참고한 원문/문서는 `sources`, 검증 수준은 `confidence`에 반영합니다.
4. **연결**: 본문 맥락에서 실제로 참조되는 문서는 설명을 붙인 `[[wikilink]]`로 연결합니다. 의미 관계는 `evidence`와 `reason`을 쓸 수 있을 때만 `relations`에 기록합니다.
5. **검증**: broken link, 형식, 고립 여부를 확인하고 결과를 보고합니다. 자동 추천은 관계 후보이지 관계 확정이 아닙니다.

`aliases`, `contested`/`contradictions`, 상태 전이·archive는 각각 rename/병합, 조사된 충돌, 운영 근거·권한이 있을 때만 사용합니다. 세부 소스 판정과 관계 품질은 [CURATION.md](CURATION.md)를 따릅니다.

---

## 2. 3가지 자연스러운 write 시점

> "raven은 모든 걸 적는 곳이 아니라, **다시 찾고 싶을 것**만 적는 곳이다."

### 트리거 1: 결정할 때 (Decision Moment)
- **언제**: A vs B 선택지가 있고, 둘 다 합리적일 때
- **비용**: 10-15분
- **왜**: 결정을 안 적으면 다음 에이전트(또는 미래의 나)가 같은 고민 반복
- **5섹션 표준**: 컨텍스트(후보 비교 표) / 결정 / 이유 / 트레이드오프 / 대안 검토 시 다시 보기

### 트리거 2: 막혔던 게 풀렸을 때 (Stuck Moment)
- **언제**: 30분+ 고민해서 답을 찾았을 때
- **판단**: 다음에 또 같은 검색할 것 같으면 → concept. 실수/함정 → lesson
- **왜**: 막힌 지점이 가장 값진 학습

### 트리거 3: 하루 끝 (Daily Closure)
- **언제**: 작업 세션 종료 시 (하루 1번)
- **비용**: 5분
- **3개 포함**: 오늘 한 것 (1-3줄) / 배운 것 (있으면) / 내일 할 것 (1줄)
- **왜 매일**: 작업 자체는 자취 안 남지만 시간순 흐름은 자산

---

## 3. 스킵 규칙 (이럴 땐 안 적어도 됨)

| 상황 | 이유 |
|---|---|
| 단순 버그 수정 | git log + diff에 이미 남음 |
| 1회성 작업 (다시 안 함) | 미래 참조 가치 0 |
| 자명한 사실 (코드 보면 알 수 있음) | 중복 = 부담만 추가 |
| 외부 자료 복붙 | 출처 + 1줄 평이면 OK, 본문 복사 ❌ |

---

## 4. 일일 cap (15분) — 강제 라인

| 트리거 | 빈도 | 시간 | 일일 환산 |
|---|---|---|---|
| 결정 | 주 1-2회 | 15분 × 2 = 30분 | ~4분/일 |
| 막힘 → 풀림 | 주 1-2회 | 15분 × 2 = 30분 | ~4분/일 |
| 일일 journal | 매일 | 5분 | 5분/일 |
| **합계** | | | **~13분/일** |

→ **하루 15분 cap**. 이 넘으면 분리/축소. "많이 쓴다 = 잘 쓴다" ❌.

**작성 직전 1초 자기 질문**:
> **"6개월 후의 내가 이걸 검색해서 찾겠는가?"**
> - ✅ Yes → 적는다
> - ❌ No → 스킵

---

## 5. Phase 게이트 — 회사 두뇌화 강제 룰

**원칙**: 모든 Phase 종료 시 vault write 없으면 다음 Phase 진행 불가. 강제지만 자연스러운 형태.

### 5.1 게이트 룰 (5개 팀 SOUL.md 인라인)

| 팀 | write 위치 | Phase 종료 시 1건 이상 필수 |
|---|---|---|
| harumoa | `~/vaults/wiki/content/harumoa/{journal,decisions,concepts,lessons}/` | 결정/lesson/journal 중 1 |
| homeauto | `~/vaults/wiki/content/homeauto/{...}/` | 동일 |
| resume | `~/vaults/wiki/content/resume/{...}/` | 동일 |
| design-spec | `~/vaults/wiki/content/design-spec/{...}/` | 동일 |
| wiki-orchestrator | `_meta/` (시스템 문서) 또는 위임 결과 검증 | 시스템 문서 갱신 OR 위임자가 위 4팀 중 1팀에 write 확인 |

### 5.2 메커니즘

1. 위임 Phase 종료 보고 수신
2. orchestrator가 `raven page ls --vault <active-vault> --tag <project>` 로 write 확인
3. 1건 이상 ✅ → 다음 Phase 진행
4. 0건 ❌ → fix 위임 또는 반려 (사용자에게 알림)

---

## 6. 누가 쓰나 (책임 경계)

| 역할 | write 권한 |
|---|---|
| **오케 (당신)** | 자기 팀 도메인 결정 · handoff 일지 · 사용자-facing summary |
| **위임 (worker)** | 콘텐츠 작성·링크 정리 OK. **결정 / lesson은 오케 자신이** (사용자 컨펌 책임) |
| **wiki-orchestrator** | 다른 팀 결정 ❌. 자기 팀 (wiki 시스템 문서)만 |
| **lessons 자동 생성** | ❌. 사용자가 반복 실수 / 강한 지적 시 오케가 후보 만들고 **사용자 컨펌 후** write |

---

## 6.5 주기적 큐레이팅 (Curation 루프) 및 역할 경계

> **[핵심 철학: 정적/동적 역할 분담]**
> * **도구 (Raven)**: 단순하고 객관적인 사실 확인인 **"정적 린트(Static Lint)"**만 수행합니다. (예: `wiki_lint()` 툴을 통한 데드링크 검출, 포맷 미준수 확인 등)
> * **지능 (에이전트 - 당신)**: 도구의 린터 진단 결과를 입력으로 받아 병합(Consolidation), 아카이브(Pruning), 모순 해결안 제시 등 **"동적인 의미론적 판단"**을 직접 내립니다. 도구가 직접 동적으로 판단하고 자동 수정하는 것은 허용되지 않습니다.

에이전트는 사용자가 "볼트 청소해줘", "정리해줘"라고 요청할 때나 주기적인 크론/세션 종료 단계에서 아래 **Curation 루프**를 자율 수행합니다.

### ① 1단계: 정적 진단 (Lint & Flag)
* `wiki_lint()` 툴을 활용하여 기계적인 오류들을 수집합니다. (예: broken links, orphans, contradictions 등)
* `confidence: low` 상태로 오랫동안 방치된 문서를 찾습니다.

### ② 2단계: 동적 판단 (Consolidate & Prune)
* **병합 (Consolidation)**: 파편화되거나 중복되는 개념들을 찾아 하나의 대표 문서로 병합하는 결정을 내립니다.
* **가지치기 (Pruning)**: 불필요해진 임시 문서를 아카이브(`_archive/` 이동)하기로 결정합니다.
* **모순 정리**: 모순된 두 문서의 텍스트 맥락을 비교 분석하여 최선의 해결방안을 마련합니다.

### ③ 3단계: 큐레이션 제안서 작성
* 에이전트가 내린 동적 판단을 **[Curation Proposal]** 형식으로 작성하여 사용자(사람)에게 컨펌을 요청합니다. 에이전트 임의로 문서를 대량 삭제하거나 합치는 파괴적인 행위는 금지합니다.
  ```markdown
  ### [Curation Proposal]
  - **병합 대상**: [[concept-A]] + [[concept-B]] -> [[concept-new]]
  - **아카이브 대상**: [[old-idea]] (이유: 설계 변경으로 미사용)
  - **모순 해결**: [[decision-A]]의 충돌 섹션을 최신 내용으로 부분 수정 제안
  
  이 정리 제안을 실행할까요?
  ```

### ④ 4단계: 승인 후 실행
* 사용자의 승인(Confirm)을 얻은 후에만 `wiki_update()`, `wiki_delete()`, `wiki_rename()` 등의 쓰기/관리 툴을 순차 실행하여 볼트를 청소합니다.

---

## 7. 부트스트랩 — 새 작업 시작 시 자동 read

에이전트는 새로운 작업 사이클을 시작할 때 반드시 아래 **MCP 툴**들을 호출하여 맥락을 동기화(부트스트랩)해야 합니다.

1. **최근 로그 조회**: `wiki_log(tail_n=3)` 툴 호출
2. **이전 결정 및 규칙 파악**: `wiki_search` 또는 `wiki_get_page`를 통한 최신 `rule` 수집
3. **인수인계 확인**: `wiki_get_page`로 최근 작성된 `journal` 조회
4. **품질/모순 검사**: `wiki_lint` 실행

→ 동기화된 지식 맥락을 컨텍스트에 주입한 뒤 태스크를 시작합니다. **Vault는 에이전트의 외부 메모리**입니다.

**당신의 SOUL.md §0에 권장 한 줄**:
> 새 작업 시작 시 `wiki_log(tail_n=3)` 및 `wiki_search`/`wiki_get_page`를 통한 지식 맥락 수집을 반드시 수행합니다.

---

## 8. 시나리오 — harumoa 연속 작업 (학습 사이클)

**1라운드**: 사용자 "harumoa 백엔드 스택 정해줘"
→ harumoa-orchestrator 결정 → `content/harumoa/decisions/backend-stack` 생성
→ 사용자에게 Telegram 보고: "저장됨: [[.../backend-stack]]"

**2라운드** (다음 날): 사용자 "harumoa 백엔드 작업 시작"
→ 부트스트랩 §7 자동 read → 어제 결정 발견 → 컨텍스트 주입
→ "어제 결정대로 Spring Boot + JPA로 진행합니다"

**3라운드** (작업 중): "JPA vs JOOQ 결정 필요"
→ 위임 → 결정 → `content/harumoa/decisions/orm-choice` (rule, `contradictions: [backend-stack]`)
→ 사용자 read → 모순 발견 시 "이거랑 모순 아닌가?" 피드백

**4라운드**: lessons 후보 자동 생성 (사용자 강한 지적 시)
→ "사용자가 'orm 모순' 지적 → lessons 후보 작성 → 사용자 컨펌"

**학습 사이클 완성**:
> vault = 사용자도 오케도 같이 보는 **외부 메모리**. 메모리만 의존하면 사라지지만, vault에 있으면 git 추적 + 검색 + 다음 세션 자동 read.

---

## 9. cross-link 패턴 (팀 간 연결)

```
content/harumoa/decisions/why-jpa-over-jdbc.md
  → [[content/_system/llm-wiki]] (도구 자체)
  → [[content/homeauto/decisions/db-choice]] (다른 팀 결정 참조)
  → [[content/design-spec/concepts/api-design]] (설계 영향)
```

- 같은 vault 안이므로 `[[content/...]]` 자유롭게 가능
- wikilink가 곧 cross-team trace — 다음 에이전트가 영향 받는 결정 검색 가능
- lint가 자동으로 broken/orphan 검증

---

## 10. 절대 안 되는 패턴 (워크플로)

| ❌ 안됨 | ✅ 대안 |
|---|---|
| "일단 적자" — 강제로 채우기 | 트리거 시점에만 (§2) |
| 트리거 아닌데 적기 (회피용) | 스킵 규칙 (§3) |
| 한 페이지 200줄+ (장황함) | 분리 — 15분 cap (§4) |
| 본문 복붙 (외부 자료) | 출처 + 1줄 평 |
| 빈 frontmatter로 commit | frontmatter 5필드 필수 (SCHEMA 참조) |
| Phase 끝났는데 vault write 0건으로 보고 | 결정 1건 + lesson 1건이라도 write 후 보고 |
| 메모리에만 결과 보관 (휘발) | vault에 결정/lesson write (영구) |
| 같은 vault가 아니라 매번 새 vault 만들기 | 단일 vault + 프로젝트별 하위폴더 |

---

## 관련

- [README.md](README.md) — 진입점
- [TOOLS.md](TOOLS.md) — 인터페이스 + scope 규칙
- [SAFETY.md](SAFETY.md) — 금지 행동
- `_meta/system/SCHEMA.md` — frontmatter 규약
