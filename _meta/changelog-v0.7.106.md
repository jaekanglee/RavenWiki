# Changelog v0.7.106 — PWW §0.5 [N6] Layer 2 + §3 lint 면제 + §6.5 archive + §7.1 type 권한

> **BLUF**: 2-party 합의 (Codex + Antigravity) + 사용자 명시 (journal/issue/decision write 권한). PWW §0.5 [N6] Layer 2 정체성 + §3 4신호 lint 면제 + §6.5 archive 권한 + §7.1 type별 write 권한. SCHEMA.md 9종 type 표에 "에이전트 write" 컬럼 추가. SCHEMA L81 aliases 보존 north star 명시. 5 file patch.

이전 changelog: `_meta/changelog-v0.7.105.md`

---

## §0 — 묶음 메타

| 항목 | 값 |
|---|---|
| 묶음 | PWW §0.5/§3/§6.5/§7 + SCHEMA 9종 type 권한 보강 |
| 범위 | v0.7.106 (단일 사이클) |
| 기간 | 2026-07-08 |
| 시작 트리거 | 2-party (Codex + Antigravity) write/read 신호 평가 + 사용자 journal/issue/decision write 권한 질문 |
| 종료 트리거 | patch 5 file + pytest Lite bootstrap surface/Tier boundary pass |
| 정책 변경 | 0 (모두 기존 SOT 정합 보강) |
| ADR 동반 | 0 (ADR-2026-07-06/08 인용만) |

## §1 — 무엇을 했나 (what)

### 1.1 PWW §0.5 [N6] Layer 2 정체성 (normative 부속)

`raven/core/templates/agent/PROJECT-WORKFLOW.md` L42-67 normative 5건에 6번째 추가:

> vault는 Layer 1 (Raven 제품) 위에 사람이 1차로 curate하는 운영 영역. **north star "원문 보존 + 증분 누적"의 실행 주체 = 사람**, 에이전트는 그 영역에서 "증분"을 보조하는 자율 역할.
> - 사람 1차 영역: `raw/` (full CRUD), `_meta/` 직접 수정, vault 운영 결정 (issue, decision, rule)
> - 에이전트 영역: `content/` 자유 write (§3 4신호 또는 lint 자동 수리), 다른 영역 read-only
> - 모든 write는 §3 4신호 또는 lint 수리 동기 필요 — **무신호 저장 ❌**

### 1.2 PWW §3 4신호 — lint 자동 수리 면제

L249 다음에 면제 명시:

> **면제**: lint (#1, #2, #5, #7, #10, #15) 자동 수리를 위한 `wiki_update` / `wiki_rename`은 §3 4신호 판단 **면제**. "기존 문서 무결성 수정"은 north star "원문 보존"에 부합 (§6.5 큐레이션 절차). **단, lint #15 일괄 rename은 vault 운영자 명시 결정 필수 (ADR-2026-07-08 §2.1).**

**Conflict C1 해소** (2-party 합의): §3 4신호 vs lint 자동 수리 write 경계.

### 1.3 PWW §6.5 archive 권한 (ADR-2026-07-06 §1.2 반영)

L309 다음에 1줄 추가:

> **#7 stale → `wiki_archive` (ADR-2026-07-06 §1.2)** — 에이전트도 가능 (lint 결과 기반). 단 `archived → current` 복귀는 **사람 승인 필수** (status 머신 4종 §1.1).

**Conflict C3 해소** (2-party 합의): PWW §6.5 "archive = 사람 전용" vs ADR-2026-07-06 "에이전트 ✅" — ADR이 더 최근, PWW 갱신.

### 1.4 PWW §7.1 type별 에이전트 write 권한 (사용자 명시)

L325 다음에 1줄 추가:

| type | 자율 write | 명시 | 비고 |
|---|---|---|---|
| `concept` / `rule` / `person` | ⚠️ draft → 사람 review → final | ✅ | PWW §7 L312 |
| `comparison` / `project` / `tool` / `query` | ✅ 자유 | ✅ | §3 4신호 |
| **`journal`** | ✅ **자율 가능** | ✅ | PWW §7 L316 + event_date |
| **`issue`** | ❌ **발의만** (직접 write ❌) | ✅ | PWW §6.5 #4/#7/#8 |
| **`decision`** (ADR) | ❌ (사람 1차) | ✅ (에이전트 보조) | SCHEMA L99 |

**사용자 질문 정합**:
- "**journal**" = ✅ 자율 (harumoa 28건 journal patch 사례)
- "**issue**" = ❌ 발의만 (PWW §6.5 명시)
- "**decision**" = ❌ 사람 1차 (PWW §7 L312, SCHEMA L99 컨벤션)

### 1.5 SCHEMA.md 9종 type 표 + aliases 보존 (vault + codebase 양쪽)

**vault SCHEMA.md L99 부근**:
- 9종 type 표에 "에이전트 write" 컬럼 추가 (PWW §7.1 cross-ref)
- L93 (journal/ADR 컨벤션) 다음에 aliases 보존 north star 명시 (ADR-2026-07-08 §2)

**codebase `_meta/SCHEMA.md` L87-97**:
- 9종 type 표에 "에이전트 write" 컬럼 추가
- L162 다음에 aliases 보존 north star 명시

## §2 — 무엇을 하지 않았나 (의도적 scope-out)

- ❌ **lint #16 (vault 성장률) / #17 (중복 페이지) 코드 구현** — 2-party 권고이나 사용자 명시 없음. SOT 정의만 (별도 사이클)
- ❌ **1.5배 soft limit override** — 1-party 권고, 2-party 미합의. 미적용
- ❌ **다른 vault audit** (babymoa, hermes-infra, homelab) — 다음 사이클
- ❌ **vault 데이터 write** (filesystem 작업) — 이번 사이클은 SOT 보강만
- ❌ **3-party 평가 결과 본 합의 적용** — 사용자가 명시한 Codex + Antigravity 2-party만. Claude 결과 (`docs/evaluations/2026-07-08-agent-signal-evaluation.md`)는 **별도 평가로 분리 보존** (본 합의 미포함)

## §3 — 검증

| 항목 | 결과 |
|---|---|
| PWW §0.5 [N6] 추가 | ✅ (L68-74) |
| PWW §3 lint 면제 명시 | ✅ (L251-253) |
| PWW §6.5 archive 권한 추가 | ✅ (L313) |
| PWW §7.1 type별 write 권한 | ✅ (L327-344) |
| SCHEMA.md type 표 5컬럼 (vault) | ✅ (L99-110) |
| SCHEMA.md type 표 5컬럼 (codebase) | ✅ (L87-97) |
| SCHEMA.md aliases 보존 (vault + codebase) | ✅ (L94 / L163) |
| pytest Lite bootstrap surface + Tier boundary | (아래 검증) |

## §4 — 회고 (lessons)

1. **2-party vs 3-party 정직** — 사용자가 명시한 party count 정확히 따름. Claude 결과는 별도 평가로 분리 보존. 정직 보고
2. **사용자 질문이 SOT gap** — "journal/issue/decision 에이전트 쓰나?" → SOT에 type별 write 권한 명시 없음 (§7 L312-316 모호). **사용자 질문 자체가 SOT 보강 트리거**
3. **conflict C1 (4신호 vs lint 수리) 해결** — 2-party 모두 "lint 수리는 4신호 면제" 합의. SCHEMA/PRW §3에 명시
4. **conflict C3 (archive 권한) 해결** — ADR-2026-07-06이 더 recent. PWW §6.5 갱신
5. **SCHEMA type 표 = vault 운영의 1차 entry** — 에이전트가 vault 진입 시 가장 먼저 보는 표. 컬럼 1개 추가 = 운영자/에이전트 권한 명확화

## §5 — 알려진 회귀 / 후속 작업

| 항목 | 우선순위 | 비고 |
|---|---|---|
| lint #16 (vault 성장률) / #17 (중복 페이지) 코드 구현 | 다음 사이클 (사용자 명시 시) | 2-party 권고 |
| 다른 vault audit (babymoa, hermes-infra, homelab) | 다음 사이클 | harumoa 다음 |
| 1.5배 soft limit override (Conflict C5) | 별도 사이클 | 1-party 권고, 2-party 미합의 |
| 3-party 평가 결과 (Claude) 통합 | 별도 (사용자 명시 시) | 현재 별도 보존 |
| raven wikilink resolver 한글 slug 한계 | 별도 사이클 | raven core |

## §6 — 다음 사이클

본 사이클 = SOT 보강 종착 (PWW 4 patch + SCHEMA 4 patch + changelog 1). 다음 사이클은 사용자 명시 요청 시 (P55-6).

가능한 후보:
- 다음 사이클: lint #16/#17 코드 구현
- 다음 사이클: 다른 vault audit
- 다음 사이클: 1.5배 soft limit override (Conflict C5)

---

🤖 Generated with [Claude Code](https://claude.com/claude-code)
