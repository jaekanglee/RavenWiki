# Changelog v0.7.88 — PROJECT-WORKFLOW.md §0.5 NORTH STAR BOUNDARY 추가 (2026-07-07)

> **BLUF**: 외부 LLM 에이전트가 vault 진입 시 Layer 1 (Raven 제품, 사람 1차 PKM) vs Layer 2 (에이전트 활용 레이어) 의 경계를 즉시 인식하도록, `PROJECT-WORKFLOW.md` §0 끝에 `§0.5 North Star 경계` 섹션을 신설하고 도입 인용구의 톤을 사람 1차로 정정했습니다. Lite bootstrap = Layer 1 sub-feature (자동 주입은 Raven 제품 동작) 명시, Layer 2 north star = cwd 작업 산출물/인사이트를 사람 curation 옵션만 두고 vault 위키화.

이전 changelog: `_meta/changelog-v0.7.87.md`

---

## §0 — commit 1개

| commit | 항목 | 파일 | 변경 |
|---|---|---|---|
| `a0bc5ac` | A. PROJECT-WORKFLOW.md — §0.5 layer-separation (Layer 1 vs Layer 2) | `raven/core/templates/agent/PROJECT-WORKFLOW.md` | +43/−3 |

---

## A. PROJECT-WORKFLOW.md — §0.5 layer-separation

### 진단

외부 LLM 에이전트가 vault 진입 시 읽는 `PROJECT-WORKFLOW.md`에는 두 가지 모호함이 동시에 존재했습니다:

1. **North star 부재** — 본 문서가 어떤 north star에 종속되어 있는지 명시 없음.
   - 외부 에이전트가 "Agent-as-primary"로 오독하거나, 반대로 "사람이 1차 = 무관"으로 무시할 위험.
2. **톤 불일치** — L13-15 인용구가 `"Raven is the IDE; the LLM is the programmer; the wiki is the codebase."` 로 LLM-as-primary 톤.
   - Raven 제품 정체성(사람 1차, Obsidian 모티브 자체 구현체)과 충돌.

추가로 Lite bootstrap(2-file vault 자동 주입)에 대한 외부 에이전트의 오해 가능성:
- "이 문서가 어떻게 vault에 들어왔는지"가 §0에서 명시 안 됨
- 일부 에이전트는 "내가 vault에 진입했을 때 Raven 내부 도구/CLI를 직접 조회해야 하지 않나?"로 R9(Raven 소스 코드/외부 시스템 조회) 위반 시도 위험.

### 진짜 원인

§0 도입 인용구 + Lite bootstrap 자동 주입에 대한 메타 설명 부재. 두 레이어(Layer 1 제품 / Layer 2 활용)를 정의하는 단락이 어디에도 없음.

### 변경 사항

| 위치 | 변경 |
|---|---|
| L13-15 (도입 인용구) | `"Raven is the IDE; the LLM is the programmer; the wiki is the codebase."` 톤 제거 → `"사람이 원본을 공급하고, Raven이 그 원본을 정리·누적하는 공간입니다. 당신(에이전트)은 그 공간의 옵션 손님입니다."` |
| L17-18 (도입 직후) | 1줄 anchor 추가: `본 문서 §1+ 는 에이전트 활용을 위한 Layer 2 가이드입니다. Raven 제품 자체(사람 1차 PKM)의 정체성은 Layer 1 이며, 이를 바꾸지 마세요.` |
| §0 끝 + §1 직전 (§0.5) | 신규 37줄 — Layer 1/2 정의 + Layer 2 north star (cwd 산출물 위키화) + Layer 1 정체성 침범 경고 + actor provenance + Lite bootstrap = Layer 1 sub-feature |

§0.5 신규 본문 핵심 5블록:

1. **Layer 정의** — Layer 1 = Raven 제품 / Layer 2 = 에이전트 활용. 문서 self-contained.
2. **Layer 2 north star** — `당신 자신의 cwd 작업 과정·산출물·인사이트 — 사람 입력이 있을 때도 없을 때도 — 를 vault에 위키화`. 사람 curation은 옵션일 뿐 전제조건 아님.
3. **Layer 1 침범 경고** — vault 구조·데이터 규격·운영 패턴을 "더 나은 방식"으로 교체 ❌.
4. **산출물 출처** — 사람·에이전트 어느 쪽이든 가능. `actor=human`/`actor=<agent-name>` provenance.
5. **Bootstrap 본질** — 본 문서는 Layer 1(=Raven)에 의해 자동 제공. 내용만 Layer 2.

### 4-pass 리뷰

| Pass | 도구 | 결과 |
|---|---|---|
| 1 | Claude (delegate_task) — 구조/경계/Tone | §0.5 위치 §0/§1 사이 ✅, "Raven 제품" 표기 → 추상화 권고 |
| 2 | Claude (delegate_task) — Anchor-fit + Cross-layer | L41-L42 사이 확정, §1 MCP 표와 충돌 0, "Layer 2로 한정" → cross-layer 조항 보강 |
| 3 | agy `--print` — Gemini cross-check | 위치 ✅, vendor-neutral 통과, "북극성 경계" 추상 risk → 명시 anchor 1줄 추가 |
| 4 | agy `--print` — Final patch review | Layer 1 leak 2건 발견 — `vault-bootstrap`/`SCHEMA` 직접 표기 → "자동 제공"/"데이터 규격(스키마)" 추상화 권고, 권고 반영 |

### 검증

| 항목 | 명령 | 결과 |
|---|---|---|
| Layer 1 leak (직접 표기) | `grep -nE 'vault-bootstrap\|SCHEMA[^.()\[]'` | ✅ 0건 |
| Vendor neutrality | `grep -nE 'Claude\|Cursor\|Hermes\|Codex\|Antigravity\|OpenAI\|Anthropic\|Google\|Gemini'` | ✅ 0건 |
| Layer 정의 self-contained | §0.5 본문 grep `Layer 1\|Layer 2\|제품\|활용` | ✅ 14개 anchor |
| 동기화 일치 | `cp -p templates → ~/Raven/raven-dev/_meta/agents/` 후 `diff -q` | ✅ 0 diff |

### 동기화

`raven/core/templates/agent/PROJECT-WORKFLOW.md` → `~/Raven/raven-dev/_meta/agents/PROJECT-WORKFLOW.md` (cp -p). 다른 4개 vault(`homelab`/`harumoa`/`babymoa`/`hermes-infra`)는 사용자 결정 보류.

### §13 컴포넌트화 원칙 무관 (doc 패치)

### 연관

- **v0.7.85** (`6a116e6`) — PROJECT-WORKFLOW.md 에이전트 CRUD 가이드 보강 (이 commit과 함께 §1 MCP 사용 규약 확장으로 직접 인접)
- **v0.7.78** (`PROJECT-WORKFLOW.md §0 + system 폴더 ❌ defense-in-depth`) — Lite bootstrap 외부 에이전트 경계 (이 commit이 일관 후속)
- **AGENTS.md §0.5** — Raven 제품 자체 north star 재정렬 (사용자 확인, v0.7.85 시점)
- **ADR-2026-07-06 stale loop** — Layer 2 north star (stale detect ↔ archive ↔ update)의 의인(擬人)화 단락이 본 §0.5와 의미 일치

---

## §1 — 검증 종합

| 검증 | 결과 |
|---|---|
| Layer 1 leak 0건 | ✅ |
| Vendor neutrality 0건 | ✅ |
| Layer 정의 self-contained | ✅ |
| raven-dev 동기화 일치 | ✅ (cp -p, diff -q 0) |
| `pytest tests/` | (문서 패치 — 코드 무관) N/A |

---

## §2 — 사이클 연속성

| 사이클 | 항목 |
|---|---|
| v0.7.85 | PROJECT-WORKFLOW.md CRUD 가이드 + RAG 4원칙 보강 |
| v0.7.86 | raven.sh status() MCP mode 정확성 silent hotfix |
| v0.7.87 | Dashboard 다크 `--color-primary-bg` override 누락 patch |
| **v0.7.88** | **PROJECT-WORKFLOW.md §0.5 layer-separation (Layer 1 vs Layer 2)** |
