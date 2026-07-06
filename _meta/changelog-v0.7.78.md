# Changelog v0.7.78 — PROJECT-WORKFLOW §0 vault 경계 명시 (2026-07-06)

> **BLUF**: 사용자 정확한 진단 (2026-07-06) — "외부 에이전트에게 vault를 줬을 때 어디까지 읽으라고 안내해야 하는지". Lite bootstrap 정책(v0.7.65+)상 `_meta/system/` 등 Tier 1 경로는 물리적으로 전달되지 않지만, defense in depth 차원에서 §0에 명시적 안내 추가.
>
> 이전 changelog: `_meta/changelog-v0.7.77.md`

---

## §0 — commit 1개

| commit | 항목 | 파일 | 변경 |
|---|---|---|---|
| `e58df40` | A. PROJECT-WORKFLOW.md §0 vault 경계 명시 | `raven/core/templates/agent/PROJECT-WORKFLOW.md` | +6 |

---

## A. PROJECT-WORKFLOW.md §0 vault 경계 명시 (`e58df40`)

### 진단 배경

Lite bootstrap 정책(v0.7.65+)에 따라 외부 에이전트가 받는 vault는 `_meta/agents/` 2종 (SCHEMA.md, PROJECT-WORKFLOW.md) + `log.md` + `content/`만 포함. `_meta/system/` (Tier 1 운영 매뉴얼)은 *물리적으로 전달되지 않음*.

하지만:
- 정책 자체를 *에이전트가 알도록* 명시되어 있지 않음
- 만약 vault clone 과정에서 오염 발생 시 에이전트가 *오염 폴더를 보고 사용자에게 경고*할 근거가 약함
- §0가 "당신이 받은 vault"에 대한 자기-기술을 강화해야 함

### 추가된 단락 (§0)

> **당신이 받는 vault에 포함된 것**: `_meta/agents/` (SCHEMA.md + PROJECT-WORKFLOW.md), `log.md`, `content/`. 이 외 경로(예: `_meta/system/`, 운영자 README, raven 패키지 내부 CLI 매뉴얼)는 **Lite bootstrap 정책(v0.7.65+)에 의해 포함되지 않습니다**. vault 안에 보이지 않는 폴더가 있다고 가정하지 마세요 — 보인다면 오염 가능성이 있으므로 사용자에게 보고하세요.

### 효과

- 외부 에이전트가 *자기 vault 범위*를 명확히 인식
- Tier 1 leak 감지 능력 (오염 폴더 발견 시 즉시 보고)
- vendor-agnostic 정책 + Lite bootstrap 정책 일관성 강화

**검증**: 변경 라인 수만 (md 파일, TypeScript/Python 무관).

---

## §1 — 검증 종합

| 검증 | 결과 |
|---|---|
| `git push origin master` | 완료 |

---

## §2 — 사이클 연속성

| 사이클 | 항목 |
|---|---|
| v0.7.74 | PROJECT-WORKFLOW.md §1.5 신설 + Wizard MCP snippet |
| v0.7.77 | §1.5.1 표준 MCP 패턴 + Wizard 동기화 |
| v0.7.78 | **§0 vault 경계 명시 (Lite bootstrap 정책 안내)** |

→ 외부 에이전트 진입 가이드 강화 3 사이클 연속. v0.7.78은 *자기 인식 경계* — 에이전트가 자기가 받은 vault의 경계를 명확히 알도록.