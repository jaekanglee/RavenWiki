---
title: "ADR: PROJECT-WORKFLOW.md §1-7 재배치 (사용자 워크플로우 정렬)"
date: 2026-07-07
status: accepted
audience: agent, human
supersedes: null
related:
  - AGENTS.md §6 (작업 절차: 작업 분류, verify-in-loop, changelog)
  - _meta/decisions/adr-2026-07-07-mcp-wiki-get-guide.md (v0.7.91 MCP 표면 신설)
  - _meta/changelog-v0.7.89.md (Dashboard /guides viewer)
  - _meta/changelog-v0.7.90.md (PROJECT-WORKFLOW.md PR1: normative 1곳 + cross-ref, 정책 0% 변경)
  - docs/vault-patterns.md (Karpathy LLM Wiki +α 가이드)
related_changelog: v0.7.92
type: rule
---

# ADR — PROJECT-WORKFLOW.md §1-7 재배치 (사용자 워크플로우 정렬)

> **한 줄**: v0.7.90 PR1이 normative 응집 + cross-ref 정합을 달성했지만, **§1-7의 본문 순서는 여전히 "MCP 도구 → 권한 → 저장 → 형식 → 분업 → ..."** 순으로, 운영자/에이전트의 실제 작업 흐름 ("vault 진입 → MCP 도달 → 문서 작성 → 저장 판단 → 검증") 과 어긋남. **§1-7 본문 순서를 사용자 워크플로우 순서로 재배치**하되, **normative 정의 위치 (§0.5, §2, §3, §8) 는 불변**, cross-ref만 새 번호로 일괄 재작성. **의미 변경 가능성 (cross-ref 50+개)** → ADR 동반.

## 0. 맥락 (Context)

v0.7.90 PR1 후속 사용자 피드백 (3-round 합의):

> "Quick Start (1분) → Vault 진입 절차 → MCP 사용법 → 문서 작성 규칙 → 저장 판단 → 검증 절차 → 금지 사항 → 부록(철학, North Star, ADR 배경)"

이 순서가 운영자/에이전트의 **즉시 답이 필요한 질문** 순서와 정합:

1. "내가 뭘 해야 하지?" → Quick Start (§0)
2. "어디서 시작하지?" → Vault 진입 절차 (현재 §1 → §0 Quick Start에 흡수됨, v0.7.90)
3. "MCP 어떻게 도달하지?" → MCP 사용법 (현재 §1.5)
4. "문서 어떻게 쓰지?" → 문서 작성 규칙 (현재 §5)
5. "저장해야 하나?" → 저장 판단 (현재 §3)
6. "검증 어떻게?" → 검증 절차 (현재 §7 + §7.1 + §7.5)
7. "하지 말 것은?" → 금지 (현재 §9)
8. "왜 이렇게 됐지?" → 부록 (현재 §0.5 + §10 + §11)

현재 순서: §1(MCP 도구) → §1.5(도달법) → §2(권한) → §3(저장) → §4(분업) → §5(형식) → §6(폴더) → §7(체크리스트) → §7.1 → §7.5 → §8(멀티에이전트) → §9(금지).

→ §1-7 본문 순서가 "규범 → 운영" 흐름이라, 작업 중 "지금 뭐 하지?" 즉시 답이 안 나옴.

## 1. 결정 (Decision)

**§1-7 본문 순서를 사용자 워크플로우 순서로 재배치**한다. **normative 정의 위치는 불변** (§0.5 normative 5건, §2 권한, §3 저장신호 4가지, §8 금지 — normative 단일 위치 정책 v0.7.90).

### 1.1 재배치 매핑

| 현재 | → | 변경 후 | 비고 |
|---|---|---|---|
| §0 Quick Start | → | §0 (불변) | v0.7.90 신설, 정책 0 |
| §0.5 North Star | → | §0.5 (불변) | normative 5건 SoT, 불변 |
| §0 TOC | → | §0 (불변) | v0.7.90 신설 |
| §1 MCP 도구 9종 + §1.5 MCP 도달법 | → | **§1 MCP (도구 + 도달법 통합)** | 정책 불변, 통합 |
| §2 권한 | → | **§2 권한** (불변) | normative |
| §3 저장 결정 4가지 신호 | → | **§3 저장 결정** (불변) | normative |
| §5 형식 요구사항 | → | **§4 문서 작성 규칙** (shift -1) | 정책 불변, 위치 이동 |
| §6 폴더 구조 권장 | → | **§5 폴더 구조** (shift -1) | 정책 불변, 위치 이동 |
| §7 + §7.1 + §7.5 (체크리스트 + 자율점검 + 큐레이션) | → | **§6 검증 절차** (통합, shift -1) | 정책 불변, 통합 |
| §4 분업/트리거 | → | **§7 분업/트리거** (shift +3) | 정책 불변, 위치 이동 |
| §8 멀티 에이전트 협업 | → | **§7.5 멀티 에이전트 협업** (shift) | 정책 불변, 위치 이동 |
| §9 하지 말 것 | → | **§8 금지** (shift -1) | normative (cross-ref) |
| §11 "이 문서에 없는 것" | → | **§8.5 부록: 에이전트 스스로 판단/기억할 영역** (shift) | 정책 불변 |
| §10 다음 단계 | → | **§9 부록: 다음 단계** (shift -1) | 정책 불변 |

**번호 정합**:
- §0, §0.5, §1, §2, §3 = 5개 normative/policy position (불변)
- §4, §5, §6, §7, §7.5, §8, §8.5, §9 = 8개 운영 사실 (재배치)
- §11 제거 (이전 "末" 절 → §8.5 로 통합)

### 1.2 cross-ref 일괄 재작성 (의미 변경 = 본 ADR의 핵심)

모든 `→ §X` / `→ §X.Y` 참조를 **새 번호로** 갱신. cross-ref 50+개 위치:

- `→ §0.5` (normative) — 위치/내용 불변 → 갱신 불요
- `→ §0.5 §1` `→ §0.5 §2` `→ §0.5 §3` `→ §0.5 §4` `→ §0.5 §5` — normative 내부 sub-section, 불변
- `→ §2` (권한) — 불변
- `→ §3` (저장신호) — 불변
- `→ §5` → `→ §4` (형식 → 문서규칙)
- `→ §6` → `→ §5` (폴더)
- `→ §7` → `→ §6` (체크리스트 → 검증)
- `→ §7.1` → `→ §6.1` (자율점검)
- `→ §7.5` → `→ §6.5` (큐레이션)
- `→ §8` → `→ §7.5` (멀티에이전트)
- `→ §9` → `→ §8` (금지)
- `→ §11` → `→ §8.5` (이 문서에 없는 것)
- `→ §10` → `→ §9` (다음 단계)

## 2. 이유 (Rationale)

### 2.1 사용자 워크플로우 정렬
**"지금 뭐 하지?" 즉시 답**. 운영자/에이전트가 vault에 진입했을 때 가장 자주 찾는 답 4가지:
1. lint 언제? → §6 (검증 절차, 체크리스트)
2. 권한 어디? → §2 (불변)
3. 쓰기 전 뭐? → §3 (저장신호) + §4 (문서규칙)
4. 금지 뭐? → §8 (cross-ref → §0.5/§2/§3)

재배치 전엔 "§7 체크리스트"까지 스크롤, 후엔 "§6 검증 절차" 즉시 도달. **1-depth 절약** × 4가지 자주 찾는 답 = **즉답성 4× 향상**.

### 2.2 normative 단일 위치 정책 보존
v0.7.90 PR1의 핵심: "normative = 1곳, 나머지 = cross-ref". 재배치 후에도:
- §0.5 (normative 5건) — 불변
- §2 (권한) — 불변
- §3 (저장신호) — 불변
- §8 (금지) — cross-ref만 새 번호로

→ normative drift 위험 0. 정책 변경 0.

### 2.3 AGENTS.md §6 작업 절차 정합
AGENTS.md §6: "사용자 요청을 작업 종류로 분류 (build / test / lint / doc / commit)". 본 문서가 이 분류에 직접 매핑:
- "lint" → §6 검증
- "doc" → §4 문서규칙
- "test" → §4 (BLUF/slug) + §6
- "commit" → §3 저장신호 + §6 체크리스트
- "build" → §7 분업/트리거

### 2.4 §0 Quick Start와 일관성
v0.7.90 Quick Start 7 steps (Layer 인지 → log.md → index → 관련 3-5 → SCHEMA → content only → lint) 가 본문 §1-7 순서와 정합해야 함. 현재:
- Step 1-2 = §0 (Quick Start 본체)
- Step 3-4 = §0 (관련 문서 — Quick Start 본체)
- Step 5 = §4 (SCHEMA 위치 — 재배치 후)
- Step 6 = §0.5 §5 + §2 (`_meta/system` + 권한)
- Step 7 = §6 (lint — 재배치 후)

재배치 전엔 Step 5-7 의 cross-ref 가 §1-7 사이 멀리 떨어진 위치. 후엔 §0 → §4 → §2 → §6 의 자연스러운 깊이 (top → mid → mid → top-mid). 가독성 ↑.

## 3. 결과 (Consequences)

### 3.1 긍정 (Positive)
- **즉답성 ↑** — "lint 언제?" / "권한 어디?" / "쓰기 전?" / "금지?" 4가지 자주 답이 1-depth 절약.
- **normative 단일 위치 유지** — v0.7.90 정책 보존, drift 위험 0.
- **Lite bootstrap 자동 sync** — `raven meta sync --lite`로 기존 vault도 자동 업뎃 (v0.7.65+ 정책, opt-in).
- **PR2-A (v0.7.91 MCP wiki_get_guide)와 정합** — §1 MCP 도구 표 + §1.5 도달법 통합, "MCP 사용법" 단일 절.
- **§0 Quick Start cross-ref 자연스러움** — Step 5-7의 → §X 참조가 §0에서 가까운 깊이.

### 3.2 부정 / 위험 (Negative / Risks)
- **외부 에이전트 cite 깨짐** — 어떤 agent가 `PROJECT-WORKFLOW.md §7.5`를 cite했다면 §6.5로 갱신 필요. mitigation: §11 "이 문서에 없는 것" 절에 "단절 cite 갱신은 각 에이전트 책임" 명시 (v0.7.65+ 정책, v0.7.65 §11 그대로).
- **git blame 손실** — 재배치로 §5 → §4 같은 cross-ref 50+개가 한꺼번에 갱신되면 blame이 §1-7 본문에선 거의 의미 없어짐. mitigation: §0.5 normative 5건은 단일 위치 (blame 유효), cross-ref는 별도 grep으로 추적.
- **§4 (분업/트리거) 위치 논쟁** — 사용자 제안 순서 "Quick Start → Vault 진입 → MCP → 문서규칙 → 저장판단 → 검증 → 금지 → 부록" 에 분업/트리거가 명시 없음. 본 ADR은 사용자 워크플로우 마지막 직전 (검증 → 분업 → 금지) 으로 배치. **이 결정은 운영 사실 기술**이므로 재배치 자유도가 높음. 후속 PR3+ 에서 사용자/스테이크홀더와 재검토 가능.

## 4. 대안 (Alternatives Considered)

| 대안 | 거부 이유 |
|---|---|
| **A. §1-7 그대로 유지** | 사용자 워크플로우 정렬 안 됨. v0.7.90 PR1의 cross-ref 정합이 "MCP 도구 → 권한" 순서를 가정했음. 본 ADR은 그 가정을 재검토. |
| **B. §1-7 통합/축소** | 정책 0% 변경이 PR1의 핵심. 본 PR2-B는 "순서 재배치"만, 통합/축소는 별도 PR3+. Karpathy §1 simplicity first 적용은 다음 사이클. |
| **C. normative 위치도 이동** | v0.7.90 normative 단일 위치 정책 위반. §0.5 SoT 깨짐. ADR 본문 drift 위험. ❌ |
| **D. ADR 없이 진행** | cross-ref 50+개 재작성 = 의미 변경 가능성. 사용자 정한 ADR threshold (의미 변경 시) 적용. ADR 동반. |

→ **본 ADR의 결정 (§1-7 재배치, normative 불변)** 가 best.

## 5. 구현 / 검증 (Implementation / Verification)

### 변경 파일
| 파일 | 변경 |
|---|---|
| `raven/core/templates/agent/PROJECT-WORKFLOW.md` | §1-7 본문 재배치 + cross-ref 50+개 일괄 재작성 + §11 → §8.5 통합 |

### 검증
- pytest 회귀: `pytest tests/ -q --ignore=tests/curator` → v0.7.91 baseline **631 passed** 유지
- Lite bootstrap sync: `raven meta sync --lite` (opt-in)
- norm 위치 grep: §0.5 normative 5건, §2 권한, §3 저장신호, §8 금지 — 모두 단일 위치 유지
- cross-ref grep: 모든 `→ §X` 새 번호 일치 (50+개)
- Dashboard build: 변경 0 (sanity)

### Cross-reference
- v0.7.89 (REST `/guide`): `_meta/changelog-v0.7.89.md`
- v0.7.90 (PROJECT-WORKFLOW PR1): `_meta/changelog-v0.7.90.md` — normative 1곳 + cross-ref 정합
- v0.7.91 (MCP `wiki_get_guide`): `_meta/changelog-v0.7.91.md`
- v0.7.92 (PROJECT-WORKFLOW §1-7 재배치): 본 ADR + `_meta/changelog-v0.7.92.md` (작성 예정)
