# raven v0.7.11 — `make dev` one-command = 풀세트 (4 진입점 일괄)

> **핵심**: 사용자 (2026-06-30) — "하나의 패키지처럼 세트로 올렸다 내렸다 하고 싶음. 따로 관리하기 너무 복잡."
>
> v0.7.11: `make dev` = **backend 3 (API/MCP HTTP/Dashboard) + MCP stdio** 모두 한 명령으로 띄움. `make stop`도 모두 종료. CLI는 `make raven ARGS="..."`로 on-demand (변경 ❌).

릴리스 일자: 2026-06-30
이전: v0.7.10 (MCP 진입점 fix)

---

## 한 줄 요약

`make dev` = API + Dashboard + MCP HTTP (port 8766) + MCP stdio (`setsid` for Linux, `nohup`/`disown` for macOS). **stdio는 본질상 background-safe ❌ (stdin 닫힘)** — 한계 정직 표시. CLI는 on-demand.

## 1. 변경 사항

### 1-1. `Makefile` `dev` target — MCP stdio 추가

```makefile
dev: venv-check
    # stop-dev → API background → MCP HTTP background → MCP stdio (setsid|nohup) → Dashboard background
    @( if command -v setsid >/dev/null 2>&1; then \
        setsid env PYTHONPATH=. $(PY) -m raven.mcp.cli --transport stdio \
            </dev/null >/tmp/raven-mcp-stdio.log 2>&1; \
      else \
        nohup env PYTHONPATH=. $(PY) -m raven.mcp.cli --transport stdio \
            </dev/null >/tmp/raven-mcp-stdio.log 2>&1; \
      fi ) &
    @sleep 2
```

→ **macOS (setsid 없음)**: `nohup ... &` 자동 fallback. stdin을 `</dev/null` redirect → server는 stdin EOF 감지 후 종료 (stdio의 본질).

### 1-2. `Makefile` `status` — MCP HTTP + MCP stdio 별도 표시

```
API (8765):           ✅ listen
Dashboard (5173):     ✅ listen
MCP HTTP (8766):      ✅ listen (background)
MCP stdio:            ✅ pid (setsid/nohup로 background 띄움)
```

### 1-3. `Makefile` `stop-dev` — port 8766 추가

```
@pids="$( { \
    lsof -ti :8765 -ti :5173 -ti :5174 -ti :8766 2>/dev/null; \
    ps -ef | awk '/[r]aven\.api|[r]aven\.mcp\.cli|[n]ode .*\/vite|[v]ite( |$$)/ {print $2}'; \
  } | sort -u )"
```

### 1-4. `tests/test_v0_7_11_one_set.py` (신규, 5 tests)

1. `test_make_dev_starts_all_4_entries` — make dev = API + MCP HTTP + MCP stdio + Dashboard
2. `test_make_status_checks_all_4` — status = 4개 모두 표시
3. `test_stop_dev_kills_all_4` — stop-dev = 4개 모두 종료
4. `test_make_dev_one_command_full_set` — "one command" + "full set" 박힘
5. `test_cli_not_in_make_dev` — dev target이 CLI 자동 실행 ❌ (on-demand 유지)

### 1-5. `tests/test_v0_7_7_mcp_accurate.py` 갱신

- `test_makefile_dev_starts_mcp_via_http`: `raven.mcp --transport` → `raven.mcp.cli --transport` (v0.7.10 fix)
- `test_makefile_status_handles_mcp_not_running`: "make mcp" 안내 → "make dev/make stop" 안내 (v0.7.11)

## 2. 검증

| 항목 | 결과 |
|---|---|
| pytest | **459 passed, 1 skipped** (v0.7.10: 454 → v0.7.11: 459, +5) |
| `make dev` 출력 | ✅ API + MCP HTTP + Dashboard ready, MCP stdio log: `📡 transport: stdio` |
| `make status` | ✅ 4개 모두 정확 표시 |

## 3. 한계 (정직)

| 한계 | 영향 |
|---|---|
| **MCP stdio = 본질상 background-safe ❌** | macOS에서 `nohup ... &` 시 stdin 닫힘 → server 종료. 단, **stdio client (Claude Desktop)가 fork/exec로 띄우는 표준 패턴은 정상** |
| **stdio 단일 인스턴스만 가능** | 한 머신에서 stdio MCP server 1개만. 동시 여러 client ❌ |

## 4. 다음 단계

- **v0.7.12 (후보)**: Docker 셋업 — `docker compose up` 1 명령, 다른 PC 환경에서 동일 동작
- **v0.8.0 (후보)**: MCP server 핵심 도구 정리

## 5. 호환성

- ✅ **v0.7.10 사용자**: 영향 ❌ (stdlib 추가만)
- ✅ **HTTP MCP client**: 변경 ❌
- ⚠️ **stdio MCP client**: make dev로 띄운 server는 stdin 닫힘 → client가 직접 띄우는 게 표준

## 6. 운영

```bash
make dev              # 4 진입점 (API + MCP HTTP + Dashboard + MCP stdio) one command
make dev HOST=0.0.0.0 # Tailscale 노출
make status           # 4개 상태
make stop             # 종료
make mcp              # 별도 stdio 띄우기 (foreground)
```