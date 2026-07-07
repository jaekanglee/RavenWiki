# Changelog v0.7.90 — PROJECT-WORKFLOW.md readability refactor (PR1)

> **BLUF**: 외부 LLM 에이전트의 첫 30초 인지 부담을 줄이기 위해 `PROJECT-WORKFLOW.md` (Lite bootstrap Tier 2 표면) 를 **non-functional refactor** 했습니다. **정책 0% 변경**, "normative source = 1, 나머지 = cross-ref" 원칙으로 §0.5에 5건 normative를 응집. §0 Quick Start (7 steps) 신설 + §0 목차 추가. **NORTH STAR (원문 보존 + 증분 누적) 가드**: `wiki_update` 1.5배 차단 동작 그대로. 회귀 623/623 PASS + Lite bootstrap sync 5/5 marker.

이전 changelog: `_meta/changelog-v0.7.89.md`

---

## §0 — 변경 요약 (1 file + changelog, 333 → 333 LOC, normative 0 변경)

| 파일 | 변경 | LOC |
|---|---|---|
| `raven/core/templates/agent/PROJECT-WORKFLOW.md` | §0 Quick Start 신설 + §0.5 normative 5건 응집 (Layer 1/2 + North Star + 제품정체성 + 추측금지 + `_meta/system`) + §0 TOC + cross-ref 정리 | 333 → 333 (zero-sum) |
| `_meta/changelog-v0.7.90.md` (신설) | 본 changelog | — |

> **회귀 가드**: "normative 문장 추출 diff = 0" + "normative 외 위치는 모두 `→ §X.Y` 참조 패턴으로 변경". 1 file only, 정책 단어 단위 동일성은 목표 아님 (normative 단일 위치가 목표).

---

## §1 — 무엇을 바꿨나

### 1.1 §0 Quick Start 신설 (7 steps, 30초)

본문 최상단에 행동 시작 7단계:

```
1. Layer 1 / Layer 2 인지 — 나는 어디서 일하는가? (→ §0.5)
2. log.md — 최근 5-10줄
3. content/index.md 또는 tree — 전체 구조
4. 관련 문서 3-5개
5. SCHEMA.md — 데이터 계약
6. content/만 쓰기 — _meta/system/ 절대 ❌
7. wiki_lint — 커밋 전 필수
```

각 step 끝에 `→ §X.Y` jump. **Step 1이 Layer 인지인 이유**: "나는 누구인가?"가 이후 행동의 해석 전제. (사용자 피드백 반영.)

### 1.2 §0.5 normative 5건 응집 (single source of truth)

| # | Normative | 위치 (normative) | cross-ref로 바뀐 곳 |
|---|---|---|---|
| 1 | Layer 1/2 정의 | §0.5 §1) | §0 L17-18 흡수, §1.5 L173 ("vault not found" → §0.5) |
| 2 | 제품(=Layer 1) North Star "원문 보존 + 증분 누적" | §0.5 §2) | §1 wiki_update 1.5배 가드, §2 권한 표 머리말 |
| 3 | 제품 정체성 변경 금지 | §0.5 §3) | §9 L333 (type 9종 외), §9 L335 (외부 시스템) |
| 4 | 추측 금지 (도메인/구조/타입) | §0.5 §4) | §1.5 3단계 (wiki_search 먼저), §6 (vault 구조 따르기), §9 L329, §7.1 RAG 4원칙 |
| 5 | `_meta/system/` 절대 수정 금지 + `_meta/agents/` read-only | §0.5 §5) | §0 Step 6, §2 권한 표, §9 L331 |

**cross-ref 형식**: `→ §0.5 §3` (간결) 또는 `(→ §0.5)`. 단어 단위 동일성 ❌ (오히려 norm 외 위치에서 같은 규칙을 다른 문맥으로 인용 가능).

### 1.3 §0 목차 신설 (TOC only, `[↑ top]` ❌)

상단 §0에 §0~§11 한 줄 인덱스. 헤더 옆 `[↑ top]` 링크는 사용자 피드백대로 ❌ (산만).

### 1.4 §9 "하지 말 것" cross-ref화

각 ❌ 항목에 `→ §0.5 §X` / `→ §2` / `→ §3` 짧은 참조. 본문 반복 제거.

### 1.5 §11 신설 (이전 "이 문서에 없는 것" 절 번호 부여)

기존 "末" 절이었던 "이 문서에 없는 것 — 에이전트 스스로 판단/기억할 영역"에 §11 번호 부여. 정합.

---

## §2 — 정책 변경 0건 — 회귀 가드

**변경하지 않은 것 (의도적)**:
- §1 MCP 도구 9종 표 — 그대로
- §1.5 HTTP localhost 흐름 — 그대로
- §2 권한 표 — 그대로 (raw/ / content/ / _meta/ / log.md)
- §3 4가지 저장 신호 — 그대로
- §5 형식 요구사항 (BLUF, 슬러그, 요약) — 그대로
- §7.5 큐레이션 절차 — 그대로
- §8 멀티 에이전트 규칙 — 그대로
- **`wiki_update` 1.5배 차단 동작** — 그대로 (NORTH STAR 가드)
- Lite bootstrap 정책 (3종 = `_meta/agents/SCHEMA.md` + `PROJECT-WORKFLOW.md` + `log.md`) — 그대로

**Normative 단일 위치 정책**: normative 문장이 §0.5에 1번 등장하고, 다른 위치에서는 `→ §0.5 §N` 참조. 정책 단어 단위 동일성은 목표 아님 (normative 1곳이 진짜 single source of truth).

---

## §3 — 왜 이게 "non-functional refactor"인가

사용자 피드백 (3-round):

1. **1차 피드백**: "구조를 약간만 재배치하면 더 좋아질 것 같다" — "Quick Start (1분) → Vault 진입 → MCP → 문서규칙 → 저장판단 → 검증 → 금지 → 부록"
2. **2차 피드백**: "B(2-PR split) 추천 동의. PR1은 비기능적 리팩터링 (정책 변경 ❌), PR2에서 정책/구조 변경 + ADR 검토"
3. **3차 피드백**: "§0.6 신설 ❌, §0.5에 North Star 흡수. Layer 1/2 + North Star는 분리된 규범이 아니라 하나의 사고 흐름"

**원칙**:
- 정책 변경 = 0 (NORTH STAR 가드, 권한 표, 1.5배 차단 모두 그대로)
- normative source = 1곳 (§0.5), 나머지 = 참조
- ADR = 불요 (의미 변경 없음, 문서 리팩터링)
- Lite bootstrap 자동 sync — `raven meta sync --lite`로 기존 vault에 opt-in 적용 (운영자 명시 실행 시점에만, v0.7.65+ 정책)

---

## §4 — 검증

### 4.1 pytest 회귀

```
$ pytest tests/ -q --ignore=tests/curator
623 passed, 1 skipped, 1 warning in 39.59s
```

(v0.7.89 baseline과 동일 — 0 회귀)

### 4.2 Lite bootstrap sync (신규 vault 자동 주입)

```
vault create 시 자동 주입 확인:
  size: 13552 chars
  has Quick Start:        True
  has §0.5 normative 5:   True
  has TOC:                True
  has §11:                True
  has cross-ref style:    True (→ §0.5)
```

### 4.3 sync_meta (기존 vault 업뎃)

```
sync_meta --lite:
  {'copied': [], 'skipped': [...3 files...], 'errors': []}
```

신중하게 skipped — v0.7.65+ 정책 (사용자 의도 없이 덮어쓰지 않음). 운영자가 `--force`로 명시 실행 시 반영.

### 4.4 Dashboard build sanity

```
$ cd dashboard && npm run build
✓ built in 1.82s (변경 0)
```

### 4.5 norm 추출 grep verify

| Normative | normative 1곳 | cross-ref 위치 |
|---|---|---|
| Layer 1/2 | §0.5 L46-49 | §0 L21,23 / §1.5 / §2 / TOC |
| 제품 정체성 | §0.5 L56-58 | §9 L333, 335 |
| 추측 금지 | §0.5 L60-62 | §1.5 / §6 / §7.1 / §9 L329 |
| `_meta/system` | §0.5 L64-66 | §0 Step 6 / §2 / §9 L331 |
| North Star | §0.5 L51-54 | §1 (1.5배 가드) / §2 (권한) |

---

## §5 — AGENTS.md / SCHEMA.md 영향

- **AGENTS.md §4 (Lite bootstrap 정책)**: 변경 없음. 3종 그대로.
- **SCHEMA.md**: 변경 없음.
- **AGENTS.md §0.5 (Layer 1/2 라벨)**: 변경 없음. 본 changelog는 §0.5 layer-separation의 "표현 다듬기"이지 정의 변경 아님.

---

## §6 — 후속 작업 후보 (deferred, PR2+)

PR1은 non-functional refactor로 마감. 다음은 별도 사이클:

- **PR2**: §1-7 재배치/세분화 — 의미 변경 발생 시 ADR 동반 검토
- **PR3**: FAQ / 작업 흐름도 (Quick Start 보완) — 사용자가 요청 시
- **PR3+**: `docs/vault-patterns.md` 링크 + jump 최적화 (현재 §10 1줄)

Lite bootstrap sync: v0.7.65+ 정책 그대로. 기존 vault 운영자가 `raven meta sync --lite --force`로 opt-in 적용 가능. 자동 push ❌.
