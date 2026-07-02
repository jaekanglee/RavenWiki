---
title: "ADR: raw/ 폴더 — 사람 1차 / 에이전트 read-only 권한 분리"
date: 2026-07-02
status: accepted
audience: agent, human
supersedes: null
related:
  - AGENTS.md §0.5 (North Star: 사람 1차 사용자)
  - AGENTS.md §3 (사용자 3종: 사람 / 단일 에이전트 / 멀티 에이전트)
  - _meta/raw/articles/karpathy-llm-wiki-2026.md L36 (raw sources — immutable to LLM)
  - raven/mcp/tools/write.py L54-60 (is_read_only_slug)
  - raven/core/lint.py L450-451 (카파시 3-Layer 분리)
related_changelog: v0.7.50
type: rule
---

# ADR — raw/ 폴더 사람 1차 / 에이전트 read-only 권한 분리

> **한 줄**: Raven의 raw/ 폴더는 **사람이 직접 조회·수정·정리하는 1차 운영 영역**이며, LLM 에이전트는 **read-only**로만 접근한다. 이 권한 분리는 AGENTS.md §0.5 north star ("사람 1차 사용자로 하는 local-first markdown PKM vault")의 **vault 자유 폴더 구조 원칙**과 Karpathy LLM Wiki 원문 (L36, "You drop a new source into the raw collection") 양쪽과 정렬된다.

---

## 0. 맥락 (Context)

Raven은 AGENTS.md §0.5에 따라 **사람 1차 사용자**를 north star로 두고, Obsidian 모티브 + LLM Wiki 패턴 (선택적 +α)을 결합한 **local-first markdown PKM vault**다. v0.6.37 재정렬 이후 vault 구조는 사용자 자유로 두되, LLM Wiki의 raw/log.md/_meta/agents/ 패턴은 vault 안의 **특정 영역에 +α로 켜는 구조**로 합의됐다.

**현실 (v0.7.49 시점)**:
- `~/Raven/raven-dev/raw/test_source.md` 등 **사람이 raw/에 직접 자료를 떨어뜨리는 운영**이 실제 일어나고 있다 (자가 사용 vault 실측).
- 그러나 Dashboard/Sidebar/검색 어디에서도 raw/는 노출되지 않는다 (API: `server.py:215`는 `content_root.rglob`만 수행).
- 사람 진입점이 없으므로 **사람은 raw/를 CLI의 `ls`나 OS 파일관리자로만 관리**할 수 있다.
- 에이전트(MCP)는 `wiki_update`에서 raw/를 read-only로 차단되어 있다 (`raven/mcp/tools/write.py:54-60, 337-341`).

**문제**:
이 상태는 **AGENTS.md §0.5 north star에 어긋난다** — "사람 1차 사용자"라면서 vault의 한 영역(raw/)에서 사람 관리 인터페이스가 비어 있다. 또한 **Karpathy LLM Wiki 원문(L36)에도 어긋난다** — 원문은 "You drop a new source into the raw collection"으로 **사람이 drop하는 행위**를 명시적으로 전제하고 있다.

## 1. 결정 (Decision)

Raven의 raw/ 폴더는 **사람이 자유롭게 조회·수정·정리하는 1차 운영 영역**으로 두고, LLM 에이전트는 **read-only**로만 접근하도록 권한을 분리한다.

| 주체 | raw/ 권한 | 인터페이스 |
|---|---|---|
| **사람** (개발자 / 운영자) | **full CRUD** (조회 / 작성 / 수정 / 삭제 / 이동) | Dashboard panel (`/raw`), CLI (`raven raw ...`), OS 파일관리자 (직접) |
| **단일 에이전트** (LLM client) | **read-only** | MCP `wiki_read` (raw slug 조회), `wiki_ingest`로만 raw에 추가 가능 (단, **명시적 사용자 명령 시에만**) |
| **멀티 에이전트** | **read-only** (단일 에이전트와 동일, 동시성 보호 없음) | 동일 |

**`wiki_ingest`는 사람 운영자의 명시적 호출** (LLM이 자율적으로 호출 ❌). 이는 Karpathy 원문의 "You drop a new source... and tell the LLM to process it" 워크플로우와 일치한다.

## 2. 정당화 (Rationale)

### 2.1. North Star 정렬

| 원칙 | 정렬 |
|---|---|
| **AGENTS.md §0.5** ("사람 1차 사용자") | raw/도 사람이 자유롭게 관리 — **정렬** |
| **AGENTS.md §3** (에이전트 = MCP only) | 에이전트의 raw/ 접근은 MCP `wiki_read`로 단일화 — **정렬** |
| **P32 (Folder as First-Class Citizen)** | OS directory = folder, Raven은 raw/에 파일 안 만들어도 됨 — **정렬** |
| **Karpathy LLM Wiki L36** ("You drop a new source") | 사람 drop + LLM read-only — **정렬** |

### 2.2. Trade-off 명시

- **(+)** 사람 진입점이 생겨 raw/가 vault의 진짜 1급 시민이 됨 → 운영 일관성, north star 일치.
- **(+)** Lite bootstrap의 RULES.md / README.md가 "raw = 사람 1차"를 명시 → 에이전트가 잘못 호출하는 사고 방지 (이미 `wiki_update`로 차단 중이나, **RULES에 명문화**).
- **(+)** Dashboard에 `/raw` panel이 생기면 사용자가 "이 vault에 어떤 source가 들어와 있는지" 한눈에 파악 가능 → wiki 작성 결정에 도움.
- **(−)** raw/ panel을 Dashboard에 추가하면 Sidebar 트리에 raw/ 노드가 보이게 됨 → 기존 "OS directory = folder, sidebar가 filesystem을 반영" 원칙(P32) 적용하면 **자동으로 노출**되어야 함. **별도 토글 ❌**.
- **(−)** Lite bootstrap 5종(SCHEMA, RULES, README, PROJECT-WORKFLOW, log.md)에 raw/ 명시를 추가하면 문서 양이 늘어남 — **허용 범위 내**.

### 2.3. 거절한 대안 (Rejected Alternatives)

- **대안 A**: raw/ 정책 그대로 두고 사람 CLI로만 관리 → **거절**. §0.5 north star 위반 (사람 1차 사용자에게 vault 한 영역 진입점 부재).
- **대안 B**: LLM에게도 raw/ 쓰기 허용 → **거절**. Karpathy 원문(L36 "LLM never modifies raw") + 운영 안전성(raw/는 source of truth, 손상되면 컴파일 결과 신뢰성 붕괴).
- **대안 C**: raw/를 `content/`로 흡수 → **거절**. P32 (Folder as First-Class Citizen) 위반. 폴더는 OS directory = first-class, Raven이 raw/ 폴더를 합치거나 옮길 권한 ❌.
- **대안 D**: raw/ 전용 권한 플래그 (`raw_access: "agent"|"human"`)를 vault 메타에 추가 → **거절**. global 정책으로 충분, per-vault 분기는 YAGNI.

## 3. 구현 영향 (Implementation Impact)

### 3.1. Lite Bootstrap 5종 (사용자 vault `_meta/system/`) — 문서 갱신

| 파일 | 변경 |
|---|---|
| `templates/system/RULES.md` | "raw/ = 사람 1차, 에이전트 read-only" 섹션 추가 (현재 정의 없음) |
| `templates/system/README.md` | raw/ 도구 표면 안내 (Dashboard `/raw` panel, CLI `raven raw ...`) 추가 |
| `templates/system/SCHEMA.md` | 변경 ❌ (type 8종만 정의, raw는 type이 아니라 folder) |
| `templates/system/PROJECT-WORKFLOW.md` | raw → wiki ingest 워크플로우 다이어그램에 "사람 drop, LLM compile" 명시 |
| `templates/log.md` | 변경 ❌ (log는 action history, raw는 content) |

→ **Tier 1 leak 아님**: 모두 도구 표면 가이드 (사용자 vault 운영 매뉴얼). Raven 내부 정책 (OPERATIONS, agent/*, raven-policy)은 **v0.7.9 정책대로** vault에 복사 안 함.

### 3.2. API endpoints (신규 4개, 진입점 추가 ❌ — 기존 4 진입점 API의 raw/ 부분집합)

| Method | Path | 용도 |
|---|---|---|
| `GET` | `/api/vaults/{name}/raw` | raw/ 트리/메타 (sidebar raw/ panel용) |
| `GET` | `/api/vaults/{name}/raw/{path:path}` | raw/ 파일 내용 (조회) |
| `PUT` | `/api/vaults/{name}/raw/{path:path}` | raw/ 파일 작성/수정 (사람 OSS) |
| `DELETE` | `/api/vaults/{name}/raw/{path:path}` | raw/ 파일 삭제 (사람 OSS, _archive 미사용 — raw는 immutable-to-LLM, 사람도 의도적 삭제 가능) |

→ **이는 5번째 진입점 추가가 아님**: 기존 API 진입점(AGENTS.md §2, "HTTP API = Dashboard backend / 외부 자동화")의 기능 확장. ADR §4 대안 검토 완료.

### 3.3. MCP tools (변경 1건)

| Tool | 변경 |
|---|---|
| `wiki_ingest(source, project)` | **명시적 user command** 플래그 — 사람 운영자가 "이 자료 ingest 해"라고 명시한 경우에만 허용. 에이전트 자율 호출 ❌. |
| `wiki_read` | raw/ 경로 조회 허용 (read-only) — 사람 ↔ 에이전트 동일 |
| `wiki_update` | raw/ 차단 **유지** (변경 ❌) |

### 3.4. Dashboard 신규 panel (1개 route, 1개 sidebar 토글)

| 컴포넌트 | 위치 |
|---|---|
| `/raw` route | `dashboard/src/routes/RawPanel.tsx` — raw/ 파일 트리 + 선택 파일 뷰어 (read-only viewer) + 편집/삭제 액션 |
| Sidebar | `raw/` 노드를 OS directory 원칙(P32)대로 sidebar 트리에 자동 표시 (별도 토글 ❌) |
| Lite bootstrap README | "Dashboard 사용법" 섹션에 raw/ panel 안내 추가 |

### 3.5. Lite bootstrap 검증 (v0.7.9 정책 보강)

- `_meta/system/RULES.md` / `README.md`에 vendor 표기 절대 금지 (Raven north star).
- `tier_boundary` 테스트 갱신 — raw/ 권한 명시 패턴 (예: "raw: human write, agent read-only")이 **사용자 vault 문서에 등장**해도 통과해야 함 (이전엔 Tier 1 leak으로 차단됐을 가능성 → 검증).

## 4. 단계 (Phasing)

각 단계는 surgical하게 짜고 사용자 승인 받으며 진행:

| 단계 | 산출물 | 사용자 승인 |
|---|---|---|
| 0 | **이 ADR** | ✅ 본 문서 (2026-07-02) |
| 1 | API 4 endpoints + 회귀 테스트 | ⏸ 사용자 리뷰 |
| 2 | MCP `wiki_ingest` 명시적 user command 플래그 | ⏸ 사용자 리뷰 |
| 3 | Dashboard `/raw` panel + Sidebar raw/ 노드 자동 표시 | ⏸ 사용자 리뷰 |
| 4 | Lite bootstrap RULES.md / README.md / PROJECT-WORKFLOW.md 갱신 | ⏸ 사용자 리뷰 |
| 5 | tier_boundary 테스트 + 회귀 가드 | ⏸ 사용자 리뷰 |
| 6 | Changelog v0.7.50 + commit | ⏸ commit 승인 |

## 5. 결과 (Consequences)

### 5.1. 장점

- raw/가 **vault의 진짜 1급 시민**이 됨 — 사람 1차 north star 정렬
- Karpathy LLM Wiki 원문(L36) 정합 — 사람 drop, LLM read-only
- Dashboard panel이 "이 vault의 source가 뭐가 있는지" 한눈에 보여줌 → wiki 작성 결정 지원
- Lite bootstrap에 명시되어 **에이전트가 raw/를 잘못 호출하는 사고**를 RULES 단계에서 차단

### 5.2. 단점 / 수용

- raw/를 사람이 삭제해도 **로그/undo 없음** (raw는 immutable-to-LLM이지만 사람은 의도적 삭제 가능). 사용자가 OS 파일관리자로 복구 가능.
- 5번째 진입점이 **아님** — 기존 API의 확장. 단, Lite bootstrap에 raw/ 명시 추가는 사용자 표면 가이드 변경이므로 **사용자 재승인** 필요.
- 멀티 에이전트 동시 raw/ read는 충돌 없음 (read-only), 동시 write는 차단 (에이전트 권한 없음).

### 5.3. 회귀 위험 (Regression Risks)

- 기존 vault에서 raw/를 **에이전트가 호출**하던 워크플로우가 있다면 **명시적 user command 요구**로 막힘. 완화: CLI/MCP 문서에 "사용자 명시 호출" 패턴 가이드.
- Lite bootstrap 갱신 시 tier_boundary 테스트가 false positive 가능 → 단계 5에서 동시 검증.

## 6. 참고 (References)

- **North Star**: AGENTS.md §0.5
- **에이전트 인터페이스 단일화**: AGENTS.md §3, §5.5 (MCP = 단일 표준)
- **Folder = OS directory**: AGENTS.md §13 + P32
- **Lite bootstrap 5종 정책**: AGENTS.md §4
- **Karpathy 원문**: `_meta/raw/articles/karpathy-llm-wiki-2026.md` L36
- **현재 read-only 코드**: `raven/mcp/tools/write.py:54-60, 337-341`
- **현재 lint 3-Layer 분리**: `raven/core/lint.py:450-451`
- **현재 API content_root only**: `raven/api/server.py:215`
- **현재 prefix system areas**: `raven/core/slug.py:94`

---

## 부록 A. Self-audit (Karpathy §6 + AGENTS.md §6,9)

- [x] **명시 (Karpathy §6 ①)**: 사용자 raw/ 정책 정정 + north star 위반 사례 모두 명시
- [x] **단순성 (YAGNI)**: per-vault 권한 플래그 ❌, raw panel은 sidebar 자동 표시로 기존 P32 재사용
- [x] **Surgical (Karpathy §3)**: 6단계 phasing, 각 단계 사용자 승인
- [x] **검증 가능 (Goal-Driven)**: 단계 5의 tier_boundary 회귀 가드 + 단계별 verify-in-loop
- [x] **4 저장 신호**: 재사용성 ❌ / 인수인계 ✅ / scope/provenance ✅ (ADR) / 실패 리스크 ✅ (회귀 위험 명시)
