# raven v0.7.36 — 사용자 표면 SOT 동기화(AGENTS.md→README.md) + Docker 이미지 SHA 핀 + 운영 절차 명시

> **핵심**: v0.7.35의 `_meta/system/AGENTS.md` → `README.md` 리네임이 사용자 표면(SOT 3종 + 대시보드 wizard)에는 적용되지 않아 **half-applied** 상태였던 사고를 마감했습니다. 동시에 docker-compose의 `image: raven:latest` 캐시가 stale 코드를 들고 있어 vault 생성이 silent fail하는 회귀 경로를 **이미지 GIT SHA 핀 + 박제 SHA 식별**로 잠갔습니다. README에 정식 Docker 운영 절을 추가해 향후 코드 변경 후 컨테이너 갱신 절차를 사용자 표면에서도 분명히 안내합니다.

릴리스 일자: 2026-07-01
이전: v0.7.35

---

## 1. 배경 — 사고 단서

사용자가 신규 vault 생성 시 다음 에러를 접수:

```
create failed: Lite bootstrap failed: could not copy _meta/system/AGENTS.md
from templates/system/AGENTS.md: [Errno 2] No such file or directory
```

조사 결과 — **로컬 raven 패키지 코드와 템플릿은 정상(RENAME 완료 상태)**, 그러나 다음 두 층이 stale:

1. **사용자 표면(SOT)** — `AGENTS.md` / `README.md` / dashboard `NewVaultWizard.tsx`가 여전히 `_meta/system/AGENTS.md`를 가리킴
2. **Docker 컨테이너** — 옛 `image: raven:latest` 캐시가 v0.7.35 리네임 이전의 `_bootstrap_lite`(=AGENTS.md 매핑)를 보유, 재기동만으로는 갱신 안 됨

→ SOT 동기화 + 이미지 핀 양쪽에서 잠금.

---

## 2. 변경 사항

### 2-1. 사용자 표면(SOT) 4곳 일제 동기화

* **`AGENTS.md`** (3곳):
  * line 14 — 본문 인용을 `_meta/system/AGENTS.md` → `_meta/system/README.md`로 정정.
  * line 94 — Tier 2 5종 표면화 표에서 `AGENTS.md` → `README.md` (툴 표면, v0.7.35+ 리네임 주석 부착).
  * line 108 — 독자 라우팅 표의 "사람 (운영자)" 시작 문서를 `_meta/system/README.md`로 정정.
* **`README.md`** (2곳):
  * line 105 — Lite bootstrap 표의 운영자 가이드 셀을 `README.md`로 정정, 표제목을 "vault 운영자 가이드 (Vault User Guide)"로 명시.
  * line 412 — "관련 문서" 절의 사용자 vault 경로 가이드를 `_meta/system/README.md`로 정정.
* **`dashboard/src/components/NewVaultWizard.tsx`** (line 494):
  * wizard Step 2 미리보기에 출력되는 5종 파일명을 `AGENTS.md` → `README.md`로 정정.

→ **현 master에서 `_meta/system/AGENTS.md`를 가리키는 SOT 0건** (`templates/ai-agent-wiki-1.0.0/` vendor 박제본과 changelog 역사는 보존).

### 2-2. Docker 이미지 핀 — yaml anchor + GIT_SHA 태그

* **`docker-compose.yml`**:
  * 이미지 빌드/태그 설정을 yaml anchor `x-raven-image`로 추출해 3개 서비스(`api`, `mcp-http`, `dashboard`)가 동일 정의(`<<: *raven_image`)를 공유.
  * `image: raven:latest` → `image: raven:${GIT_SHA:-latest}` 로 변경. 코드 변경 시 다른 SHA가 박힌 새 이미지가 생성되며, 이전 `:latest` 이미지로 자동 다운그레이드되는 사고 차단.
  * 빌드 인자로 `GIT_SHA` 전달 (없으면 `latest` fallback).
* **`Dockerfile`**:
  * runtime stage에 `ARG GIT_SHA=latest` + `ENV GIT_SHA=${GIT_SHA}` 선언.
  * `RUN printf '%s\n' "${GIT_SHA}" > /app/.git_sha` 로 이미지 안에 SHA 한 줄 박제 — `docker exec raven-api cat /app/.git_sha` 한 줄로 어떤 커밋이 박혔는지 즉시 식별 가능.

### 2-3. README — Docker 운영 정식 절 신설

* **`README.md`** ("Lite bootstrap" 절 다음에 신규 삽입):
  * **"Docker 운영 (v0.7.36+: 이미지 SHA 핀)"** 절 신설.
  * 사고 단서(이전 stale 캐시로 `Lite bootstrap failed` 발생)를 짧게 언급한 뒤 표준 3스텝 절차 제시:
    1. `docker compose build --build-arg GIT_SHA=$(git rev-parse --short HEAD)`
    2. `docker compose down && docker compose up -d`
    3. `docker exec raven-api cat /app/.git_sha` — 박힌 SHA 즉시 확인
  * "왜 이미지 핀 정책이 필요한가" 근거 한 단락 포함 (코드 변경 → 다른 태그 → 이전 이미지로 다운그레이드 차단 메커니즘).

### 2-4. 부수 — 검증 자동화 1줄 (`docker exec` 식별)

* 핀 정책이 실제로 컨테이너 안에서 동작하는지 확인할 단일 명령이 README에 박혀 있어, 향후 stale 의심 시 사용자/에이전트가 빠르게 진단 가능.

---

## 3. 검증 결과

| 항목 | 결과 | 비고 |
|---|---|---|
| **로컬 `_bootstrap_lite` 실제 호출** (임시 vault 생성 dry-run) | **Success** | `_meta/system/{SCHEMA,RULES,README}.md` + `PROJECT-WORKFLOW.md` + `log.md` 모두 정상. AGENTS.md 미생성 확인 |
| `pytest tests/ -q` (venv) | **488 passed, 1 skipped** | v0.7.34 이후 누적 회귀 없음 ✅ |
| `npx tsc -b --noEmit` | **Success** | dashboard 타입 검증 통과 |
| docker-compose yaml anchor 사용처 (3 expected) | **3/3** | `api`, `mcp-http`, `dashboard` 모두 `<<: *raven_image` 사용 |
| `GIT_SHA` 핀 위치 (compose + Dockerfile) | **2/2** | compose 빌드 인자 + Dockerfile 박제 양쪽 OK |
| SOT(`AGENTS.md` / `README.md` / dashboard tsx) `AGENTS.md` 잔존 참조 | **0건** | vendor 템플릿과 changelog 역사는 의도적 보존 |

---

## 4. 사용자 영향 (이번 사이클이 닫는 회귀)

* **vault 생성 실패**(`Lite bootstrap failed: ... templates/system/AGENTS.md`) — 컨테이너 재기동 후 자동 회복. 신규 vault 생성은 사용자 표면 SOT(`README.md`)와 코드 템플릿(`README.md`)이 일치하므로 정상 부트스트랩.
* **대시보드 wizard** — Step 2 미리보기 안내문이 실제 파일명과 일치 (이전엔 `AGENTS.md`라고 거짓 안내).
* **이후 코드 변경 시** — `git pull`만 받고 컨테이너를 재기동해도 옛 이미지가 그대로 떠 있는 사고 차단. 반드시 `docker compose build --build-arg GIT_SHA=$(git rev-parse --short HEAD)` 한 줄이 동반되어야 새 이미지로 올라감.

---

## 6. v0.7.36 hotfix (a) — `mcp-http` 컨테이너 Restarting 무한 루프 회귀

> 위 §1~§5 커밋 적용 후 컨테이너를 핀 이미지로 재기동(`docker compose up -d`)하니 `raven-mcp-http`만 즉시 죽고 무한 Restarting 루프에 빠지는 사고가 추가로 발견되었습니다. 같은 v0.7.36 사이클에 묶어 hotfix로 마감합니다.

### 6-1. 근본 원인

`docker-entrypoint.sh`의 `mcp-http` 분기가 **v0.7.21**부터 다음 두 uvicorn 옵션을 wiki-mcp 호출에 함께 던져 왔습니다:

```bash
exec python -m raven.mcp.cli --transport http --host "$HOST" --port "$PORT_MCP_HTTP" \
    --forwarded-allow-ips='*' --proxy-headers
```

**v0.7.23** 리팩토링에서 Tailscale 421 회피 옵션(`forwarded_allow_ips`, `proxy_headers`, `TrustedHostMiddleware`)은 `raven/mcp/cli.py` 내부에서 uvicorn 호출 시 직접 박아 넣는 방식으로 옮겼습니다. 그러나 **`docker-entrypoint.sh`의 exec 라인은 동기화 누락** — Typer 기반 `wiki-mcp` CLI는 위 두 옵션을 모르는 채 매번:

```
wiki-mcp: error: unrecognized arguments: --forwarded-allow-ips=* --proxy-headers
```

→ exit 2 → 컨테이너 Restarting 무한 루프. 다른 두 컨테이너(`api`, `dashboard`)는 영향 없음 (각자 다른 진입점).

### 6-2. 변경 사항

* **`scripts/docker-entrypoint.sh`**: `mcp-http` 분기 exec 라인에서 wiki-mcp가 모르는 두 옵션 제거 + 코멘트에 사고 원인/해결 기록.
* **`tests/test_v0_7_7_mcp_accurate.py`**: 신규 회귀 가드 `test_mcp_http_entrypoint_only_known_flags` — 향후 누가 entrypoint에 `--forwarded-allow-ips` / `--proxy-headers` 같은 Typer 모르는 옵션을 다시 박으면 즉시 차단. `cli.py` 자체엔 `forwarded_allow_ips`와 `proxy_headers=True`가 박혀 있는지 sanity check도 동봉.
* Tailscale 421 회피 동작은 **그대로 유지** — uvicorn 옵션이 `cli.py` 내부에 박혀 있어 외부 트래픽 Tailscale IP 신뢰 동작은 변함 없음.

### 6-3. 검증

| 항목 | 결과 | 비고 |
|---|---|---|
| `wiki-mcp --help` | **Success** | 5개 옵션만 노출 (실행 가능 인자) |
| 컨테이너 재기동 후 `raven-mcp-http` 상태 | **Up** (Restarting 사라짐) | `docker ps -a` 확인 |
| `docker logs raven-mcp-http` | **`unrecognized arguments` 에러 0건** | |
| Tailscale IP로 `/mcp` 호출 | **동작 유지** | cli.py 안 박힌 옵션이 그대로 TrustHost 우회 |
| `pytest tests/test_v0_7_7_mcp_accurate.py` | **4 passed (신규 1 포함)** | 회귀 가드 통과 |
| `pytest tests/` 전체 | **489 passed, 1 skipped** (v0.7.36 §3 = 488 → +1 신규 가드) | 회귀 없음 |

---

## 7. 부수 정리 (v0.7.36 사이클 마감 시)

* `sanity-fix-verify` vault registry entry 제거 — v0.7.36 §2 검증 dry-run 중 생성됐던 임시 vault. 디렉토리는 이미 사라졌으나 registry.json에 stale entry로 남아 `GET /api/vaults` 응답을 어지럽히던 항목. 컨테이너 안 `registry.remove('sanity-fix-verify')` 호출로 제거. 디스크 영향 0건.
* 죽은 컨테이너 3개 (`news-cron-dashboard-1` / `harumoa_app_qc` / `harumoa_db_qc`) — 7주~2개월 전 잔재. **`raven` 프로젝트 산출물이 아니므로 (사용자 자산 영역) 본 사이클에서 일괄 `docker rm` 하지 않음**. 사용자가 직접 정리하거나 다음 사이클에서 별도 의사결정 필요.

---

## 8. 다음 단계

* v0.7.37+: 사용자 표면 정확성 (silent failure 회피) 보강 사이클. 현 우선순위 후보:
  1. `raven vault create` 결과 메시지 표면 점검 — 생성 직후 `/api/vaults/{name}` 응답에 `bootstrap_files` 키를 추가해 클라(예: wizard)에서 "정확히 어느 5종이 복사됐는지" 즉시 확인할 수 있게.
  2. 또는 다음 페이지 단위 UX 사이클 (현행 GardenPage/PageView 후보).
