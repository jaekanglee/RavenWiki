# raven v0.7.13 — Makefile 청소 (Docker 우선, 로컬 host 실행 deprecated)

> **핵심**: 사용자 (2026-06-30) — "도커로만 올리고 내릴 거니까, 나머지 `dev` 같은 기존 레거시는 make 스크립트 청상해"
>
> v0.7.13: Makefile = **Docker 우선** (docker-build/up/down/logs/ps + install/test/clean/nuke/help). **옛 dev/status/stop/mcp/api/dashboard target 전부 제거**. 호스트에서 직접 띄울 일 없음 (Docker로 통일).

릴리스 일자: 2026-06-30
이전: v0.7.12 (Docker 셋업)

---

## 한 줄 요약

Makefile 246줄 → 96줄. **13개 target만**: help / install / venv-check / docker-{build,up,down,logs,ps} / test / test-quick / test-one / clean / nuke. 옛 v0.7.3~v0.7.11 host 실행 target 전부 제거. LaunchAgent (plist) 시도 흔적도 폐기 (v0.7.12 Docker로 대체).

## 1. 변경 사항

### 1-1. `Makefile` — 전면 단순화 (246 → 96 줄)

| 제거된 target | 이유 |
|---|---|
| `dev` (v0.7.3~v0.7.11, 4 진입점 background) | Docker compose로 대체 |
| `stop-dev` (PID 기반 kill) | `make docker-down` |
| `stop` (stop-dev wrapper) | `make docker-down` |
| `status` (4 진입점 lsof 검사) | `make docker-ps` |
| `mcp` (stdio foreground) | `docker compose exec api docker-entrypoint.sh mcp-stdio` |
| `api` (API foreground) | Docker compose `api` 서비스 |
| `dashboard` (Vite foreground) | Docker compose `dashboard` 서비스 |
| `raven` / `vault-list` / `where` / `link-check` (CLI shortcut) | `scripts/.venv/bin/python -m raven.cli ...` 또는 Docker exec |

| 유지된 target | 이유 |
|---|---|
| `help` | 명령 자동 표시 |
| `install` | 로컬 venv fallback (Docker 빌드 안 할 때) |
| `venv-check` | install 후 venv 검증 |
| `docker-build` / `docker-up` / `docker-down` / `docker-logs` / `docker-ps` | **Docker 표준** |
| `test` / `test-quick` / `test-one` | pytest |
| `clean` / `nuke` | 빌드 산출물 정리 |

### 1-2. `scripts/daemon.sh` + `raven-dev.plist` — **폐기**

v0.7.12 이전 LaunchAgent 시도 (macOS plist + shell script). v0.7.12 Docker compose로 대체되어 **불필요**. git history 보존 (커밋된 적 없음).

### 1-3. 회귀 가드 갱신 (Docker 우선 정책 반영)

| 파일 | 변경 |
|---|---|
| `tests/test_v0_7_11_one_set.py` | 5 tests → 4 tests (Makefile 청소 검증). `.PHONY: dev` 단독 ❌ 검증 추가 |
| `tests/test_v0_7_4_tailscale_host.py` | Makefile HOST 변수 검증 → `.env.example` HOST=0.0.0.0 검증으로 이동 (Docker compose 사용) |
| `tests/test_v0_7_7_mcp_accurate.py` | Makefile `make dev` 검증 → docker-entrypoint.sh 검증 (mcp-http/mcp-stdio 라우팅) |

### 1-4. `_meta/diagrams/api-vs-mcp.{md,html,svg,png,txt}` — **commit (기록 보존)**

v0.7.8 작업 중 만든 다이어그램 5개. Docker 우선 정책 전환에도 **진실은 그대로** — commit해서 보존.

## 2. 검증

| 항목 | 결과 |
|---|---|
| Makefile 라인 수 | 246 → **96** |
| Makefile `.PHONY` target 수 | 13개 (Docker 우선 + setup + test) |
| pytest | **463 passed, 1 skipped** (v0.7.12: 468 → v0.7.13: 463, -5 = 옛 가드 일부 제거) |
| 회귀 가드 | Docker 우선 정책 일치 |
| `make help` 출력 | ✅ 13개 target 표시 |

## 3. 의도

사용자 (2026-06-30):
> "도커로만 올리고 내릴 거니까, 나머지 `dev` 같은 기존 레거시는 make 스크립트 청상해"

→ **Docker 우선 정책 확정**. Makefile = Docker 셋업 도구. 옛 host 실행 흔적 전부 청소.

**호스트에서 직접 띄울 일 없음**:
- 모든 진입점 (API/Dashboard/MCP) = Docker compose
- 로컬 host 실행 = **deprecated** (make install은 venv setup용으로만 유지)

## 4. 사용법 (v0.7.13+)

```bash
# 1회 셋업
cp .env.example .env
# .env의 RAVEN_VAULTS_DIR 조정 (호스트 외부 vault 경로)

# 빌드 + 시작
make docker-build
make docker-up

# 운영
make docker-ps      # 컨테이너 상태
make docker-logs    # 로그 follow
curl http://localhost:8765/api/vaults

# 종료
make docker-down

# (옵션) 로컬 venv
make install        # venv setup
scripts/.venv/bin/python -m pytest tests/ -q   # 직접 테스트
```

## 5. 다음 단계

- **v0.7.14 (후보)**: docker compose로 vault 자동 migrate (기존 `~/Raven` → 호스트 경로 mount 검증)
- **v0.8.0 (후보)**: 신규 사용자 onboarding — README → Docker compose up → MCP 가이드

## 6. 호환성

- ✅ **v0.7.12 사용자**: `make dev` 등 사용 중이었으면 v0.7.13+에서 `make docker-up`으로 변경
- ✅ **Docker compose 셋업**: 영향 ❌
- ✅ **로컬 venv**: `make install` 유지 (테스트/local dev)
- ⚠️ **MCP stdio client (Claude Desktop)**: v0.7.12 이전 `make dev`로 띄운 server 없음 (Docker만 사용). stdio client 설정은 별도 guide

## 7. 시각화

**v0.7.12**: Makefile = docker-* + dev + status + stop + mcp + api + dashboard + ... (13+ targets)
**v0.7.13**: Makefile = docker-* + setup + test + cleanup + help (13 targets, 단순)

다음 사용자 입력 대기. 👋