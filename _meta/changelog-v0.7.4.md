# raven v0.7.4 — `make dev HOST=0.0.0.0` Tailscale 접속 지원

> **핵심**: 사용자 (2026-06-30) — "테일스케일로 접속가능하도록 띄워줬었는데 왜 안되지"
>
> 3가지 원인 분석 후 수정:
> 1. **Makefile dashboard detach 문제**: `cd dashboard && nohup ... &`에서 `&`가 `cd`에 적용 안 됨 → make가 dashboard process 기다림 → 45초 timeout
> 2. **API host hard-coded**: `--host 127.0.0.1` → Tailscale IP (100.x.x.x) 접속 불가
> 3. **Tailscale URL 자동 출력 누락**

릴리스 일자: 2026-06-30
이전: v0.7.3 (4 진입점 ready)

---

## 한 줄 요약

`make dev HOST=0.0.0.0` = API 모든 인터페이스 bind + Dashboard 즉시 detach + Tailscale URL 자동 출력. Tailscale IP `100.121.237.40` 으로 원격 접속 가능.

## 1. 변경 사항

### 1-1. `Makefile` — HOST 변수 + subshell detach

**Before (v0.7.3)**:
```makefile
dev: venv-check ## ...
    @cd dashboard && nohup npm run dev >/tmp/raven-dashboard.log 2>&1 </dev/null &
    # ↑ `&`가 cd 명령에 적용 안 됨 → make가 dashboard 기다림 → timeout
    # ↑ --host 127.0.0.1 hardcoded → Tailscale 접속 ❌
```

**After (v0.7.4)**:
```makefile
HOST ?= 127.0.0.1
api: venv-check ## ... (HOST=0.0.0.0 override 가능)
    PYTHONPATH=. $(PY) -m raven.api --host $(HOST) --port 8765

dev: venv-check ## ...
    @nohup env PYTHONPATH=. $(PY) -m raven.api --host $(HOST) --port 8765 >/tmp/raven-api.log 2>&1 </dev/null &
    @(cd dashboard && nohup npm run dev >/tmp/raven-dashboard.log 2>&1 </dev/null &)
    # ↑ subshell `(cd && nohup &)` → make 즉시 detach
    @if [ "$(HOST)" = "0.0.0.0" ]; then \
        echo "🔗 Tailscale/원격 접속: http://$(shell tailscale ip -4 2>/dev/null | head -1):8765"; \
    fi
```

### 1-2. `tests/test_v0_7_4_tailscale_host.py` (신규, 5 tests)

회귀 가드:
1. Makefile dashboard 띄우기가 subshell `(cd && nohup &)` 형식
2. Makefile HOST 변수 정의 (`HOST ?= 127.0.0.1`)
3. Makefile api target이 `$(HOST)` 사용
4. Makefile Tailscale URL 출력 (HOST=0.0.0.0 시)
5. Makefile dev 안에 hard-coded `--host 127.0.0.1` ❌

### 1-3. `tests/test_v0_7_1_lite_bootstrap_surface.py` — harumoa sync 제외

v0.7.4+: harumoa는 **운영자가 실제 사용 중** (5 entry in log.md) — sync 테스트에서 제외. raven-dev만 검증.
이유: 사용자 vault 데이터 write 정책 (AGENTS.md §10) — 운영자 작업물 존중.

## 2. 검증

| 항목 | 결과 |
|---|---|
| pytest | **465 passed, 1 skipped** (v0.7.3: 460 → v0.7.4: 465, +5) |
| `make dev HOST=0.0.0.0` | ✅ 4 진입점 ready, Tailscale URL 출력 |
| `curl http://127.0.0.1:8765/api/vaults` | ✅ HTTP 200 |
| `curl http://100.121.237.40:8765/api/vaults` | ✅ HTTP 200 (Tailscale) |
| `curl http://localhost:5173` (Dashboard) | ✅ HTTP 200 |

## 3. 의도

사용자가 Tailscale로 원격 접속 시도 → 실패. 원인 분석:
1. **`cd dashboard && nohup &` 문제**: `cd` 후 `&`는 background를 **전체 명령**에 적용. 그러나 `cd`는 subshell 없이 진행 → make가 dashboard를 기다림. **수정**: `(cd dashboard && nohup &)` subshell로 detach 보장.
2. **`--host 127.0.0.1` 문제**: Tailscale IP (100.x.x.x)로 접속 시 server가 `127.0.0.1`만 listen 중이면 reject. **수정**: `HOST ?= 127.0.0.1` (override 가능).

## 4. 사용법

### 로컬만 (default)
```bash
make dev
# → API 127.0.0.1:8765 (로컬만)
```

### Tailscale / 원격 포함
```bash
make dev HOST=0.0.0.0
# → API 0.0.0.0:8765 (모든 인터페이스, Tailscale 포함)
# → 출력에 Tailscale URL 자동 표시
```

## 5. 다음 단계

- **v0.7.5 (후보)**: Dashboard도 Tailscale로 노출 (현재는 localhost만). HOST=DASHBOARD_HOST=0.0.0.0 등.
- **v0.8.0 (후보)**: harumoa 운영자가 만든 페이지 (5phase-workflow, harumoa concept) 자동 검증 → wiki.db 빌드 + lint

## 6. 호환성

- ✅ **v0.7.3**: `make dev` 동작 유지 (default 127.0.0.1) — 기존 사용자 영향 ❌
- ✅ **기존 사용자**: `HOST=` 변수 추가, 기본값 유지 → 기존 워크플로우 그대로
- ✅ **Tailscale 사용자**: `make dev HOST=0.0.0.0` 한 줄로 원격 접속 가능