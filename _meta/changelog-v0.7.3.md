# raven v0.7.3 — `make dev` 4 진입점 통합 (product-ready dev stack)

> **핵심**: 사용자 의도 (2026-06-30) — "`make dev`는 프로덕트를 돌릴 준비". 즉, **4 진입점 (CLI / API / Dashboard / MCP)을 한 명령으로 띄움**.
>
> 기존: `make dev` = API + Dashboard만 띄움. CLI/MCP는 별도. → **harumoa팀이 `make dev` 후 CLI 죽었다고 착각한 사건** (실제로는 `raven` 명령 = 다른 Node 도구, 우리 Python Raven과 무관).
>
> v0.7.3: `make dev`가 4 진입점 모두 띄움. 사용자가 어느 진입점으로든 즉시 접근.

릴리스 일자: 2026-06-30
이전: 사용자 commit `9d2c8a5 docs(product): align Raven as zettelkasten PKM`

---

## 한 줄 요약

`make dev` = `CLI + API + Dashboard + MCP` 4 진입점 ready (product-ready dev stack). `make status`로 4개 모두 확인.

## 1. 변경 사항

### 1-1. `Makefile` `dev` target 강화

**Before (v0.7.2)**:
```makefile
dev: ## Run exactly one API + dashboard instance
    @echo "🚀 raven API → http://127.0.0.1:8765"
    @echo "🌐 dashboard  → http://localhost:5173/"
    cd dashboard && npm run dev    # foreground (사용자 shell 점유)
```

**After (v0.7.3+)**:
```makefile
dev: ## Run product-ready dev stack: CLI + API + Dashboard + MCP
    # API: nohup background → http://127.0.0.1:8765
    # MCP: nohup background (stdio) → logs: /tmp/raven-mcp.log
    # Dashboard: nohup background → http://localhost:5173 (or :5174)
    # CLI: `make raven ARGS="..."` 또는 scripts/.venv/bin/python -m raven.cli
```

→ **4 진입점 모두 background, 사용자 shell 안 점유**. ready 보고만 출력.

### 1-2. `Makefile` `stop-dev` target 강화

API + Vite + **MCP**까지 모두 stop. dynamic PID 탐지:
```makefile
ps -ef | awk '/[r]aven\.api|[r]aven\.mcp|[n]ode .*\/vite|[v]ite( |$$)/ {print $2}'
```

### 1-3. `Makefile` `status` target 강화

4개 모두 표시:
```
API (8765):     python3.1 ... (LISTEN)
Dashboard (5173): node ... (LISTEN)
MCP (stdio):    pid: 89254 (logs: /tmp/raven-mcp.log)
```

### 1-4. `Makefile` `stop` target 강화 (광범위 kill 회피)

이전 `stop`이 `make dev` wrapper까지 kill → 자기 자신 죽음. **광범위 kill 제거**, `stop-dev`만 호출. 자기 자신 안 죽음.

### 1-5. `raven/core/vault.py` + `raven/core/verify.py` 정합성 (PROJECT-WORKFLOW.md 5종)

Lite bootstrap 5종 자동 복사 — `_meta/agents/PROJECT-WORKFLOW.md` 추가. 사용자가 만든 `templates/agent/PROJECT-WORKFLOW.md` (5종 표준 위치) 가 vault.py에서 사용. verify.py path 일치 (`templates/agent/`, not `templates/agents/`).

### 1-6. 신규 `raven/core/templates/agent/PROJECT-WORKFLOW.md` (템플릿)

Lite bootstrap 5종 중 5번째. vault 사용자(팀/프로젝트)가 자기 워크플로우 정의.

## 2. 검증

| 항목 | 결과 |
|---|---|
| pytest | **460 passed, 1 skipped** (v0.7.2: 459 → v0.7.3: 460, +1) |
| test_bootstrap_verify (이전 7 실패 → 0) | ✅ 모두 통과 (verify.py path 정정) |
| `make dev` 실행 | ✅ API 12880 / Dashboard 12932 / MCP 89254 ready |
| `make status` | ✅ 4 진입점 모두 표시 |
| `make stop` | ✅ 자기 자신 안 죽음 (광범위 kill 제거) |

## 3. 의도

### 사용자 의도 분석 (2026-06-30)

- "`make dev`를 함으로써 실제 프로덕트를 돌릴 준비" — **한 명령으로 셋업 완료**
- 이전 `make dev` = API + Dashboard만 → CLI는 별도 → **사용자가 CLI 죽었다고 오인**
- harumoa 오케스트레이터 보고: "raven CLI: 런타임 미설치" → **다른 도구(Node `raven`)와 우리 Raven(Python) 혼동**

→ **v0.7.3 해결**:
1. `make dev` = 4 진입점 모두 ready (사용자 shell 점유 ❌)
2. `make raven ARGS="..."` 또는 `scripts/.venv/bin/python -m raven.cli` 명시
3. 다른 Node `raven` 명령이 PATH에 있어도 우리와 무관 — `_meta/agents/PROJECT-WORKFLOW.md`에 명시

## 4. 4 진입점 사용 가이드 (v0.7.3+)

| 진입점 | 사용법 | 상태 확인 |
|---|---|---|
| **CLI** | `make raven ARGS="vault list"` 또는 `scripts/.venv/bin/python -m raven.cli ...` | (명령마다 실행) |
| **API** | `curl http://127.0.0.1:8765/api/vaults` 또는 Dashboard가 자동 사용 | `make status` |
| **Dashboard** | 브라우저에서 http://localhost:5173 열기 | `make status` |
| **MCP** | Hermes/Claude/Cursor 등 MCP 클라이언트가 stdio 연결 | `make status` (pid 확인) |

## 5. 다음 단계

- **v0.7.4 (후보)**: `_meta/agents/PROJECT-WORKFLOW.md` 자동 템플릿 작성 — 사용자가 직접 작성한 harumoa 워크플로우를 다른 vault에도 적용 가능하게
- **v0.8.0 (후보)**: 신규 사용자 onboarding — README → Lite bootstrap 5종 → PROJECT-WORKFLOW.md → docs/vault-patterns.md 순서
- **harumoa 운영**: 첫 결정 페이지 + 첫 journal + LLM Wiki 패턴 첫 적용

## 6. 호환성

- ✅ **v0.7.2**: `make dev` 동작 유지 (API + Dashboard만 띄움) + 4 진입점 추가로 확장
- ✅ **기존 사용자**: `make raven`/`make where`/`make link-check` 등 그대로 동작
- ✅ **Lite bootstrap 신규 vault**: 5종 자동 복사 (PROJECT-WORKFLOW.md 포함)
- ⚠️ **Lite bootstrap 기존 vault**: `harumoa`/`raven-dev`는 사용자가 PROJECT-WORKFLOW.md 직접 작성 → 그대로 (Lite bootstrap 정책 "기존 파일 절대 덮어쓰지 않음" 준수)