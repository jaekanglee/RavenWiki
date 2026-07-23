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
