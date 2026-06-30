# raven v0.7.7 — MCP 표시 버그 수정 (Codex false positive + stdio 부적합)

> **핵심**: 사용자 (2026-06-30) — "make dev 했는데 왜 MCP가 살아있다고 하지? pid 89254는 Codex인데"
>
> 2가지 근본 원인:
> 1. v0.7.3+ Makefile의 MCP background 실행 → MCP는 stdio 기반이라 background 시 stdin 닫혀서 즉시 죽음
> 2. `make status`의 `pgrep -f 'raven.mcp'`이 Codex Computer Use의 `SkyComputerUseClient`까지 매칭 (false positive, 89254 pid)

릴리스 일자: 2026-06-30
이전: v0.7.6 (PROJECT-WORKFLOW.md 강화)

---

## 한 줄 요약

`make dev`에서 MCP 자동 띄우기 제거 (stdio 부적합). `make mcp` 별도 target 추가 (foreground/별도 terminal). `make status`의 pgrep 패턴 `python.*-m raven.mcp`로 정확히 (Codex false positive ❌).

## 1. 변경 사항

### 1-1. `Makefile` `dev` target — MCP 자동 띄우기 제거

**Before (v0.7.3+)**:
```makefile
dev: venv-check ## Run product-ready dev stack: CLI + API + Dashboard + MCP
    @nohup env PYTHONPATH=. $(PY) -m raven.api --host $(HOST) --port 8765 >/tmp/raven-api.log 2>&1 </dev/null &
    @nohup env PYTHONPATH=. $(PY) -m raven.mcp >/tmp/raven-mcp.log 2>&1 </dev/null &  # ❌ stdio dies
    @(cd dashboard && nohup npm run dev >/tmp/raven-dashboard.log 2>&1 </dev/null &)
    # 출력: "🟢 4 진입점 ready: ... MCP: stdio (default vault)"
```

**After (v0.7.7+)**:
```makefile
dev: venv-check ## Run product-ready dev stack: CLI + API + Dashboard (3 진입점 ready)
    @nohup env PYTHONPATH=. $(PY) -m raven.api --host $(HOST) --port 8765 >/tmp/raven-api.log 2>&1 </dev/null &
    @(cd dashboard && nohup npm run dev >/tmp/raven-dashboard.log 2>&1 </dev/null &)
    # MCP는 띄우지 않음 (stdio 부적합)
    # 출력: "🟢 3 진입점 ready: ... ⚠️ MCP는 별도: 'make mcp' (foreground/별도 terminal, stdio 기반)"
```

### 1-2. `Makefile` `mcp` target 신규

```makefile
.PHONY: mcp
mcp: venv-check ## Run raven MCP (stdio, foreground — for MCP clients like Claude/Cursor)
	PYTHONPATH=. $(PY) -m raven.mcp
```

→ 사용자가 **별도 terminal**에서 `make mcp` 실행 → MCP client (Claude/Cursor/Hermes) 가 stdio로 연결.

### 1-3. `Makefile` `status` — pgrep 정확

**Before**:
```makefile
@pid=$$(pgrep -f 'raven.mcp' | head -1); \
# ❌ 'raven.mcp' substring 매칭 → Codex의 SkyComputerUseClient도 매칭
# (실제 pid 89254는 Codex Computer Use, raven.mcp 아님)
```

**After**:
```makefile
@pid=$$(pgrep -fl 'python.*-m raven\.mcp' | awk '{print $1}' | head -1); \
# ✅ 'python.*-m raven.mcp' 정확한 패턴 → Codex 매칭 안 됨
if [ -n "$$pid" ]; then echo "  pid: $$pid (logs: /tmp/raven-mcp.log)"; \
else echo "  (not running — see 'make mcp')"; fi
```

### 1-4. 신규 회귀 가드 `tests/test_v0_7_7_mcp_accurate.py` (4 tests)

1. `test_makefile_dev_does_not_start_mcp` — make dev는 MCP 자동 띄우기 ❌
2. `test_makefile_has_mcp_target` — make mcp 별도 target 존재
3. `test_makefile_status_pgrep_accurate` — pgrep `python.*-m raven.mcp` (Codex false positive ❌)
4. `test_makefile_status_handles_mcp_not_running` — 친절한 안내 (`make mcp`)

## 2. 검증

| 항목 | 결과 |
|---|---|
| pytest | **472 passed, 1 skipped** (v0.7.6: 468 → v0.7.7: 472, +4) |
| `make dev` 출력 | ✅ 3 진입점 (CLI/API/Dashboard) |
| `make status` MCP | ✅ "(not running — see 'make mcp')" 정확 |
| `make mcp --help` | ✅ 별도 target 명시 |
| API + Dashboard | ✅ 정상 살아있음 |

## 3. 의도

사용자 (2026-06-30):
> "왜 이래? 아니면 에러 없는 건가?"

→ **에러는 아님**. 단 **표시 버그 + stdio 부적합**:
1. make dev 시 MCP background 실행 ❌ (stdio는 stdin 살아있어야 함)
2. make status의 pgrep이 Codex 프로세스까지 매칭 (false positive)

→ **3 진입점으로 정리** + **MCP는 별도 target**. 정직하게 표시.

## 4. MCP 사용법 (v0.7.7+)

```bash
# Terminal 1 (메인)
make dev                   # API + Dashboard (background)

# Terminal 2 (MCP client용)
make mcp                   # stdio, foreground (Ctrl+C로 종료)
```

MCP client (Claude Desktop / Cursor / Hermes 등)는 `make mcp` 띄운 terminal의 stdio에 연결.

## 5. 다음 단계

- **v0.7.8 (후보)**: MCP 자동 재연결 로직 (client가 끊겼을 때 graceful restart) — 사용자 요청 시
- **v0.8.0 (후보)**: 신규 사용자 onboarding — README → Lite bootstrap 5종 → docs/vault-patterns.md

## 6. 호환성

- ✅ **v0.7.6 사용자**: make dev 동작 변경 (3 진입점) — 기존 4 진입점 기대 시 `make mcp` 별도 실행 안내
- ✅ **MCP client 설정**: 변경 ❌ (어떻게 띄우든 stdio 연결 동일)
- ✅ **make status pgrep**: false positive 제거
- ⚠️ **tmux/screen 사용자**: v0.7.7+에서 `make mcp`를 tmux pane/screen window에서 실행 권장