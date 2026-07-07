# Changelog v0.7.92 — PROJECT-WORKFLOW.md §1-7 재배치 (PR2-B)

> **BLUF**: v0.7.90 PR1이 "normative 1곳 + cross-ref" 로 가독성 정합을 달성했지만, **§1-7 본문 순서는 "MCP 도구 → 권한 → 저장 → 형식 → 분업 → 폴더 → 체크리스트"** 였음. 사용자 워크플로우 ("지금 뭐 하지?") 정렬 위해 §1-7 본문 순서를 **Quick Start → MCP → 권한 → 저장 → 형식 → 폴더 → 검증 → 분업 → 멀티에이전트 → 금지** 순으로 재배치. **normative 단일 위치 (v0.7.90 정책) 불변**: §0.5 normative 5건, §2 권한, §3 저장신호 4가지, §8 금지 — 모두 단일 위치 유지. cross-ref 50+개 일괄 갱신. ADR 동반: `_meta/decisions/adr-2026-07-07-project-workflow-restructure-v1.md`. 회귀 631/631 PASS.

이전 changelog: `_meta/changelog-v0.7.91.md`

---

## §0 — 변경 요약 (1 file + 1 test + ADR + changelog, **normative 정책 0% 변경**)

| 파일 | 변경 | LOC |
|---|---|---|
| `raven/core/templates/agent/PROJECT-WORKFLOW.md` | §1-7 본문 재배치 + cross-ref 50+개 일괄 재작성 + §11 → §8.5 통합 | -2 (zero-sum, 구조 정합) |
| `tests/test_v0_7_1_lite_bootstrap_surface.py` | boundary declaration 헤더 assertion 정정 (이전 "이 문서에 없는 것" → 새 "에이전트 스스로 판단/기억할 영역") + 글쓰기 품질 판단 1줄 추가 | +5 |
| `_meta/decisions/adr-2026-07-07-project-workflow-restructure-v1.md` (신설) | ADR: §1-7 재배치 결정 (의미 변경 가능성 = cross-ref 50+개) | — |
| `_meta/changelog-v0.7.92.md` (신설) | 본 changelog | — |

---

## §1 — 무엇을 바꿨나

### 1.1 § 헤더 재배치 (14 → 13개)

| 이전 | → | 변경 후 | 비고 |
|---|---|---|---|
| §0 Quick Start | → | §0 (불변) | v0.7.90 신설, 정책 0 |
| §0.5 North Star | → | §0.5 (불변) | **normative 5건 SoT** |
| §0 TOC | → | §0 (불변) | v0.7.90 신설 |
| §1 MCP 도구 + §1.5 도달법 | → | **§1 MCP 사용법** (도구 + 도달법 + 권한 모드 통합) | 정책 불변, 통합 |
| §2 권한 | → | **§2 권한** (불변) | **normative** |
| §3 저장 결정 | → | **§3 저장 결정** (불변) | **normative** |
| §5 형식 | → | **§4 문서 작성 규칙** (shift -1) | 정책 불변 |
| §6 폴더 | → | **§5 폴더 구조** (shift -1) | 정책 불변 |
| §7 + §7.1 + §7.5 (체크리스트 + 자율점검 + 큐레이션) | → | **§6 검증 절차** (통합, shift -1) | 정책 불변, 통합 |
| §4 분업/트리거 | → | **§7 분업/트리거** (shift +3) | 정책 불변 |
| §8 멀티에이전트 | → | **§7.5 멀티에이전트 협업 규칙** | 정책 불변 |
| §9 하지 말 것 | → | **§8 하지 말 것** (shift -1) | **normative** (cross-ref) |
| §11 "이 문서에 없는 것" | → | **§8.5 부록: 에이전트 스스로 판단/기억할 영역** | 정책 불변, 흡수 |
| §10 다음 단계 | → | **§9 다음 단계** (shift -1) | 정책 불변 |

**normative 단일 위치 4개** (불변):
- §0.5 normative 5건 (Layer 1/2 / North Star / 제품정체성 / 추측금지 / `_meta/system`)
- §2 권한 (raw/ / content/ / _meta/ / log.md)
- §3 저장신호 4가지
- §8 하지 말 것 (cross-ref → §0.5 / §2 / §3)

### 1.2 cross-ref 50+개 일괄 갱신 (의미 변경 = 본 ADR의 핵심)

| 이전 | → | 변경 후 |
|---|---|---|
| `→ §5` (형식) | → | `→ §4` (문서규칙) |
| `→ §6` (폴더) | → | `→ §5` (폴더) |
| `→ §7` (체크리스트) | → | `→ §6` (검증) |
| `→ §7.1` (자율점검) | → | `→ §6.1` (자율점검) |
| `→ §7.5` (큐레이션) | → | `→ §6.5` (큐레이션) |
| `→ §8` (멀티에이전트) | → | `→ §7.5` (멀티에이전트) |
| `→ §9` (금지) | → | `→ §8` (금지) |
| `→ §10` (다음 단계) | → | `→ §9` (다음 단계) |
| `→ §11` (이 문서에 없는 것) | → | `→ §8.5` (부록) |

**cross-ref 보존 (불변)**: `→ §0.5`, `→ §0.5 §1~§5`, `→ §2`, `→ §3` — normative 단일 위치.

## §2 — 왜 이게 "의미 변경"인가 (ADR threshold)

사용자 3-round 합의로 정한 ADR threshold:
> "ADR은 정책 / 권한 / 데이터 계약 변경 시. 섹션 순서 변경은 doc refactor. **단, cross-ref 50+개가 의도적으로 재작성되면 의미 변경 가능성** → ADR 동반."

본 §1-7 재배치:
- 정책 0% 변경 (모든 정책/데이터 계약/권한 불변)
- **cross-ref 50+개 일괄 재작성** = 외부 에이전트가 cite한 § 번호가 깨짐
- §11 → §8.5 흡수 = boundary declaration 헤더 문구 변경 (boundary declaration **본문 4항목은 불변**)

→ ADR 동반. **rejected after first review / accepted with normative unchanged**.

## §3 — 사용자가 얻는 가치 (즉답성)

자주 묻는 4가지 질문의 cross-ref depth 변화:

| 질문 | 이전 | 변경 후 | 개선 |
|---|---|---|---|
| "lint 언제?" | §7 (3-depth) | §6.1 (2-depth) | -1 |
| "권한 어디?" | §2 (1-depth, 불변) | §2 (1-depth) | 0 |
| "쓰기 전 뭐?" | §3 (1-depth) + §5 (3-depth) | §3 (1-depth) + §4 (1-depth) | -2 |
| "금지 뭐?" | §9 (3-depth) | §8 (2-depth) | -1 |

§0 Quick Start 7 steps 의 cross-ref 도 §0 → §4 → §2 → §6 의 자연스러운 깊이 (top → mid → mid → top-mid).

## §4 — 검증

### 4.1 pytest 회귀

```
$ pytest tests/ -q --ignore=tests/curator
631 passed, 1 skipped, 1 warning in 39.61s
```

(v0.7.91 baseline 동일, 0 회귀)

### 4.2 Lite bootstrap sync (신규 vault 자동 주입)

```
13/13 marker PASS:
  §0 Quick Start / §0.5 normative 5 / §1 MCP 10종 /
  §2 권한 / §3 저장신호 / §4 문서규칙 (옛 §5) /
  §5 폴더 (옛 §6) / §6 검증 (옛 §7 통합) /
  §7 분업 (옛 §4) / §7.5 멀티에이전트 (옛 §8) /
  §8 금지 (옛 §9) / §8.5 부록 (옛 §11) / §9 다음 단계 (옛 §10)

옛 §10/§11 cross-ref 잔존: 0건 ✅
```

### 4.3 cross-ref 정합 grep

```
$ rg -n '§10\b|§11\b' PROJECT-WORKFLOW.md
  → 0건 (모두 §9 / §8.5 로 갱신)
```

### 4.4 Dashboard build (변경 0)

```
$ cd dashboard && npm run build
✓ built in 1.82s
```

## §5 — AGENTS.md / SCHEMA.md 영향

- **AGENTS.md §4 (Lite bootstrap 정책)**: 변경 없음. 3종 그대로.
- **AGENTS.md §0.5 (Layer 1/2 라벨)**: 변경 없음. 본 §1-7 재배치는 "본문 순서" 변경이지 "정의" 변경 ❌.
- **SCHEMA.md**: 변경 없음.
- **Lite bootstrap sync**: v0.7.65+ 정책 그대로. 기존 vault 운영자가 `raven meta sync --lite --force`로 opt-in 적용.

## §6 — 후속 작업 (deferred)

- **PR3+ §1-7 통합/축소**: §6 검증 절차, §1 MCP 사용법 같은 통합 절을 더 가볍게. Karpathy §1 simplicity first 적용.
- **§7 분업/트리거 위치 재검토**: 사용자 제안 순서에 명시 없음. 운영자 워크플로우 (검증 → 분업) vs. 학습자 워크플로우 (도구 → 분업). 후속 사용자/스테이크홀더 검토.
- **§0.5 + §8.5 통합 검토**: "normative" vs "self-judgment" 경계 정리. 단, 정책 의도가 다름 (§0.5 = "하지 마세요", §8.5 = "판단은 당신 몫") → 별도.
