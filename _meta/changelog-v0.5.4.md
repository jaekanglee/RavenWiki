# wikisys v0.5.4 — 카파시 스킬 사용 메커니즘 차용 (B + D)

> **핵심**: 카파시 LLM Wiki gist의 5가지 "스킬 사용 메커니즘" 중 **B (Session Start Orientation)** + **D (액션별 check/avoid)** 차용. 위키 작업의 "기본 안전망" 완성.

릴리스 일자: 2026-06-26
이전: v0.5.3 (Q3 tag 승격 + lint 파싱)

---

## 한 줄 요약

**orchestrator에 Session Start Orientation 3-step** (카파시 SCHEMA+index+log 차용) + **wikisys/SKILL.md에 §"Common Mistakes by Action"** (8개 액션 × 4-8개 mistake). **코드 변경 0, 문서 2개 +1**.

---

## 1. 카파시 5-메커니즘 매트릭스

| # | 메커니즘 | 카파시 | 우리 v0.5.3 | v0.5.4 |
|---|---|---|---|---|
| A | 발화 트리거 ("When the user...") | ✅ | ✅ | ✅ |
| **B** | **Session Start Orientation** | ✅ | ❌ | **✅ (이번)** |
| C | 단계별 프로토콜 (Phase별) | 부분 | 부분 | 부분 (보류) |
| **D** | **액션별 check/avoid** | ✅ | ❌ (P1-P8 일반) | **✅ (이번)** |
| E | 시나리오별 pitfall (vault 크기) | ✅ | ❌ | ❌ (다음 사이클) |

---

## 2. B. Session Start Orientation

### 추가 위치
`~/.hermes/profiles/wiki-orchestrator/SOUL.md` §3.5 (Off-limits와 Handoff 사이).

### 동작
- Telegram DM 수신 + vault 키워드 감지 시
- 3-step read 자동:
  1. `~/vaults/<active>/_meta/SCHEMA.md`
  2. `~/vaults/<active>/_meta/RULES.md`
  3. `wikisys log list --tail 30`
- 단순 명령 (예: "log status")은 skip
- vault 식별 불가 시 사용자에게 질문

### 효과
- 중복 페이지 생성 방지
- cross-reference 누락 방지
- 사용자 모순 발언 방지
- 반복 작업 방지
- Phase 프로필 일관성 (architect vs writer vs curator)

### 차용 원본 (카파시)
> "When the user has an existing wiki, **always orient yourself before doing anything**"
> ① Read SCHEMA.md → ② Read index.md → ③ Scan recent log.md
>
> 우리: `index.md` 없음 → `wiki.db`로 대체 (v0.2 결정)

### 예외
- "그냥 [명령]" → orient 후 writer 위임
- "급해" / "빨리" → orient 생략

---

## 3. D. Common Mistakes by Action

### 추가 위치
`~/.hermes/profiles/wiki-orchestrator/skills/wikisys/SKILL.md` §"Common Mistakes by Action" (P1-P8 다음, "다음 단계 후보" 직전).

### 8개 액션 × 4-8개 mistake

| 액션 | mistake 수 | 핵심 |
|---|---|---|
| 페이지 생성 (`wikisys page new`) | 7 | FM 누락, intent 미사용, slug 안전 |
| wikilink 검사 | 5 | broken 누락, false positive |
| `wikisys build` | 5 | `--no-lint` 오용, wiki.db commit |
| `wikisys lint` | 6 | grace 만료, 면제 규칙 무시 |
| `wikisys log` | 5 | 수동 편집, rotate 누락 |
| `wikisys migrate` | 5 | **dry-run 없이 apply** (가장 위험) |
| vault create / multi-vault | 5 | name 충돌, mode 혼동 |
| Dashboard | 4 | PWA 캐시, API down |
| 운영 일반 | 5 | raw 손, 외부 수정, git 누락 |

**총 47개 mistake** (P1-P8과 별개, 액션별).

### 차용 원본 (카파시)
> "This prevents:
> - Creating duplicate pages for entities that already exist
> - Missing cross-references to existing content
> - Contradicting the schema's conventions
> - Repeating work already logged"

→ **카파시는 4가지, 우리는 47가지로 확장** (액션별 분해).

---

## 4. 변경 파일 (3개)

| 파일 | 변경 | +LOC |
|---|---|---|
| `~/.hermes/profiles/wiki-orchestrator/SOUL.md` | §3.5 Session Start Orientation | +40 |
| `~/.hermes/profiles/wiki-orchestrator/skills/wikisys/SKILL.md` | §"Common Mistakes by Action" | +90 |
| `_meta/changelog-v0.5.4.md` | (이 문서) | 신규 |

**총 +200 LOC** (코드 0, 문서 200)

---

## 5. C. 단계별 프로토콜 (보류 이유)

**위 4개 프로필에 "Operating Protocol" 추가하는 것**은 v0.5.4 후보였으나 보류:

- **memory 안전 문제**: "사용자가 직접 config 설정 함 — 내가 덮어쓰면 노여움 (2026-06-24 사건)"
- 프로필 SOUL.md는 **사용자 영역** — 내가 임의로 패치하면 사용자 config 변경
- v0.5.4+ 에서 사용자가 명시적으로 "프로필에 추가해줘" 요청 시 진행

**대안**: RULES.md 또는 wikisys/SKILL.md에 **프로토콜 요약** (architect=6단계 / curator=6단계 / writer=10단계) — 이미 RULES.md §2-§7에 부분 있음.

---

## 6. E. 시나리오별 pitfall (다음 사이클)

- vault 10-30 / 30-100 / 100+ pages별 운영 가이드
- size별 orient depth, lint cadence, search 도구
- v0.5.4+ 후보였지만 B+D가 우선 → 보류

---

## 7. 효과 (예상)

| 메트릭 | v0.5.3 | v0.5.4 (예상) |
|---|---|---|
| 세션 시작 시 일관성 | ❌ (각자) | ✅ (3-step orient) |
| 사용자 실수 방지 | 부분 (P1-P8) | ✅ (47 액션별) |
| 에이전트 handover 품질 | ⚠️ | ✅ (SCHEMA/RULES 일관) |
| 위키 작업 시간 | 기준 | -10% (중복/반복 제거) |

---

## 8. 누적 v0.5.x (7 커밋)

| 버전 | 핵심 | 커밋 | +LOC |
|---|---|---|---|
| v0.5.0 | log.md 인프라 | `bb0be3b` | +1,425 |
| v0.5.1 | lint 12개 | `f1d010c` | +1,288 |
| v0.5.2 | Dashboard + migrate | `71277f6` | +1,592 |
| v0.5.2.1 | 면제 + 마이그레이션 | `c33e68b` | +176 |
| v0.5.3 | Q3 + 파싱 | `9bd7113` | +186 |
| **v0.5.4** | **B + D (스킬 메커니즘)** | **(이번)** | **+200** |
| **합계** | | **6 커밋** | **+4,867** |

→ **카파시 12/12 lint + UI + 도구 + 실행 + 마무리 + 안전망 = 위키 시스템 운영정책 완전 통합**

---

## 9. 다음 단계

| 후보 | 시점 |
|---|---|
| **C**: 프로필별 Operating Protocol | 사용자 명시 시 (memory 안전) |
| **E**: vault 크기별 시나리오 pitfall | 다음 사이클 |
| v0.6: MCP tool 4개 추가 (search/ingest/lint/log) | M3 vector search 결정 시 |
| v0.6: Dataview 대용 (wikisys query CLI) | 50+ 페이지 시 |

→ **v0.5.x 시리즈 마무리**. 다음 사이클 = vault 사용 + 자연스러운 gap 발견.

---

## 관련

- [[_meta/changelog-v0.5.3]] (이전)
- [[_meta/ai-roadmap]] (M3 보류 노트)
- 카파시: https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f
- hermes skill: `research/llm-wiki` (B + D 원본 차용)
