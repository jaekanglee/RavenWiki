# Changelog v0.7.86 — raven.sh status() MCP mode process args 기반 표시 (2026-07-07)

> **BLUF**: 사용자 정확한 진단 (2026-07-07) — "RAVEN_MCP_MODE=write로 재시작했는데 status는 read로 표시". silent hotfix: status()가 `$MCP_MODE` shell 변수 대신 *process args*에서 `--mode` 파싱 — env 의존 0, 실제 실행 모드와 100% 일치.
>
> 이전 changelog: `_meta/changelog-v0.7.85.md`

---

## §0 — commit 1개

| commit | 항목 | 파일 | 변경 |
|---|---|---|---|
| `5f67126` | A. raven.sh status() MCP mode process args 기반 | `raven.sh` | +16/−1 |

---

## A. raven.sh status() silent hotfix (`5f67126`)

### 진단 (사용자)

`RAVEN_MCP_MODE=write ./raven.sh restart`로 MCP를 write 모드로 띄웠지만 `./raven.sh status`는 `mode=read`로 표시 — *env fallthrough 버그*.

### 진짜 원인

```bash
# v0.7.83 silent hotfix
MCP_MODE="${RAVEN_MCP_MODE:-read}"
# ... start() 시점에만 env 읽어서 $MCP_MODE shell 변수 설정
# status()는 *별도 호출* — RAVEN_MCP_MODE env가 export되지 않음
# → $MCP_MODE가 fallback 'read'로 표시
```

→ **shell 변수 lifecycle** 문제. `RAVEN_MCP_MODE=write ./raven.sh restart`는 *한 번* env를 export → start()가 *그때* read → *그 다음 status()는 env 없음*.

### silent hotfix

- `mcp_mode_from_pid()` helper 신설: `ps -p "$pid" -o args=` 로 process args 추출 → `--mode` 다음 값 파싱
- `status()`가 `$mcp_mode_display` 변수 사용 (process args 기반)
- `$MCP_MODE` shell 변수 의존 제거
- echo 라인: `mode=${mcp_mode_display:-?}` (fallback `?` — PID 없을 때)

### 검증

| 시나리오 | 표시 |
|---|---|
| `RAVEN_MCP_MODE=write ./raven.sh restart` 후 `status` | `mode=write` ✅ |
| `./raven.sh restart` 후 `status` (env unset) | `mode=read` ✅ |
| 실제 process args | `python -m raven.mcp.cli ... --mode write` 또는 `... --mode read` |

→ process args 기반 = *실제 실행 모드*와 100% 일치. env 의존 0.

### silent hotfix 정책 §9 연속

v0.7.83 silent hotfix (MCP lifecycle 통합) + v0.7.86 silent hotfix (status 표시 정확성) — 운영자가 lifecycle/모드 확인할 때마다 *정확한 정보*.

---

## §1 — 검증 종합

| 검증 | 결과 |
|---|---|
| `RAVEN_MCP_MODE=write` 후 status 표시 | `mode=write` ✅ |
| `unset RAVEN_MCP_MODE` 후 status 표시 | `mode=read` ✅ (default) |
| `git push origin master` | 완료 |

---

## §2 — 사이클 연속성

| 사이클 | 항목 |
|---|---|
| v0.7.83 | silent stale hotfix: MCP lifecycle 통합 (MCP는 *별도 띄울 필요 없음*) |
| v0.7.85 | PROJECT-WORKFLOW.md 에이전트 CRUD 가이드 보강 (wiki-builder) |
| v0.7.86 | **status() MCP mode 표시 정확성 (silent hotfix 후속)** |

→ 운영자가 `./raven.sh` lifecycle 자동화에 이어 status 정확성까지 — *env 의존 0*.