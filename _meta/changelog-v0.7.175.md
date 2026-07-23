---
title: Changelog v0.7.175
created: 2026-07-23
type: rule
tags: [desktop, tauri, python-core]
---

# v0.7.175 — Desktop Runtime Spike

## BLUF

Raven Dashboard를 macOS Tauri 창으로 기동하고, 그 수명주기에 맞춰 loopback 전용 Python Core를 시작·종료하는 최소 desktop runtime을 검증했습니다.

## 변경

| 영역 | 변경 | 효과 |
|---|---|---|
| Tauri shell | `desktop/src-tauri/` 프로젝트와 Dashboard dev/build 명령 추가 | Dashboard를 독립 desktop window로 실행 |
| Python Core | `raven.desktop.runtime` 추가 | `127.0.0.1` random port에서 `/health` readiness만 제공 |
| lifecycle | Tauri가 readiness JSON을 읽어 Core를 관리하고 종료 시 child process 정리 | 고정 포트·고아 프로세스 없이 수명주기 확인 |
| 안전 경계 | Core는 loopback만 bind하고 vault를 읽거나 수정하지 않음 | 외부 노출·데이터 변경 없이 runtime 통로만 검증 |

## 비목표

- Python runtime의 앱 번들링·서명·notarization
- Dashboard API를 random Core endpoint로 연결
- MCP 원격 노출 또는 외부 접근

## 검증

- `pytest tests/test_desktop_runtime.py -q` → 1 passed
- `cargo test --lib` 및 `cargo check` → passed
- `npm run desktop:dev` → Tauri window + Python Core readiness 확인
- Core `/health` 응답 확인 후 parent 종료 시 Core port/process 정리 확인
- `npm run desktop:build` → release binary 빌드 성공
- Dashboard Vitest → 162 passed, 1 skipped

## 전체 Suite에서 관찰된 실패

전체 Python suite는 agent curation·Lite bootstrap contract 테스트 14건이 실패했습니다. 이번 작업의 직접 변경 경로와 겹치지 않지만, 별도 triage가 필요합니다.
