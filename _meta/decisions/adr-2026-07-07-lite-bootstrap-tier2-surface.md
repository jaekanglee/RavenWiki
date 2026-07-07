---
title: "ADR: Lite bootstrap Tier 2 표면 강화 (v0.7.89-95, 7-사이클 묶음)"
date: 2026-07-07
status: accepted
audience: agent, human
supersedes: null
related:
  - AGENTS.md §4 (Lite bootstrap 정책: 3종 = `_meta/agents/SCHEMA.md` + `PROJECT-WORKFLOW.md` + `log.md`)
  - AGENTS.md §5.5 (MCP 표준화: 에이전트 ↔ Raven = MCP 단일)
  - AGENTS.md §9 (R9: vault 외부 시스템/폴더 수정 ❌)
  - _meta/decisions/adr-2026-07-07-mcp-wiki-get-guide.md (v0.7.91: MCP wiki_get_guide)
  - _meta/decisions/adr-2026-07-07-project-workflow-restructure-v1.md (v0.7.92: PROJECT-WORKFLOW §1-7 재배치)
  - _meta/changelog-v0.7.89.md ~ v0.7.95.md (7 사이클 묶음)
related_changelog: v0.7.89-95 묶음
type: rule
---

# ADR — Lite bootstrap Tier 2 표면 강화 (v0.7.89-95, 7-사이클 묶음)

> **한 줄**: Lite bootstrap 3종 (`_meta/agents/SCHEMA.md` / `PROJECT-WORKFLOW.md` / `log.md`) read-only viewer를 **두 layer × 두 모드 (REST + MCP)** 양쪽에 동등 contract로 노출 — 운영자(Tier 1) 와 에이전트(Tier 2) 가 같은 surface를 다른 진입점으로 조회. **NORTH STAR 가드 (원문 보존 + 증분 누적) + R9 (vault 외부 시스템 ❌) + Tier 1 leak 방지 (화이트리스트 fail-closed)** 모두 보존. **3 PR 패턴 (코드 → MCP → 문서 refactor)** 으로 7 사이클 진행.

## 0. 맥락 (Context)

v0.7.65+ Lite bootstrap 정책 (§4): 3종이 vault 진입 시 자동 주입되는 Tier 2 표면. 운영자가 자기 vault에 어떤 지침이 들어왔는지 확인하려면 v0.7.89 이전엔 vault filesystem 직접 read (사람 운영자 도구인 Dashboard 는 read-only viewer 없음) 또는 wiki_search 우회. **외부 LLM 에이전트는 filesystem read = R9 위반 위험**.

7 사이클 묶음 (v0.7.89-95) 으로:
- 운영자 (Tier 1) 가 **REST API** 로 read + diff 조회
- 에이전트 (Tier 2) 가 **MCP 표준 protocol** 로 read + diff 조회
- 같은 화이트리스트, 같은 응답 shape (contract 1:1)

## 1. 결정 (Decision)

**Lite bootstrap 3종 read-only surface를 4개 진입점 (REST read / REST diff / MCP read / MCP diff) 으로 노출한다. 모두 동일한 3종 화이트리스트 (`_meta/agents/SCHEMA.md` / `PROJECT-WORKFLOW.md` / `log.md`) + 동일한 응답 shape (read) / 동일한 unified diff 형식 (diff).**

### 1.1 4 진입점 contract

| 진입점 | Layer | read endpoint | diff endpoint | 비고 |
|---|---|---|---|---|
| REST API | Tier 1 (사람) | `GET /api/vaults/{name}/guide/{kind}` (v0.7.89) | `GET /api/vaults/{name}/guide-diff/{kind:path}` (v0.7.94) | Dashboard drawer 가 사용 |
| MCP | Tier 2 (에이전트) | `wiki_get_guide(vault, kind)` (v0.7.91) | `wiki_get_guide_diff(vault, kind)` (v0.7.95) | 표준 protocol, R9 정합 |

**화이트리스트 4 진입점 모두 동일**: 3종만 매칭, 그 외 403 fail-closed (Tier 1 leak 방지).

**응답 shape 1:1 (read)**:
```
{ok, vault, kind, content, size, modified}
```

**응답 shape 1:1 (diff)**:
```
{ok, vault, kind, identical, template_path, diff_lines, stats, truncated, truncation_note}
```

### 1.2 7-사이클 묶음 타임라인

| cycle | version | 핵심 결정 | 의미 변경? |
|---|---|---|---|
| 1 | v0.7.89 | REST `GET /guide/{kind}` 신설 | ❌ (신규 surface) |
| 2 | v0.7.90 | PROJECT-WORKFLOW.md readability PR1 (normative 1곳 + cross-ref) | ❌ (non-functional) |
| 3 | v0.7.91 | MCP `wiki_get_guide` 신설 (ADR 동반) | ✅ (Tier 2 표면 승격) |
| 4 | v0.7.92 | PROJECT-WORKFLOW §1-7 재배치 (PR2-B, ADR 동반) | ✅ (cross-ref 50+개) |
| 5 | v0.7.93 | 표준 surface 정합 명시 (안내 1줄) | ❌ (코드 0줄) |
| 6 | v0.7.94 | REST `GET /guide-diff/{kind:path}` 신설 (drawer Preview/Diff 토글) | ❌ (신규 surface) |
| 7 | v0.7.95 | MCP `wiki_get_guide_diff` 신설 (ADR 동반 X, v0.7.91 패턴 따라) | ❌ (Tier 2 표면 승격) |

ADR 동반: v0.7.91, v0.7.92 (의미 변경). 나머지 5개는 §5 ADR threshold 미달.

## 2. 이유 (Rationale)

### 2.1 R9 정합
> "에이전트는 vault 외부 시스템/폴더를 직접 수정하지 않는다."

Lite bootstrap 3종 read 시 **filesystem 직접 read = R9 strict 해석 위반 가능성** (v0.7.65+ 정책상 `_meta/agents/` 는 vault 내부지만, 그 contents를 agent가 raw read는 정책의도와 어긋남).

→ **표준 MCP surface 4종 = R9 risk 0**. 에이전트가 filesystem 우회 없이 read 가능.

### 2.2 Layer 정합 (Tier 1 ↔ Tier 2)
운영자 도구 (Tier 1) 와 에이전트 (Tier 2) 가 같은 데이터를 다른 진입점으로 조회. **contract 1:1** = 두 layer 가 같은 surface 인지 가능. v0.7.93 에서 명시.

### 2.3 NORTH STAR 가드 보존
> 제품 north star: **원문 보존 + 증분 누적**.

- Lite bootstrap 3종 = Raven이 자동 주입 (사람 운영자가 직접 편집 ❌)
- read + diff surface = **진단용** (편집 ❌)
- `wiki_update` 1.5배 차단 / 권한 / Tier 1 leak 방지 / `ensure_log()` 자동 append 모두 그대로

### 2.4 3 PR 패턴 (코드 → MCP → 문서 refactor)
사용자 합의로 정한 3-round PR 분할:
- **PR1** (v0.7.89+90): 코드 (Dashboard /guides) + non-functional refactor (PROJECT-WORKFLOW readability)
- **PR2-A** (v0.7.91): MCP 표면 (의미 변경, ADR)
- **PR2-B** (v0.7.92): PROJECT-WORKFLOW §1-7 재배치 (의미 변경, ADR)

이후 v0.7.93/94/95 는 **PR2 후속** (v0.7.93 정합 명시, v0.7.94 diff REST, v0.7.95 diff MCP) — 같은 묶음의 확장.

## 3. 결과 (Consequences)

### 3.1 긍정 (Positive)
- **운영자 (Dashboard) 와 에이전트 (MCP) 가 같은 Lite bootstrap surface 인지 가능** — v0.7.93 안내 1줄
- **mismatch 진단 가능** — v0.7.94 drawer + v0.7.95 MCP `wiki_get_guide_diff` 모두 unified diff (difflib 표준, 외부 의존성 0)
- **NORTH STAR 가드 4 진입점 모두 보존** — 1.5배 차단 / 권한 / Tier 1 leak / ensure_log() 자동 append
- **R9 정합** — 에이전트가 filesystem read 회피 가능
- **Lite bootstrap 정책 §4 (v0.7.65+) 의 intent 와 정합** — 3종이 Tier 2 표면임을 contract 1:1 으로 보장

### 3.2 부정 / 위험 (Negative / Risks)
- **4 진입점 drift 위험** — 화이트리스트 4개 (REST read / REST diff / MCP read / MCP diff) 가 각자 SOT. mitigation: pytest 16 tests (8 REST + 8 MCP) 강제.
- **diff truncation 200줄** — 대형 PROJECT-WORKFLOW.md (333줄) diff 가독성 ↓. mitigation: 200줄 cap + "전체 비교는 CLI `diff`" 안내.
- **URL 디자인 (v0.7.94)**: 처음엔 `/guide/{kind:path}/diff` 였으나 FastAPI path 매칭이 `{kind}/diff` 흡수 → `/guide-diff/{kind:path}` 로 변경. **테스트에서 발견 + 즉시 fix** (TDD 정합).

## 4. 대안 (Alternatives Considered)

| 대안 | 거부 이유 |
|---|---|
| **A. REST 만** (v0.7.89) | R9 위반 (에이전트 filesystem read). ❌ |
| **B. MCP 만** (v0.7.91) | Tier 1 도구 (Dashboard) 가 Tier 2 표면 사용 = layer 경계 약화. v0.7.93 에서 거부. |
| **C. Dashboard → MCP 직접 호출** (v0.7.93 A1) | Tier 1 → Tier 2 직접 호출 = layer 경계 약화. SSE/stateful 복잡성. ❌ |
| **D. 4 진입점 모두** (현재 결정) | 4 진입점 drift 위험 있지만 pytest 가드. contract 1:1 = 사용자 가치 즉시. ✅ |

## 5. ADR threshold 적용

본 묶음 (v0.7.89-95) 의 7 사이클 중:
- **v0.7.91, v0.7.92** = 의미 변경 (MCP 표면 신설, §1-7 재배치) → ADR 동반 ✅
- **v0.7.89, v0.7.90, v0.7.93, v0.7.94, v0.7.95** = 표면 신설 / non-functional / 표준 명시 → ADR 불요 (사용자 합의)

본 ADR 은 **묶음 차원의 retrospective** — 개별 사이클 ADR (v0.7.91, v0.7.92) 이 primary, 본 ADR 은 묶음 일관성 보존. 7 사이클 = Lite bootstrap Tier 2 표면 강화 **완결**.

## 6. 후속 작업 (deferred, **Lite bootstrap surface 강화는 v0.7.95 종착**)

- PR3 §1-7 통합/축소 (큰 패치, ADR 동반 검토)
- CLI `raven guide diff` (운영자 터미널 진단)
- Lite bootstrap 3종 외 다른 파일을 lite로 분류 (정책 결정 = ADR)

**v0.7.95 가 자연스러운 종착점**. 다음 사이클은 **사용자 명시 요청 시에만 시작**.

## 7. Cross-reference

### 7.1 SOT (Single Source of Truth) 결정 위치
- **Lite bootstrap 정책**: AGENTS.md §4 (v0.7.65+)
- **NORTH STAR (Layer 1 vs 2)**: AGENTS.md §0.5 (v0.7.88 5 commit 묶음)
- **MCP 표준화**: AGENTS.md §5.5 (v0.7.8+, v0.7.93 정합 명시)
- **R9 정책**: AGENTS.md §9 (vault 외부 시스템 ❌)
- **PROJECT-WORKFLOW.md normative 5건**: §0.5 (v0.7.90 PR1, v0.7.92 §1-7 재배치)
- **Lite bootstrap 3종 read-only contract 1:1**: 본 ADR §1.1 (4 진입점 매트릭스)

### 7.2 changelog 묶음
| version | cycle | 핵심 |
|---|---|---|
| v0.7.89 | 1 | REST read |
| v0.7.90 | 2 | PROJECT-WORKFLOW readability |
| v0.7.91 | 3 | MCP read (ADR) |
| v0.7.92 | 4 | PROJECT-WORKFLOW §1-7 재배치 (ADR) |
| v0.7.93 | 5 | 정합 명시 (1줄) |
| v0.7.94 | 6 | REST diff |
| v0.7.95 | 7 | MCP diff |

**Lite bootstrap Tier 2 표면 강화 v0.7.89-95 묶음 종착.**
