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
