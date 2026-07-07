# Changelog v0.7.96 — Lite bootstrap Tier 2 표면 강화 묶음 회고 (v0.7.89-95)

> **BLUF**: 7-사이클 묶음 (v0.7.89-95) 의 **묶음 회고 + 마무리**. 운영자 (Tier 1) 와 에이전트 (Tier 2) 가 Lite bootstrap 3종 read-only surface를 4 진입점 (REST read / REST diff / MCP read / MCP diff) 으로 contract 1:1 조회 가능. **NORTH STAR 가드 + R9 + Tier 1 leak 방지** 모두 보존. **본 묶음 = Lite bootstrap Tier 2 표면 강화 종착**. 다음 사이클은 사용자 명시 요청 시에만 시작.

이전 changelog: `_meta/changelog-v0.7.95.md`

---

## §0 — 묶음 메타

| 항목 | 값 |
|---|---|
| 묶음 | Lite bootstrap Tier 2 표면 강화 |
| 범위 | v0.7.89 ~ v0.7.95 (7 사이클) |
| 기간 | 2026-07-07 (1일) |
| 커밋 수 | 7 (`aabbec0` ~ `d214398`) |
| 추가된 surface | REST read + diff / MCP read + diff (4 진입점) |
| 정책 변경 | 0 (모두 NORTH STAR / R9 / Tier 1 leak 방지 정합) |
| ADR 동반 | 3 (v0.7.91 MCP, v0.7.92 §1-7 재배치, v0.7.96 묶음 회고) |

## §1 — 묶음 회고 (5 axes)

### 1.1 무엇을 만들었나 (what)

**Lite bootstrap 3종 read-only surface를 4 진입점 (2 layer × 2 모드) 으로 노출.**

- **Tier 1 (사람 운영자) = REST API**
  - v0.7.89 `GET /api/vaults/{name}/guide/{kind}` — read
  - v0.7.94 `GET /api/vaults/{name}/guide-diff/{kind:path}` — diff
- **Tier 2 (LLM 에이전트) = MCP 표준**
  - v0.7.91 `wiki_get_guide(vault, kind)` — read
  - v0.7.95 `wiki_get_guide_diff(vault, kind)` — diff

추가: Dashboard `/guides` 페이지 + VaultManage drawer (v0.7.89) + GuidesViewer 컴포넌트 (v0.7.89 + v0.7.94 Preview/Diff 토글) + PROJECT-WORKFLOW.md 가독성 refactor (v0.7.90 PR1 + v0.7.92 PR2-B).

### 1.2 어떻게 만들었나 (how)

**3 PR 패턴**:
- **PR1 (v0.7.89+90)**: 코드 (REST + Dashboard) + non-functional refactor (PROJECT-WORKFLOW.md readability, normative 1곳 + cross-ref)
- **PR2-A (v0.7.91)**: MCP 표면 (의미 변경, ADR 동반) — `_meta/decisions/adr-2026-07-07-mcp-wiki-get-guide.md`
- **PR2-B (v0.7.92)**: PROJECT-WORKFLOW §1-7 재배치 (의미 변경, ADR 동반) — `_meta/decisions/adr-2026-07-07-project-workflow-restructure-v1.md`

**이후 3 사이클 (v0.7.93-95)**: PR2 묶음의 자연스러운 후속 (정합 명시, diff REST, diff MCP).

### 1.3 왜 이렇게 (why)

- **R9 정합**: 에이전트가 Lite bootstrap 3종 read 시 filesystem 직접 read 회피 → 표준 protocol. v0.7.91 §2.1.
- **Layer 정합**: Tier 1 (사람) ↔ Tier 2 (에이전트) 양 layer 가 같은 surface contract 1:1 인지. v0.7.93 §1.
- **NORTH STAR 보존**: 1.5배 차단 / 권한 / Tier 1 leak / ensure_log() 자동 append 모두 그대로. v0.7.89-95 changelog §5 각 항목.

### 1.4 결과 (so what)

- **운영자 가치**: Dashboard drawer 에서 mismatch 즉시 진단 (v0.7.94 Preview/Diff).
- **에이전트 가치**: 표준 protocol 로 Lite bootstrap read + diff. R9 risk 0.
- **정책 정합**: Lite bootstrap 정책 §4 (v0.7.65+) 의 intent 와 100% 정합.
- **NORTH STAR**: 1.5배 차단 / 권한 / Tier 1 leak 방지 모두 보존.

### 1.5 통찰 (insight)

- **Tier 정합은 1 사이클이 아닌 묶음 작업** — v0.7.89 (REST) → v0.7.91 (MCP) → v0.7.93 (정합 명시) → v0.7.94/95 (diff). **1 사이클 단독으로는 layer 정합 달성 불가** — 양 layer 가 같은 surface 인지하는 시점이 v0.7.93.
- **URL 디자인은 테스트에서 발견** (v0.7.94) — `/guide/{kind:path}/diff` 의 FastAPI path 매칭 충돌. **TDD 가설**: TDD 정합은 "테스트 먼저 + 즉시 fix" 의 cycle.
- **3 PR 패턴 = 사용자 합의**: 큰 패치를 1 사이클에 묶지 않고 정책 / 코드 / 문서 분할. **사용자 3-round 합의가 ADR threshold (= 의미 변경) 보다 더 엄격한 분할** 만들어냄.

## §2 — 정책 / SOT 영향

- **NORTH STAR (제품 = 원문 보존 + 증분 누적)**: 보존 ✅
- **R9 (vault 외부 시스템 ❌)**: 강화 ✅ (에이전트 filesystem read 회피)
- **Lite bootstrap 정책 §4 (v0.7.65+)**: 정합 ✅ (3종 read-only surface = 4 진입점 contract 1:1)
- **AGENTS.md §5.5 (MCP 표준화)**: 정합 강화 ✅
- **PROJECT-WORKFLOW.md normative 5건** (§0.5): 보존 ✅
- **정책 변경 0**: 모든 사이클이 "NORTH STAR / R9 / Tier 1 leak 방지 / 권한" 보존

## §3 — ADR / changelog 인덱스 (Lite bootstrap Tier 2 표면 강화 묶음)

| version | changelog | ADR | 핵심 |
|---|---|---|---|
| v0.7.89 | `_meta/changelog-v0.7.89.md` | (없음) | REST read + Dashboard `/guides` + drawer |
| v0.7.90 | `_meta/changelog-v0.7.90.md` | (없음) | PROJECT-WORKFLOW readability PR1 (non-functional) |
| v0.7.91 | `_meta/changelog-v0.7.91.md` | `_meta/decisions/adr-2026-07-07-mcp-wiki-get-guide.md` | MCP `wiki_get_guide` (의미 변경) |
| v0.7.92 | `_meta/changelog-v0.7.92.md` | `_meta/decisions/adr-2026-07-07-project-workflow-restructure-v1.md` | PROJECT-WORKFLOW §1-7 재배치 (의미 변경) |
| v0.7.93 | `_meta/changelog-v0.7.93.md` | (없음) | 정합 명시 (코드 0줄) |
| v0.7.94 | `_meta/changelog-v0.7.94.md` | (없음) | REST diff + Dashboard Preview/Diff 토글 |
| v0.7.95 | `_meta/changelog-v0.7.95.md` | (없음) | MCP `wiki_get_guide_diff` |
| **v0.7.96** | (본 changelog) | `_meta/decisions/adr-2026-07-07-lite-bootstrap-tier2-surface.md` | **묶음 회고 + 종착** |

## §4 — 묶음 종착 선언

**v0.7.89-95 묶음 = Lite bootstrap Tier 2 표면 강화 종착**.

- 4 진입점 (REST read / REST diff / MCP read / MCP diff) contract 1:1 정합
- 화이트리스트 3종 (Tier 1 leak 방지) 4 진입점 모두 fail-closed
- NORTH STAR / R9 / 권한 / 1.5배 차단 모두 보존
- pytest 회귀 **647 passed** (v0.7.88 baseline 631 + 16 신규 = 647, 0 회귀)
- Dashboard `npm run build` (tsc strict) clean

**다음 사이클은 사용자 명시 요청 시에만 시작** — 본 묶음 외 새 작업이 없으면 추가 사이클 시작 안 함.

## §5 — 후속 가능 작업 (deferred, **시작 조건 = 사용자 명시 요청**)

- **PR3 §1-7 통합/축소** — §6 검증, §1 MCP 사용법 같은 통합 절 더 가볍게. 큰 패치 → ADR 동반 검토.
- **CLI `raven guide diff`** — 운영자가 터미널에서 diff 진단. v0.7.94/95 REST/MCP 와 짝.
- **Dashboard drawer에서 MCP 직접 호출** (v0.7.93 A1/A3) — 사용자 명시 요청 시 별도 사이클.
- **Lite bootstrap 3종 외 다른 파일을 lite로 분류** — 정책 결정 (ADR 필요).
- **MCP guide 결과 캐싱** (v0.7.91/95+ 후속) — 멀티 vault 효율성.

## §6 — 자가 점검 (에이전트로서)

- **NORTH STAR 보존**: 7 사이클 모두 1.5배 차단 / 권한 / Lite bootstrap 3종 그대로. ✅
- **R9 강화**: 에이전트 filesystem read 회피 가능 (v0.7.91/95). ✅
- **Tier 1 leak 방지**: 화이트리스트 4 진입점 fail-closed. ✅
- **사용자 정합**: 3-round 합의 (PR 분할, ADR threshold, 표준 정합) 모두 반영. ✅
- **자기 절제**: 사용자가 "다음 사이클 시작" 해도 매번 새 작업 만들지 않음 — 묶음 종착 후 명시 요청 대기. ✅
