---
title: Changelog v0.7.175
created: 2026-07-23
type: rule
tags: [desktop, tauri, python-core]
---

# v0.7.175 — Desktop Runtime + Dashboard ↔ Core 연결

## BLUF

Raven Dashboard를 macOS Tauri 창으로 기동하고, 그 수명주기에 맞춰 loopback 전용 Python Core(실제 Raven API)를 시작·종료하며, Dashboard가 random port Core endpoint에 자동 연결되는 desktop runtime을 구현했습니다.

## 변경

| 영역 | 변경 | 효과 |
|---|---|---|
| Tauri shell | `desktop/src-tauri/` 프로젝트 + `core_endpoint` command | Dashboard를 독립 desktop window로 실행, webview에 Core URL 주입 |
| Python Core | `raven.desktop.runtime` → 실제 Raven API (uvicorn, random port) | `/health` stub → `/api/vaults` 등 전체 API 제공 |
| Dashboard 연결 | `api-base.ts` fetch/sendBeacon intercept + `main.tsx` Tauri invoke | 기존 30개 fetch 호출 무변경, Tauri 모드에서 Core endpoint 자동 prepend |
| CORS | `RAVEN_EXTRA_CORS_ORIGIN` env → `server.py` allow_origins 확장 | `http://tauri.localhost` origin 허용 |
| lifecycle | Tauri가 readiness JSON을 읽고 종료 시 child process 정리 | 고정 포트·고아 프로세스 없이 수명주기 확인 |
| 안전 경계 | Core는 loopback만 bind, vault 읽기/쓰기 없음 | 외부 노출·데이터 변경 없이 runtime 통로만 검증 |

## 비목표

- Python runtime의 앱 번들링·서명·notarization
- MCP 원격 노출 또는 외부 접근

## 검증

- `pytest tests/test_desktop_runtime.py -q` → 1 passed (실제 API 응답 확인)
- `cargo test --lib` 및 `cargo check` → passed
- `npm run desktop:dev` → Tauri window + Core `http://127.0.0.1:56413` 기동 확인
- `curl -H 'Origin: http://tauri.localhost'` → 200 + `access-control-allow-origin` 헤더 확인
- parent 종료 시 Core port/process 정리 확인
- `npm run desktop:build` → release binary 빌드 성공
- Dashboard Vitest → 162 passed, 1 skipped

## 전체 Suite에서 관찰된 실패

전체 Python suite는 agent curation·Lite bootstrap contract 테스트 14건이 실패했습니다. 이번 작업의 직접 변경 경로와 겹치지 않지만, 별도 triage가 필요합니다.

## 2026-07-27 Mobile App Implementation (CMP)

모바일 앱 ADR(`adr-2026-07-27-cmp-mobile-app.md`) 요구사항에 따라 Compose Multiplatform 환경에 아래 사항들을 모두 구현하고 테스트를 완료했습니다.

- **데이터 레이어**: SQLDelight를 이용한 `Settings` 테이블(인증키 보관) 및 `DocumentRepository` 오프라인 퍼스트 Ktor 연동 완비.
- **보안/페어링**: QR 코드 스캐너 공통 인터페이스(`QrScanner`) 및 `PairingViewModel` 구현 (테스트 완료).
- **UI/UX**: `MainViewModel` 및 실제 도메인 객체와 바인딩된 `SlidingPanelLayout` 적용 완료.
- **패키지 명 변경**: Android, iOS 공통으로 패키지/번들 ID를 `com.ppizil.raven`으로 일괄 변경하고 `androidUnitTest` 등 19개 테스크 빌드 정상 동작 확인 완료.

## 2026-07-28 Mobile App Connection & UX Improvements

- **UX 개선 (Connection Status):** 모바일 앱(`MainViewModel`, `App.kt`)에서 연결 상태(로딩, 성공, 실패)를 시각적으로 명확히 분리하고, 네트워크 예외 발생 시 더 이상 조용히 실패하지 않고 명시적인 에러 메시지를 표시하도록 개선했습니다.
- **스마트 포매팅 (Smart Endpoint):** 사용자가 IP만 입력(`100.x.x.x`)해도 자동으로 `http://`와 `:8765` 포트를 붙여주는 자동 완성 로직을 `PairingViewModel`에 추가했습니다.
- **버그 픽스 (URL Trailing Slash):** `DocumentRepositoryImpl`에서 엔드포인트 URL 조합 시 끝에 슬래시(`/`)가 붙어 `//api/...` 형태로 잘못된 요청이 전송되는 현상을 방지했습니다.
- **아이콘 리소스 적용 (Cute Raven):** 새로운 캐주얼 까마귀 아이콘 디자인을 생성하여 macOS 데스크톱(`desktop/src-tauri/icons/`) 및 안드로이드(`mipmap-*`) 환경에 맞게 리사이징 및 적용을 완료했습니다 (중복된 구형 `.webp` 및 `.xml` 에러 유발 파일 싹 정리).
- **배포 (1.0.0-dev12):** `make deploy-dev` (Fastlane)를 통해 1.0.0-dev12 빌드를 Firebase App Distribution에 성공적으로 배포했습니다.

## 2026-07-28 Multi-Host Vault Repository & Desktop Register Support

- **Multi-Host Thin Client (`dashboard/src/lib/api-base.ts` & `api.ts`):** `getActiveTargetBaseUrl()`을 통한 동적 API Dispatcher를 도입하여, 사용자가 로컬 또는 원격 IP/URL 호스트를 선택하는 즉시 대시보드 전체의 `/api/...` 통신 대상 서버가 해당 호스트의 `~/Raven/` 지식 루트로 스위칭되도록 구현했습니다.
- **Host Switcher UI (`dashboard/src/components/HostPicker.tsx`):** 사이드바 상단에 호스트 선택 드롭다운 및 연결 추가/삭제 모달을 구현했습니다. 연결 전 `GET /api/vaults` 핑(Ping) 테스트로 원격 보관소 존재 및 헬스체크를 수행합니다.
- **기존 폴더 등록 API (`POST /api/vaults/register`):** 기존 폴더를 보관소로 손쉽게 등록하는 API 엔드포인트를 백엔드(`raven/api/server.py`)에 추가하고 대시보드 마법사(`NewVaultWizard.tsx`)에 "기존 폴더 등록" 탭을 추가했습니다.
- **CORS 설정 보강 (`raven/api/server.py`):** `RAVEN_ALLOW_ALL_CORS=1` 및 `RAVEN_EXTRA_CORS_ORIGIN="*"` 지원으로 외부 네트워크/원격 IP 기반 대시보드 연동 시 CORS 차단을 원천 방지하도록 개선했습니다.

## 2026-07-28 Remote Host Connection Fix, CORS Bugfix & Manual Update UI

- **Tauri macOS ATS(App Transport Security) 설정 추가 (`desktop/src-tauri/tauri.conf.json` & `desktop/src-tauri/Info.plist`):** Tauri 데스크톱 앱 내 웹뷰에서 원격 HTTP 주소(예: 100.121.237.40와 같은 Tailscale IP)로 HTTP fetch 요청을 보낼 때 macOS ATS에 의해 통신이 차단되는 문제를 해결하기 위해 `desktop/src-tauri/Info.plist`를 새로 생성하여 `NSAllowsArbitraryLoads: true` 설정을 주입하고 `tauri.conf.json`에서 이를 참조하도록 수정했습니다.
- **Tauri 빌드 아이콘 포맷 수정 (`desktop/src-tauri/icons/`):** 최근 캐주얼 까마귀 아이콘 반영 시 RGBA 알파 채널이 누락되어 Tauri 빌드가 실패하던 버그를 수정하기 위해, macOS Native API를 사용한 Swift 변환 도구(`tmp/convert.swift`)를 작성하여 `32x32.png`, `128x128.png`, `128x128@2x.png`, `icon.png` 파일들을 해상도 유실 없이 8-bit RGBA 포맷으로 일괄 교정 및 변환했습니다.
- **FastAPI CORS Tauri Origin 추가 (`raven/api/server.py`):** Tauri 데스크톱 앱의 custom protocol인 `tauri://localhost`, `https://tauri.localhost`, `http://tauri.localhost`에서 발생하는 원격 API 요청이 CORS(Cross-Origin Resource Sharing)에 의해 차단되지 않도록 `_cors_origins`에 해당 origin들을 기본 허용 목록으로 추가했습니다.
- **원격 호스트 상태 표시 UX 개선 (`dashboard/src/components/HostPicker.tsx`):** 사이드바의 호스트 선택기 영역에 현재 활성화된 호스트의 연결 상태를 비동기식으로 실시간 헬스체크하여 🟢(정상 연결됨), 🔴(연결 실패), 🟡(연결 확인 중...) 또는 💻(로컬 호스트) 상태를 나타내는 상태 표시등과 에러 메시지를 제공하도록 시각적 UX를 개선했습니다.
- **수동 업데이트 확인 & 설정 UI 구현 (`dashboard/src/routes/VaultManage.tsx` & `desktop/src-tauri/src/lib.rs`):** 데스크톱 앱(Tauri) 환경에서 수동으로 업데이트를 체크하거나 확인할 수 있는 경로가 마땅히 제공되지 않던 문제를 해결하기 위해, "관리" 탭 페이지 하단에 "데스크톱 앱 정보 및 업데이트" 전용 섹션을 추가했습니다. Rust 단에 `app_version` Tauri command를 노출하여 현재 실행 중인 실제 빌드 버전을 동적으로 쿼리하여 표시하고, 사용자가 수동으로 신규 업데이트를 체크하여 설치 및 재실행을 트리거할 수 있는 버튼을 제공합니다.
- **환경 의존적 데이터 하드코딩 금지 규칙 추가 (`_meta/RULES.md` & `AGENTS.md`):** Raven이 macOS/Linux 크로스 플랫폼 및 Tailscale VPN 연동 환경을 기본으로 함을 명문화하고, 개인 환경 경로(사용자명 포함 절대 경로), 고정 IP, API 키 등의 정보를 하드코딩하는 것을 엄격히 제한하는 지침을 추가했습니다.
