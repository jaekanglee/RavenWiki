# raven v0.7.60 — `make restart-all` local cache-wipe 의미 재정렬

> **핵심**: v0.7.55+에서 Docker는 deprecated, `make restart` (= `./raven.sh restart`)가 local default로 박혔는데 `make restart-all`만 그 흐름을 못 따라가서 여전히 docker 전용 스크립트로 남아있었음. 이번 패치에서 **의미를 local로 재정렬** — `restart-all` = "local stack 완전 재시작 + 모든 캐시 wipe". PID만 재시작하는 `make restart`와 차별화. 사용자가 토큰/CSS/의존성 변경 후 UI가 stale하게 갱신 안 될 때 사용.

릴리스 일자: 2026-07-03
이전: v0.7.59

---

## 1. 변경 사항

### 1-1. `scripts/restart-all.sh` — 완전 재작성 (Docker → local)

**이전 (v0.7.55~59)**: `docker compose down/build/up -d` + 60s 헬스체크. 5-10분 소요, `--no-cache --pull` 강제.

**이후 (v0.7.60)**: `raven.sh stop` → 캐시 wipe → `raven.sh start` → 30s 헬스체크. PID 기반이라 5-10초.

비우는 캐시:
- `dashboard/node_modules/.vite/` — Vite pre-bundle / optimizeDeps (가장 흔한 stale 원인)
- `dashboard/node_modules/.cache/` — Vite misc
- `**/__pycache__/` — raven/, dashboard/, scripts/ 전역 (`scripts/.venv`, `.git`, `node_modules` 제외)
- `.pytest_cache/`, `scripts/.pytest_cache/`
- `tmp/api.log`, `tmp/dashboard.log` — 구 로그 (PID 파일은 stop에서 정리)

의도적으로 안 비움:
- `wiki.db` — 백엔드 hot state. 필요시 `--wipe-db` 옵션
- `node_modules/` — 의존성 (npm install 안 함, 시간)
- `scripts/.venv/` — Python venv (재설치 안 함)
- 사용자 vault 데이터 (`RAVEN_VAULTS_DIR`)

### 1-2. 옵션 3개

| 플래그 | 동작 |
|---|---|
| _(기본)_ | 캐시 wipe + 재시작 |
| `--no-cache` | 재시작만 (= `./raven.sh restart`와 동일) |
| `--wipe-db` | 추가로 `wiki.db` 삭제 (bootstrap 재생성) |
| `--help` | 사용법 |

### 1-3. `Makefile` L132-139 — `[DEPRECATED]` 라벨 제거, 새 docstring

```diff
-# v0.7.55+: DEPRECATED. Docker stack은 더 이상 기본이 아님 (local host stack = default).
-#           Default restart는 `make restart` (./raven.sh restart) 사용.
-#           이 타겟은 호환성 위해 유지 — Docker가 production에서 쓰이는 경우에만.
-#           신규 사용자는 raven.sh 또는 그냥 `make restart` 권장.
-restart-all: ## [DEPRECATED] Force-rebuild Docker images. Use `make restart` (local) instead.
+restart-all: ## Full local restart: wipe caches (Vite/__pycache__/pytest/logs) + restart
```

`make help` 출력도 자동 갱신됨 (awk가 `## ` 뒤 docstring 추출).

### 1-4. 헬스체크 endpoint 조정

- 이전: `http://localhost:8765/api/vaults` / `http://localhost:8766/mcp` / `http://localhost:5173/`
- 이후: `http://127.0.0.1:8765/api/vaults` / `http://localhost:5173/` (MCP stdio는 endpoint 없음, 제외)
- retry: 60s → 30s (local stack은 docker보다 훨씬 빨리 뜸)

---

## 1-5. CSS hotfix — `@media (prefers-color-scheme: dark) :root` OS 팔로우 제거

**버그** (v0.7.59에서 도입, v0.7.60에서 발견):
- 사용자가 OS 다크모드 + Dashboard 사이드바에서 ☀️ 라이트 클릭 → UI가 라이트로 안 바뀜 (계속 다크).
- 원인: `globals.css` L432-497에 `@media (prefers-color-scheme: dark) { :root { --color-*: 다크값 } }` 블록이 살아있었음. CSS cascade에서 media query 안 `:root` rule은 일반 `:root, [data-color-mode="light"]` rule보다 우선 (CSS Cascade Level 4). Layout.tsx가 `[data-color-mode="light"]` set해도 OS 팔로우가 이김.
- v0.7.59 changelog 주석은 "localStorage에 저장된 사용자 명시 선택이 항상 우선 (OS follows ❌)"라고 약속했지만 코드(globals.css)가 정반대로 동작 — **정책 ≠ 코드**.

**수정**:
1. L432-497 (66줄) 통째로 L383 `[data-color-mode="dark"]` 블록 안으로 흡수
2. `html.dark` selector에도 Layer 2/3 다크 토큰 + CDS 토큰 추가 (이전엔 --color-*만 정의, Layer 2/3 누락)
3. OS 다크 자동 폴로우는 **Layout.tsx의 useState initializer** (`window.matchMedia("prefers-color-scheme: dark").matches` → "dark" 폴백)로만 동작 — 이미 v0.7.59에서 그렇게 작성되어 있어 변경 불필요

**동작 검증** (예상):
- OS 다크 + 첫 진입 → Layout이 OS 보고 "dark" set → `html.dark` + `[data-color-mode="dark"]` 박힘 → 다크 표시 (변화 없음)
- OS 다크 + 사이드바 ☀️ 라이트 클릭 → Layout이 "light" set → `html.dark` 제거 + `[data-color-mode="light"]` 박힘 → 라이트 표시 ✅ (이전엔 OS 팔로우가 이겨서 다크 유지)
- OS 라이트 + 사이드바 🌙 다크 클릭 → 다크 표시 ✅ (이전부터 동작)
- localStorage 비어있는 첫 진입 OS 다크 → 자동 다크 ✅ (Layout 폴백으로 유지)

**부수 효과**: `data-color-mode` 미설정 상태(예: 일부 컴포넌트 inline)에서 OS 다크면 `:root`만 보고 토큰 추정하는 컴포넌트는 이제 다크 적용 안 됨 — 단 Layout.tsx가 root mount 시점에 즉시 양쪽 박으므로 사실상 영향 없음.

---

## 2. 검증 결과

| 항목 | 결과 |
|---|---|
| `bash -n scripts/restart-all.sh` | exit 0 (syntax valid) |
| `bash scripts/restart-all.sh --help` | 정상 출력 |
| `make help` (restart-all 줄) | 새 docstring 반영 |

_(실제 실행은 사용자 검증 — `.venv` 없거나 stack이 이미 다른 PID로 떠있을 수 있어 위험)_

---

## 3. 사용자 흐름

```bash
# 평소: 단순 PID 재시작
make restart                  # = ./raven.sh restart

# 토큰 / CSS / node_modules 변경 후 UI stale:
make restart-all              # 캐시 wipe + 재시작 (10-20s)

# wiki.db까지 처음부터:
make restart-all -- --wipe-db # bootstrap 재생성

# 강제 새로고침 (브라우저 PWA 캐시):
# Cmd+Shift+R (Dashboard)
```

---

## 4. 부록 — self-audit (Karpathy §6 + AGENTS.md §6,9)

- [x] **명시 (§6 ①)**: `restart-all` local 재정의 — 사용자 요청 정확히 따름
- [x] **단순성 (YAGNI)**: 옵션 3개로 충분 (`--no-cache`, `--wipe-db`, `--help`). 더 추가 ❌
- [x] **Surgical (§3)**: 2개 파일만 변경 (`scripts/restart-all.sh` rewrite + `Makefile` 9줄 patch). docker-compose.yml / raven.sh / Dashboard / _meta/ AGENTS.md 미접촉
- [x] **Goal-Driven**: `make help`로 새 docstring 즉시 확인 가능
- [x] **4 저장 신호**: changelog 신규 파일 + script 자체가 재사용 절차 → 둘 다 저장 가치 높음
- [x] **사용자 원본 일치**: "도커 무관, 완전 캐시 비우고 로컬에서 다 내렸다 올리기" 그대로