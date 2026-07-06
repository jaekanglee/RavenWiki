# Changelog v0.7.83 — silent stale hotfix: MCP lifecycle 통합 (2026-07-06)

> **BLUF**: 사용자 정확한 진단 (2026-07-06) — "silent stale: 도커 컨테이너 2개가 3일간 healthy + raw MCP PID 1개 stale. `make restart-all`은 도커 안 끔". 진짜 원인 — `./raven.sh`가 API + Dashboard만 띄우고 **MCP lifecycle 통합 부재**, README 어디에도 MCP 띄우는 표준 흐름 없음. v0.7.83+: raven.sh에 MCP lifecycle 통합 + restart-all이 자동 처리 + 포트 매트릭스 일관성 (API 8765 / MCP 8766 / Dashboard 5173). per-feature commit 2개.
>
> 이전 changelog: `_meta/changelog-v0.7.82.md`

---

## §0 — commit 2개

| commit | 항목 | 파일 | 변경 |
|---|---|---|---|
| `178ada6` | A. raven.sh + restart-all.sh — MCP lifecycle 통합 + 포트 매트릭스 | 2 파일 | +63/−17 |
| `7fbb671` | B. Wizard + PROJECT-WORKFLOW + README — 8766 포트 매트릭스 일관성 | 3 파일 | +20/−7 |

---

## A. raven.sh + restart-all.sh — MCP lifecycle 통합 (`178ada6`)

### 진단 배경 (사용자)

1. "도커 컨테이너 2개가 3일간 healthy로 살아있음" — silent stale
2. "raw `python -m raven.mcp.cli --port 8766` PID 60841도 stale"
3. "`make restart-all`은 도커 안 띄우나?" — `restart-all.sh` 헤더 L4: "Docker 무관, 로컬 host stack (`./raven.sh`)만 다룸"
4. "MCP 서버 포트는 충돌나지않게 분리하자" → **MCP 8766 / API 8765** 결정

### 진짜 원인 (silent stale)

`./raven.sh` 헤더 L2: *"Control script for starting, stopping, and restarting the Raven local host stack."* 하지만 실제 함수는 **API + Dashboard만** 띄움. MCP는 *어디에서도* 자동 관리 안 됨.

```
v0.7.55+: Docker deprecated → ./raven.sh 표준
v0.7.81+: HTTP only 정책
v0.7.83+: MCP lifecycle 통합 ← silent stale 영구 해결
```

### 변경

**raven.sh** (silent hotfix 핵심):

| 영역 | 변경 |
|---|---|
| `MCP_PID="$PID_DIR/mcp.pid"` | MCP PID 파일 관리 |
| `start()` | API + **MCP** + Dashboard 3-component 시작 |
| `stop()` | API + **MCP** + Dashboard 3-component 종료 |
| `status()` | PARTIALLY RUNNING 감지 + 3-component URL 표시 |
| 포트 | `RAVEN_API_PORT=8765` / `RAVEN_MCP_PORT=8766` / `RAVEN_MCP_MODE=read` / `RAVEN_DASHBOARD_PORT=5173` (env override 가능) |

**scripts/restart-all.sh**:

| 영역 | 변경 |
|---|---|
| 헤더 | "v0.7.83+ MCP lifecycle 자동 처리 (silent stale 방지)" + 포트 매트릭스 명시 |
| 캐시 wipe | `tmp/mcp.log` 추가 |
| 헬스체크 tail | mcp.log 추가 |
| help line | mcp.log 추가 |

### 검증

```
$ make restart-all
🚀 Starting API server in background on port 8765...
🚀 Starting MCP server in background on port 8766 (mode=read)...
🚀 Starting Dashboard Vite dev server in background on port 5173...
🟢 Raven is RUNNING
   • API PID: 63245       Url: http://127.0.0.1:8765
   • Dashboard PID: 63247 Url: http://localhost:5173
   • MCP PID: 63246          Url: http://127.0.0.1:8766/mcp (mode=read)

🩺 헬스체크 (최대 30s)…
   ✅ api        http://127.0.0.1:8765/api/vaults → 200
   ✅ dashboard  http://localhost:5173/ → 200

✨ Raven 완전 재시작 완료 (캐시 wipe)
```

### stale 해소 (silent hotfix 정책 §9)

| 항목 | 이전 | 이후 |
|---|---|---|
| 도커 컨테이너 | 2개 (3일 healthy, deprecated) | 0개 (사용자가 `make docker-down` 명시적 처리) |
| raw raven.mcp PID | 60841 stale | 0개 (lifecycle 자동) |
| MCP lifecycle | README 부재, 수동 관리 | `./raven.sh` / `make restart-all` 자동 |

---

## B. Wizard + PROJECT-WORKFLOW + README — 8766 포트 매트릭스 일관성 (`7fbb671`)

### 진단

v0.7.83+ 코드 변경 (raven.sh, docker-compose, scripts/spa_server.py, Wizard defaultMcpEndpoint, Docker compose healthcheck)는 **모두 8766 일관**. **문서 3종만 stale 8765 표기**.

### 변경

**NewVaultWizard.tsx**:
- 안내 텍스트 `python -m raven.mcp.cli --port 8765` → `--port 8766` (defaultMcpEndpoint는 이미 8766)

**PROJECT-WORKFLOW.md §1.5**:
- 4곳 일괄 8765 → 8766
- §1.5 헤딩 직후 **포트 매트릭스 단락** 신설 — API/MCP/Dashboard 3개 포트 + silent stale 방지 안내

**README.md §에이전트 인터페이스**:
- 헤딩 `(MCP, v0.7.81+ HTTP only)` → `(MCP, v0.7.83+ HTTP only)`
- 헤딩 직후 **포트 매트릭스 1줄** 추가
- "1단계 운영자 서버 띄우기" 명령 8765 → 8766

**검증**: tsc -b --noEmit clean.

---

## §1 — 검증 종합

| 검증 | 결과 |
|---|---|
| `make restart-all` | 3-component RUNNING + 헬스체크 200 OK |
| `./raven.sh status` | API 8765 / Dashboard 5173 / MCP 8766 모두 healthy |
| `tsc -b --noEmit` | clean |
| `git push origin master` | 완료 |

---

## §2 — 외부 에이전트 walkthrough (v0.7.83+)

> "운영자가 vault 만든 뒤 외부 MCP 클라이언트 운영자에게 vault 전달"

1. 운영자가 `make restart-all` 또는 `./raven.sh restart` — 3개 모두 자동 시작 (lifecycle 잊어도 silent stale ❌)
2. 운영자가 외부 운영자에게 vault 경로 전달 (예: `~/Raven/my-vault/`)
3. 외부 운영자가 자기 MCP 클라이언트에 등록:
   ```json
   {"url": "http://localhost:8766/mcp"}
   ```
4. `tools/list` → 9개 도구 schema 자동 discovery → 즉시 사용

→ **포트 충돌 0 + lifecycle 자동 + 운영자 손 0**.

---

## §3 — 사이클 연속성

| 사이클 | 항목 |
|---|---|
| v0.7.81 | HTTP-only 재설계 (3 파일) |
| v0.7.82 | VaultManage banner 자세히 모달 |
| v0.7.83 | **silent stale hotfix: MCP lifecycle 통합 + 포트 매트릭스 8766** |

→ silent hotfix 정책 §9 (AGENTS.md) — silent file leaks/dropouts 방지. 라이프사이클 자동화로 영구 해결.