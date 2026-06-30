# raven v0.7.8 — MCP = 에이전트 단일 표준 (사용자 north star 재정립)

> **핵심**: 사용자 정정 (2026-06-30) — "MCP가 에이전트를 위한 프로토콜이잖아. 에이전트가 API 호출을 다이렉트로 하는 게 아니라, MCP만 바라보게 하고 싶음."
>
> v0.7.8 정책 재정립:
> - **사람**: 3개 진입 자유 (Dashboard / CLI / API 직접)
> - **에이전트**: **MCP 단일** (Python adapter ❌, API 직접 ❌)
> - **write 경로**: 단일 (API → Raven core → vault)

릴리스 일자: 2026-06-30
이전: v0.7.7 (MCP false positive 수정)

---

## 한 줄 요약

MCP = **에이전트 표준 프로토콜 (단일)**. 사람 = 3개 진입 자유. Python adapter (`raven.agents`)는 사람/스크립트 보조 도구. v0.7.7~v0.7.8 다이어그램 (three-flows.png) 갱신.

## 1. 변경 사항

### 1-1. `README.md` — 단일 에이전트 행 표현 갱신

**Before**:
```
| **Adapter** (에이전트) | Python scope-based API | `raven/agents/` |
...
| **단일 에이전트** | ✅ 안정 — scope + provenance 강제 | Python adapter |
```

**After (v0.7.8+)**:
```
| **Adapter** (Python, 사람/스크립트용) | scope-based API | `raven/agents/` |
...
| **단일 에이전트** | ⚠️ MCP가 표준 (Python adapter는 사람/스크립트 보조) | MCP :8766 |
```

### 1-2. `AGENTS.md` §3 — 사용자 3종 표 갱신 + 강조 줄

```markdown
| **단일 에이전트** | **MCP 표준 protocol** (사람/스크립트는 보조적으로 Python adapter 가능) | ✅ 지원 (MCP only) |

→ **에이전트 ↔ Raven 인터페이스 = MCP만 (단일 표준)**. Python adapter (`raven.agents`)는 사람/스크립트 보조 도구. 에이전트가 우리 API 직접 호출 ❌.
```

### 1-3. `AGENTS.md` §5.5 — 신규 섹션: "MCP = 에이전트 표준 프로토콜 (v0.7.8+)"

```markdown
### 5.5 MCP = 에이전트 표준 프로토콜 (v0.7.8+)

> **에이전트 ↔ Raven = MCP만 (단일).** Python adapter (`raven.agents`)는 사람/스크립트 보조 도구.

**이유** (4가지):
1. **표준화** — Claude/Cursor/Hermes 모두 MCP 표준 지원. 한 번 MCP server 만들면 모든 client 호환.
2. **Discovery** — MCP는 `tools/list`로 도구 자동 발견. API는 호출자가 endpoints 알아야.
3. **Tool schema** — MCP는 input/output schema 명시. LLM이 함수 호출 형식으로 자동 매핑.
4. **권한/모드** — MCP `--mode read/write/admin` 3단계 (안전망). API는 단순 endpoint.
```

### 1-4. `_meta/diagrams/three-flows.{png,txt}` — 다이어그램 갱신

- **Before**: "Flow 3: 에이전트 → MCP → API → Raven" (MCP = 옵션)
- **After**: **"Flow 3: 에이전트 → MCP → API → Raven (★ 표준, 단일)"** — 강조
- Footer: "에이전트는 MCP만 바라봄. Python adapter ❌, API 직접 ❌."
- 결론: "사람: 3개 진입 자유 / 에이전트: MCP 단일 / write 경로: 단일"

### 1-5. `tests/test_v0_7_8_mcp_only_for_agents.py` (신규, 5 tests)

회귀 가드:
1. `test_readme_agent_mcp_only` — README.md "단일 에이전트" 행: MCP 단일 명시
2. `test_agents_md_agent_mcp_only` — AGENTS.md §3: MCP 표준 박힘
3. `test_agents_md_python_adapter_deprecated_for_agent` — "API 직접 ❌" 명시
4. `test_three_flows_diagram_mcp_only` — 다이어그램 "MCP 단일" 박힘
5. `test_agents_md_mcp_protocol_reasons` — AGENTS.md §5.5 4가지 이유 (표준화/Discovery/schema/권한) 박힘

### 1-6. `tests/test_v0_7_7_mcp_accurate.py` 갱신

- 옛 `test_makefile_dev_does_not_start_mcp` → `test_makefile_dev_starts_mcp_via_http` (v0.7.8 정책 반영)
- make dev가 MCP를 HTTP transport로 자동 띄움 (port 8766, background-safe)

## 2. 검증

| 항목 | 결과 |
|---|---|
| pytest | **477 passed, 1 skipped** (v0.7.7: 472 → v0.7.8: 477, +5) |
| test_v0_7_8_mcp_only_for_agents | ✅ 5 passed (신규) |
| test_v0_7_7_mcp_accurate (갱신) | ✅ HTTP transport 명시 |
| README.md "단일 에이전트" 행 | ✅ "MCP :8766" |
| AGENTS.md §5.5 신규 | ✅ 4가지 이유 + "MCP만 (단일)" |
| three-flows.png | ✅ Flow 3 강조 갱신 |

## 3. 의도

사용자 (2026-06-30):
> "MCP가 에이전트를 위한 프로토콜이잖아. 에이전트가 API 호출을 다이렉트로 하는 게 아니라, MCP만 바라보게 하고 싶음."

→ **사용자 north star 재정립**: **에이전트 ↔ Raven 인터페이스 = MCP 단일 표준**.
- 사람 (CLI/Dashboard/API) = 자유 (정책 강제 ❌)
- 에이전트 (LLM client) = **MCP만** (단일 표준, 강제)

**이유** (정직):
1. **표준화** — Claude/Cursor/Hermes 모두 MCP 표준 지원
2. **Discovery** — `tools/list`로 자동 발견
3. **Tool schema** — LLM이 자동 매핑
4. **권한/모드** — read/write/admin 3단계 안전망

## 4. 정책 (v0.7.8+)

| 대상 | 인터페이스 | 정책 |
|---|---|---|
| **사람** | Dashboard / CLI / API 직접 | ✅ 자유 |
| **에이전트** | **MCP 단일** | ⚠️ 강제 (에이전트 ↔ Raven 표준) |
| **사람/스크립트** | Python adapter (`raven.agents`) | ✅ 보조 도구 |

## 5. 다음 단계

- **v0.7.9 (후보)**: `raven.agents` (Python adapter) deprecation 경고 추가 — "에이전트는 MCP 사용" 안내
- **v0.8.0 (후보)**: 신규 사용자 onboarding — README → Lite bootstrap 5종 → MCP 가이드 (에이전트 사용자) → docs/vault-patterns.md

## 6. 호환성

- ✅ **v0.7.7 사용자**: README/AGENTS.md 표현만 갱신 (기능 변경 ❌)
- ✅ **MCP client (Claude/Cursor/Hermes)**: 변경 ❌ (MCP 표준 그대로)
- ✅ **make dev**: 4 진입점 (API/MCP/Dashboard/CLI) 모두 background-safe
- ⚠️ **Python adapter 사용 중 (에이전트)**: v0.7.9부터 deprecation 경고
- ⚠️ **에이전트 ↔ API 직접 호출 (v0.7.8 이전)**: 정책 위반 — MCP 경유로 마이그레이션 권장

## 7. 시각화

`/Users/jaekanglee/Desktop/Dev/Project/Raven/_meta/diagrams/three-flows.png` (v0.7.8 갱신)
- Flow 1: 사람 → Dashboard → API
- Flow 2: 사람 → CLI → Raven (직접)
- Flow 3: **에이전트 → MCP → API (★ 표준, 단일)** — 강조
- Footer: 정책 요약 (사람 3개 자유, 에이전트 MCP 단일, write 단일)