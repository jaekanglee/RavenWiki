# Raven Changelog — v0.7.177

## 1. 개요

- **작성일**: 2026-07-28
- **주요 내용**: Desktop Tauri 개발 모드(`debug_assertions`)에서 Python Core 인터프리터 감지 우선순위 개선 (개발 모드 시 stale한 번들 자원 대신 `scripts/.venv` 최우선 적용)

---

## 2. 주요 변경 사항

- **Desktop Tauri Python Core 탐지 로직 개선 (`desktop/src-tauri/src/core.rs`)**:
  - `cfg!(debug_assertions)` (개발 및 `cargo run` / `desktop-dev` 구동 시) 활성화 상태일 경우, `desktop/src-tauri/resources` 번들 파일 존재 여부와 무관하게 `scripts/.venv/bin/python`을 최우선으로 탐지하여 구동하도록 보강.
  - 이로 인해 개발자가 `make install` 수행 후 `make desktop-dev`를 구동할 때 오래되었거나 갱신되지 않은 번들 자원으로 인해 발생하는 `Python Core readiness` 파싱 에러(EOF while parsing) 완벽 방지.

---

## 3. 검증

- **Rust 유닛 테스트**: `desktop/src-tauri`에서 `cargo test` 실행 완료 (4 passed, 0 failed).
