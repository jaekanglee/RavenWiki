---
title: "ADR: MCP `wiki_get_guide` — Lite bootstrap 3종 read-only surface"
date: 2026-07-07
status: accepted
audience: agent, human
supersedes: null
related:
  - AGENTS.md §4 (Lite bootstrap 정책: 3종 = `_meta/agents/SCHEMA.md` + `PROJECT-WORKFLOW.md` + `log.md`)
  - AGENTS.md §0.5 (Layer 2 = 에이전트 활용, vault-bound)
  - AGENTS.md §9 (R9: vault 외부 시스템/폴더 수정 ❌)
  - _meta/changelog-v0.7.89.md (REST surface `/api/vaults/{name}/guide/{kind}` v0.7.89 신설)
  - _meta/changelog-v0.7.90.md (PROJECT-WORKFLOW.md readability PR1, normative 1곳 + cross-ref)
related_changelog: v0.7.91
type: rule
---

# ADR — MCP `wiki_get_guide` Lite bootstrap 3종 read-only surface

> **한 줄**: REST `/api/vaults/{name}/guide/{kind}` (v0.7.89) 가 노출하는 Lite bootstrap 3종 read-only viewer를 **MCP 표면에도 동일 contract로 신설**한다 (`wiki_get_guide`, v0.7.91+). 9개 → 10개 read 도구. 화이트리스트 fail-closed 동일 (Tier 1 leak 방지). 에이전트가 R9("vault 외부 시스템 ❌) 회피하면서 표준 MCP로 PROJECT-WORKFLOW 본문 read 가능.

## 0. 맥락 (Context)

v0.7.89에서 Dashboard `/guides` 페이지용으로 REST surface가 신설됐다. Lite bootstrap 3종(`_meta/agents/SCHEMA.md` / `_meta/agents/PROJECT-WORKFLOW.md` / `log.md`)을 **화이트리스트**로 read-only 조회, 운영자가 "이 vault의 지침이 뭐지?"를 즉시 확인. Dashboard ux 가치를 만들었다.

남은 gap: **외부 LLM 에이전트가 표준 MCP로 같은 surface에 접근할 방법이 없다.** 현재 두 가지 회피 경로만 가능:

1. `wiki_search(vault, query="...")`로 우회 검색 — `wiki_search`는 `content/` 인덱스 기반이므로 `_meta/agents/` 본문은 검색되지 않거나 stale 인덱스 의존
2. 에이전트가 직접 vault 파일시스템 read — **R9 ("vault 외부 시스템/폴더 수정 ❌") 위반 가능성**. v0.7.65+ Lite bootstrap 정책상 `_meta/agents/`는 vault 내부이지만 그 contents를 agent가 raw read하는 건 **R9의 "외부 시스템" 정의**에 걸릴 수 있음

→ v0.7.90 PR1 (§0.5 normative "추측 금지" + Quick Start Step 1-2)에서 강조된 "vault 진입 즉시 PROJECT-WORKFLOW.md를 표준 절차로 read"가 MCP 클라이언트에게는 불가능. 모순.

## 1. 결정 (Decision)

**`wiki_get_guide(vault: str, kind: str) -> dict` 도구를 MCP read surface에 신설한다.** contract는 v0.7.89 REST endpoint와 1:1:

- 입력: `vault` (등록된 vault 이름), `kind` ∈ `{_meta/agents/SCHEMA.md, _meta/agents/PROJECT-WORKFLOW.md, log.md}`
- 출력: `{ok: True, vault, kind, content, size, modified}` (REST 응답과 동일 shape)
- 모드: `read` (모든 모드에서 사용 가능 — read-only)
- 화이트리스트 외 kind → tool error (MCP가 `ValueError(str(e))` 로 surface, REST 403과 동치)

도구 표 9개 → 10개. 권한 영향 ❌ (read-only, admin 권한 불요).

## 2. 이유 (Rationale)

### 2.1 표준화 (Standardization)
Raven의 north star는 "에이전트 ↔ Raven = MCP 표준 protocol 1개" (AGENTS.md §5.5). Lite bootstrap read surface가 REST에만 있으면 MCP 클라이언트는 우회해야 하고, 그 우회가 R9 위험을 만듬. **표준 표면 1개 = MCP 1개**로 정합.

### 2.2 Tier 1 leak 방지 (Whitelist fail-closed)
3종 화이트리스트는 v0.7.65+ Lite bootstrap 정책 (AGENTS.md §4) 의 **유일한 Tier 2 표면**. 이 surface를 MCP로 확장할 때도 동일 whitelist 강제 필수. `_meta/system/OPERATIONS.md` (Tier 1) 같은 민감 파일을 MCP로 노출하면 v0.7.65+ 정책 위반.

→ `_resolve_guide_path()` 가 whitelist 외 kind에서 `GuideNotFoundError` raise, MCP cli layer에서 `ValueError` 로 변환. `read.py`의 `wiki_get_guide`는 동일 contract로 응답.

### 2.3 단일 SoT (Single source of truth)
helper (`LITE_GUIDE_KINDS`, `_resolve_guide_path`, `read_guide`) 는 `raven/mcp/tools/__init__.py` 에 정의. REST endpoint (`raven/api/server.py:read_guide`) 와 **별도 화이트리스트**이지만 동일 3종 (의도적 — Raven 4개 진입점 정책상 두 layer의 화이트리스트는 각자 SOT). drift 위험은 pytest 회귀 가드 (8 tests)로 방지.

### 2.4 R9 정합
> "에이전트는 vault 외부 시스템/폴더를 직접 수정하지 않는다."

v0.7.91 이전: 에이ージェント가 PROJECT-WORKFLOW 본문을 보려면 vault 파일시스템 read가 사실상 유일한 방법. R9의 strict 해석으로는 위반.

v0.7.91 이후: 표준 MCP `wiki_get_guide(vault, kind="_meta/agents/PROJECT-WORKFLOW.md")` 한 번이면 본문 read. R9 risk 0.

## 3. 결과 (Consequences)

### 3.1 긍정 (Positive)
- **MCP 클라이언트의 정식 진입 경로 확보** — vault 진입 1단계 (PROJECT-WORKFLOW read) 가 표준 protocol로 통일. v0.7.90 PR1의 Quick Start Step 1-2가 MCP 환경에서도 즉시 실행 가능.
- **NORTH STAR 가드 동작 유지** — `_meta/system/` 등 Tier 1 폴더는 여전히 MCP로 read 불가. whitelist fail-closed.
- **도구 수 확장 가벼움** — 9→10개, read 그룹에 1개 추가. 권한 영향 0. 모드 3종 모두에서 사용 가능.
- **Dashboard /guides drawer 와 정합** — 양쪽 surface가 같은 화이트리스트 + 같은 응답 shape. frontend는 drawer 안에서 wiki_get_guide 결과를 받을 수 있게 진화 가능 (v0.7.92+ 검토).

### 3.2 부정 / 위험 (Negative / Risks)
- **REST ↔ MCP drift 위험** — 두 화이트리스트를 별도 유지하므로 향후 한쪽만 갱신될 가능성. mitigation: pytest 회귀 (`test_v0_7_89_guide_endpoint.py` + `test_v0_7_91_mcp_wiki_get_guide.py`) 가 화이트리스트 3종 모두 동일 contract를 강제.
- **에이전트의 "남용" 가능성** — 매 vault 진입마다 `wiki_get_guide`로 PROJECT-WORKFLOW read, 매 쓰기 전 `wiki_get_guide`로 SCHEMA read 등. 의도된 동작이므로 OK이나, 운영자가 "에이전트가 너무 자주 read" 를 보면 §1.5 권한 모드 조정 (read → write만 운영) 으로 대응 가능.
- **MCP 도구 표 normative 9→10** — PROJECT-WORKFLOW.md §1 도구 표 1줄 추가. **normative 변경인가?** 아니다 — 기존 read 도구 그룹 확장, 정책 변경 ❌. ADR 동반 (이 문서).

## 4. 대안 (Alternatives Considered)

| 대안 | 거부 이유 |
|---|---|
| **A. `wiki_get_page` 확장** (kind 파라미터 추가) | `wiki_get_page`는 content/ 페이지 + frontmatter + backlinks 반환. guide는 `_meta/agents/` 본문 + size + modified. 응답 shape 다름. 도구 1개에 2가지 contract = 유지보수 저하. |
| **B. `wiki_search`로 우회** | content/ 인덱스 기반이라 `_meta/agents/` 본문 정확히 안 잡힘. 사용자가 PROJECT-WORKFLOW 특정 절을 검색해도 hit 없음. ❌ |
| **C. 직접 파일 read 허용 (R9 예외)** | R9 정책 위반 + Lite bootstrap 정책 (§4) 위계 깨짐. ❌ |
| **D. MCP 신설 안 함, REST만** | R9 risk + MCP 클라이언트의 표준화 정책 (§5.5) 위반. ❌ |

→ **A (현재 결정)** 가 best.

## 5. 구현 / 검증 (Implementation / Verification)

### 변경 파일
| 파일 | 변경 |
|---|---|
| `raven/mcp/tools/__init__.py` | `LITE_GUIDE_KINDS`, `GuideNotFoundError`, `_resolve_guide_path`, `read_guide` (+93) |
| `raven/mcp/tools/read.py` | `wiki_get_guide` 함수 (+24) |
| `raven/mcp/cli.py` | `@mcp.tool(name="wiki_get_guide", ...)` 등록 + 헤더 코멘트 갱신 (+17) |
| `raven/core/templates/agent/PROJECT-WORKFLOW.md` | §1 MCP 도구 표에 `wiki_get_guide` 1줄 추가 (+1) |
| `tests/test_v0_7_91_mcp_wiki_get_guide.py` (신설) | 회귀 가드 8 tests |

### 검증
- `pytest tests/test_v0_7_91_mcp_wiki_get_guide.py -v` → **8/8 PASS**
- 전체 회귀: `pytest tests/ -q --ignore=tests/curator` → **631 passed, 1 skipped** (v0.7.90 baseline 623 + 8 신규)
- Dashboard `npm run build` → clean
- Lite bootstrap sync: raven `meta sync --lite` 로 기존 vault도 자동 업뎃 (opt-in)

### Cross-reference
- v0.7.89 (REST `/guide`): `_meta/changelog-v0.7.89.md` §0-§2
- v0.7.90 (PROJECT-WORKFLOW PR1): `_meta/changelog-v0.7.90.md` §1-§2
- v0.7.91 (MCP `wiki_get_guide`): 본 ADR + `_meta/changelog-v0.7.91.md` (작성 예정)
