# raven v0.7.10 — `make dev` MCP 진입점 fix (`raven.mcp` → `raven.mcp.cli`)

> **핵심**: v0.7.9에서 `raven.agents` 제거 후 `make dev`로 4 진입점 띄우기 시도 → **MCP HTTP failed to start**. 원인: `python -m raven.mcp` (패키지 직접 실행) → `No module named raven.mcp.__main__`. 정직한 진입점 = `python -m raven.mcp.cli`.

릴리스 일자: 2026-06-30
이전: v0.7.9 (raven.agents 제거)

---

## 한 줄 요약

Makefile의 MCP 진입점 `$(PY) -m raven.mcp` → `$(PY) -m raven.mcp.cli` (정확한 entry point). `make mcp` target도 동일 정정. 회귀 가드 갱신.

## 1. 변경 사항

### 1-1. `Makefile` — MCP 진입점 정정

**Before (v0.7.9, 깨진 상태)**:
```makefile
dev: venv-check
    # ... (생략)
    @nohup env PYTHONPATH=. $(PY) -m raven.mcp --transport http --host $(HOST) --port 8766 >/tmp/raven-mcp.log 2>&1 </dev/null &
    # ❌ 'No module named raven.mcp.__main__; raven.mcp is a package'

mcp: venv-check
    PYTHONPATH=. $(PY) -m raven.mcp  # ❌ 같은 에러
```

**After (v0.7.10+)**:
```makefile
dev: venv-check
    # ... (생략)
    @nohup env PYTHONPATH=. $(PY) -m raven.mcp.cli --transport http --host $(HOST) --port 8766 >/tmp/raven-mcp.log 2>&1 </dev/null &
    # ✅ 정상 (progname: wiki-mcp)

mcp: venv-check
    PYTHONPATH=. $(PY) -m raven.mcp.cli --transport stdio  # ✅
```

### 1-2. `tests/test_v0_7_7_mcp_accurate.py` — 회귀 가드 갱신

- 옛: `assert "raven.mcp --transport http" in content`
- 신규: `assert "raven.mcp.cli --transport http" in content`
- 추가: `assert "nohup env PYTHONPATH=. $(PY) -m raven.mcp --transport" not in content` (패키지 직접 실행 ❌)

## 2. 검증

| 항목 | 결과 |
|---|---|
| `make dev` 출력 | ✅ 4 진입점 ready (API + MCP + Dashboard + CLI) |
| API :8765 | ✅ pid 39206, HTTP 200 |
| MCP :8766 | ✅ pid 39218, HTTP OK (이전 ❌ → ✅) |
| Dashboard :5173 | ✅ pid 39249, HTTP OK |
| pytest | ✅ 454 passed, 1 skipped (회귀 0) |
| test_v0_7_7_mcp_accurate | ✅ MCP 진입점 `raven.mcp.cli` 검증 |

## 3. 의도

v0.7.9 `raven.agents` 제거 후 `make dev`를 실제로 띄워봄 → **MCP HTTP failed to start**. 원인: 옛부터 박혀있던 `python -m raven.mcp` 호출 (패키지 직접 실행). 정직한 진입점 `python -m raven.mcp.cli`로 정정.

`raven/mcp/__init__.py` (패키지 선언) + `raven/mcp/cli.py` (entry point) — 분리. `-m` 옵션은 `__main__.py` OR `cli.py` 둘 중 하나.

**v0.7.7 회귀 가드가 옛 path `raven.mcp` 박혀있었음** — 패키지 직접 실행이 불가능함을 못 잡음. **v0.7.10에서 정확한 path로 갱신**.

## 4. 다음 단계

- **v0.8.0 (후보)**: MCP server 핵심 도구 정리 (read-only search + write_page + build 정도). 불필요한 도구 제거.
- **v0.8.1 (후보)**: 신규 사용자 onboarding — README → Lite bootstrap 5종 → MCP 가이드 (에이전트 사용자) → docs/vault-patterns.md

## 5. 호환성

- ✅ **v0.7.9**: `make dev`로 4 진입점 ready (이전 ❌ → ✅)
- ✅ **v0.7.8**: 영향 ❌ (MCP HTTP transport 정정)
- ✅ **MCP client (Claude/Cursor/Hermes)**: 변경 ❌ (MCP 표준 protocol 그대로)
- ✅ **MCP 진입점 검증**: `python -m raven.mcp.cli --help` 동작 OK (progname: `wiki-mcp`)

## 6. 운영

```bash
make dev              # 4 진입점 ready (API :8765 + MCP :8766 + Dashboard :5173)
make dev HOST=0.0.0.0  # Tailscale 노출
make status           # 4개 상태 확인
make stop             # 종료
make mcp              # stdio client용 (별도 terminal, foreground)
```