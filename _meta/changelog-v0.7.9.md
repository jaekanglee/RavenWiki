# raven v0.7.9 — `raven.agents` (Python adapter) 제거 — MCP only

> **핵심**: 사용자 정정 (2026-06-30) — "deprecated면 지금 날려도 되지않아?"
>
> **즉시 제거** (v0.7.9에서 deprecation 경고 ❌). v0.7.8 정책 (**에이전트 = MCP only**) 엄격히 적용. Python adapter = **코드베이스에서 제거**.

릴리스 일자: 2026-06-30
이전: v0.7.8 (MCP = 에이전트 단일 표준)

---

## 한 줄 요약

`raven/agents/` (Python adapter) 모듈 + `tests/test_agent.py` + `tests/test_v0_6_40_resource_scope.py` **삭제**. AGENTS.md/README.md/docs.vault-patterns.md 표현 갱신. 에이전트는 **MCP only (단일 표준)**.

## 1. 변경 사항

### 1-1. `raven/agents/` 모듈 삭제 (Agent, AgentScope, Provenance, Result, AgentVault)

- `raven/agents/__init__.py` — 제거
- `raven/agents/agent.py` — 제거
- `raven/agents/__pycache__/` — 제거

### 1-2. 테스트 파일 2개 삭제

- `tests/test_agent.py` — `from raven.agents import Agent, AgentScope` (모듈 의존)
- `tests/test_v0_6_40_resource_scope.py` — `from raven.agents import AgentScope` (v0.6.40 path scope 검증)

### 1-3. `raven/__init__.py` — 모듈 docstring 갱신

**Before**:
```python
"""raven — Multi-vault wiki engine + CLI + API + GUI.
Layered architecture:
    raven.core      — pure engine
    raven.agents    — agent adapters (LLM workers with scope + provenance, vendor-neutral)
    raven.cli       — Typer-based CLI
    raven.api       — FastAPI HTTP server
    dashboard/        — React 19 SPA
"""
```

**After (v0.7.9+)**:
```python
"""raven — Multi-vault wiki engine + CLI + API + MCP.
Layered architecture (v0.7.9+):
    raven.core      — pure engine
    raven.cli       — Typer-based CLI
    raven.api       — FastAPI HTTP server (Dashboard backend)
    dashboard/        — React 19 SPA
    raven.mcp       — FastMCP server (LLM agent standard protocol, v0.7.8+)

에이전트(LLM client) ↔ Raven 인터페이스 = MCP only (단일 표준).
사람/스크립트용: CLI / API / Dashboard 자유.
"""
```

### 1-4. `raven/api/server.py` — docstring 정리

- `"server.py — FastAPI surface over raven.core + raven.agents."` → `"over raven.core."` (의존 모듈 제거)

### 1-5. `README.md` — "Python 어댑터" 섹션 → "에이전트 인터페이스 (MCP)" 섹션

- **Before**: `from raven.agents import Agent, AgentScope` (40줄 코드 예시)
- **After**: "에이전트 ↔ Raven = MCP 단일 표준" + Claude Desktop MCP client 설정 예시 (`~/.config/Claude/claude_desktop_config.json`)
- vendor-neutral 정책 일치: "Claude/Cursor/Hermes/Codex" → "어떤 LLM 기반 agent든" (추상화)

### 1-6. `docs/vault-patterns.md` — Python 예시 → MCP 클라이언트 예시

- **Before**: `Agent.named(...)` + `AgentScope(...)` 2개 예시 블록
- **After**: `mcp.Client("http://127.0.0.1:8766/mcp")` 1개 + path scope 가이드

### 1-7. `AGENTS.md` §7 — "위 4 영역 벗어나는 경로" 갱신

```
+ **`raven/agents/` — v0.7.9+ 제거됨. Python adapter = deprecated. 에이전트는 MCP only.**
- `raven/mcp/` — 변경 시 import path 검증 필수 (v0.6.0+ namespace). **에이전트 표준 프로토콜 (v0.7.8+).**
```

### 1-8. `tests/test_v0_7_8_mcp_only_for_agents.py` — 2 tests 추가

1. `test_raven_agents_module_removed` — `raven/agents/` 디렉토리 부재 + `tests/test_agent.py` 부재
2. `test_no_python_adapter_imports_in_user_paths` — 라이브러리 코드에 `from raven.agents` import ❌

## 2. 검증

| 항목 | 결과 |
|---|---|
| pytest | **454 passed, 1 skipped** (v0.7.8: 477 → v0.7.9: 454, -23) |
| `raven/agents/` | ❌ **삭제됨** |
| `tests/test_agent.py` | ❌ 삭제됨 |
| `tests/test_v0_6_40_resource_scope.py` | ❌ 삭제됨 |
| 라이브러리 `from raven.agents` | ❌ 0건 (grep 검증) |
| README.md / AGENTS.md / vault-patterns.md | ✅ vendor-neutral + MCP only 명시 |
| vendor-neutral 회귀 가드 | ✅ 통과 (Claude/Cursor/Hermes/Codex 명시 ❌, 추상화) |

## 3. 의도

사용자 (2026-06-30):
> "deprecated면 지금 날려도 되지않아?"

→ v0.7.8에서 deprecation 경고 대신 **즉시 제거**:
- raven.agents (Python adapter) = 사용자/스크립트 보조 도구였으나, **에이전트 표준 위반**
- v0.7.8 정책 "에이전트 = MCP only"와 모순 (Python adapter도 에이전트 인터페이스로 사용 가능했음)
- **즉시 제거가 정직** (deprecation 경고 ❌, "쓰지 마세요"보다 "없음"이 명료)

## 4. 정책 (v0.7.9+ 최종)

| 대상 | 인터페이스 | 도구 |
|---|---|---|
| **사람 (직접)** | 자유 | Dashboard / CLI / API / HTTP |
| **사람/스크립트 (자동화)** | 자유 | CLI / API / HTTP / curl |
| **에이전트 (LLM client)** | **MCP only (단일 표준)** | MCP :8766 (HTTP) 또는 stdio |
| **에이전트 ↔ API 직접** | ❌ (정책 위반) | — |
| **에이전트 ↔ Python adapter** | ❌ (제거됨) | — |

## 5. 다음 단계

- **v0.8.0 (후보)**: MCP server 핵심 도구 정리 (read-only search + write_page + build 정도). 불필요한 도구 제거.
- **v0.8.1 (후보)**: 신규 사용자 onboarding — README → Lite bootstrap 5종 → MCP 가이드 (에이전트 사용자) → docs/vault-patterns.md

## 6. 호환성

- ✅ **v0.7.8 사용자**: raven/agents 사용 ❌ (이미 정책 위반 영역)
- ✅ **MCP client (Claude/Cursor/Hermes)**: 변경 ❌
- ✅ **사람/스크립트**: CLI / API / HTTP 그대로
- ⚠️ **`raven.agents` import 코드 (있다면)**: v0.7.9에서 import 실패 → MCP 마이그레이션 필요
- ⚠️ **tests/test_agent.py + test_v0_6_40_resource_scope.py**: 제거됨, 옛 정책 검증

## 7. 시각화

`_meta/diagrams/three-flows.png` — v0.7.8 그대로 (Flow 3 = "★ 표준, 단일" 강조). v0.7.9는 모듈 제거만, 다이어그램 갱신 ❌.