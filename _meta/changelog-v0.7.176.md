# Raven v0.7.176 — Tailscale/원격 IP CORS 허용 및 원격 연결/삭제 디버깅 개선

**날짜**: 2026-07-28  
**유형**: 버그 수정 및 Remote UI/API 디버깅 보강

---

## 1. 개요 및 배경

테일스케일(Tailscale) 또는 동일 사설망(LAN) 환경에서 다른 PC(`100.x.x.x` 또는 `192.168.x.x`)의 Raven API/Dashboard로 연결을 시도할 때, 백엔드의 CORS origin 제한 정책으로 인해 브라우저 단에서 요청이 차단(`TypeError: Failed to fetch`)되고, UI에서 원인을 알 수 없는 "Load failed" 혹은 연결 실패 상태에 빠지는 현상이 발생했습니다.
또한, 호스트가 오프라인 상태일 때 호스트를 삭제할 방법이 제한적이거나, Vault/API 삭제 실패 시 `[object Object]` 등 모호한 메시지로 표출되던 문제를 전면 개선했습니다.

---

## 2. 주요 변경 사항

### 2.1 백엔드 CORS regex 추가 (`raven/api/server.py`)
- `CORSMiddleware`에 `allow_origin_regex` 매개변수 도입.
- **허용 대역**:
  - 로컬 (`localhost`, `127.0.0.1`)
  - Tailscale 대역 (`100.64.0.0/10` → `100.\d{1,3}.\d{1,3}.\d{1,3}`)
  - 사설망 대역 (`192.168.x.x`, `10.x.x.x`, `172.16-31.x.x`)
- Tailscale IP(`100.121.237.40` 등)를 이용한 원격 웹 대시보드 API 통신이 기본적으로 CORS 정책에 의해 차단되지 않도록 보장했습니다.

### 2.2 삭제 및 유실 Vault 안전 등록 해제 (`raven/api/server.py`)
- `DELETE /api/vaults/{name}` API 호출 시, Vault 디렉토리가 미존재하거나 디스크 유실/접근 불가 상태(`Vault.load` 실패)인 경우에도 500 에러를 던지지 않고 안전하게 등록 해제(`registry().remove(name)`)가 수행되도록 예외 처리했습니다.

### 2.3 프론트엔드 에러 디버깅 메시지 및 삭제 기능 보강 (`dashboard/src/`)
- **`formatApiError` 헬퍼 도입 (`dashboard/src/lib/api.ts`)**:
  - 네트워크/CORS 에러 (`Failed to fetch`), FastAPI JSON detail 객체(`{ reason, hint, ... }`), HTTP 에러 등을 직관적이고 상세한 한글 디버깅 메시지로 정제.
- **호스트 관리 모달 내 개별 삭제 기능 (`dashboard/src/components/HostPicker.tsx`)**:
  - 오프라인 상태이거나 선택되지 않은 원격 호스트라도 모달 목록에서 삭제(🗑)할 수 있도록 "등록된 원격 호스트 목록" 섹션 및 삭제 버튼 배치.
- **Vault 삭제 에러 상세 표출 (`dashboard/src/routes/VaultManage.tsx`)**:
  - `deleteVault` 수행 시 발생한 오류 원인과 백엔드 힌트를 `formatApiError`로 화면에 명확하게 표출.

---

### 2.4 데스크톱 앱 부팅 경주 조건(Race Condition) 및 빈 화면(Blank Screen) 이슈 해결
- **Rust `core_endpoint` / `mcp_endpoint` async 전환 (`desktop/src-tauri/src/lib.rs`)**:
  - `lib.rs`의 `setup` 훅에서 Python Core 시작을 비동기 백그라운드 태스크로 구동함에 따라, 앱 기동 직후 웹뷰가 `core_endpoint` IPC 명령을 부르면 Python Core 준비 완료 전 `""`(빈 문자열)을 즉시 반환하여 프론트엔드가 loopback 백엔드 주소 대신 커스텀 프로토콜(`http://tauri.localhost/api/...`)로 API 요청을 보내 실패하고 빈 화면이 뜨던 경주 조건 해결.
  - Rust `core_endpoint` 및 `mcp_endpoint` 명령을 async 함수로 변환하고 Python Core 준비 완료 시점까지 대기(지연 루프 대기)하도록 보강.
- **프론트엔드 endpoint 획득 재시도 로직 보강 (`dashboard/src/main.tsx`)**:
  - `initDesktopEndpoint()` 비동기 재시도 루프(최대 30회, 6초 타임아웃)를 도입하여 데스크톱 실행 시 Python Core 주소(`http://127.0.0.1:port`)를 안정적으로 받아 렌더링되도록 보충.

---

### 2.5 데스크톱 필수 개발 환경 자동 설치/사전 점검 (`desktop-check`)
- **`Makefile` 내 `desktop-check` 자동 설치 기능 보강**:
  - `make desktop-dev` 및 `make desktop-build` 실행 시 Rust(`cargo`) 미설치 환경인 경우 `rustup`(`sh.rustup.rs`)을 통해 자동으로 비대화형(`-y`) 설치를 진행하도록 개선.
  - `PATH`에 `$(HOME)/.cargo/bin`을 자동 포함하여 설치 직후 터미널 재시작 없이도 `cargo` 명령어가 즉시 인식되도록 설정.
  - Node.js 미설치 환경이고 Homebrew가 존재할 경우 `brew install node`로 자동 설치 시도.
  - `dashboard/node_modules` 미존재 시 `npm install` 자동 수행 유지.

---

## 3. 검증

- **TypeScript 타입 체크 & 빌드**: `npm run build` (dashboard) 실행 완료 — pass.
- **Rust Tauri 유닛 테스트**: `cargo test` (desktop/src-tauri) 실행 완료 — 4 passed.
- **Python 코어 & API 테스트**: `pytest tests/ -q` 실행 완료 — 704 passed.

