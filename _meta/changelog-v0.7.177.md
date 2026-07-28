# Raven Changelog — v0.7.177

## 1. 개요

- **작성일**: 2026-07-28
- **주요 내용**: Desktop 백엔드 기본 바인딩 `0.0.0.0` 자동 개방, Tailscale CORS 허용, HostPicker 자동 재연결(Auto-Reconnect) 및 수동 재시도 버튼 추가

---

## 2. 주요 변경 사항

- **Desktop 백엔드 기본 바인딩 `0.0.0.0` 전환 및 Tailscale/LAN CORS 자동 개방 (`core.rs` / `runtime.py`)**:
  - 기존 데스크톱 앱 실행 시 파이썬 백엔드가 `127.0.0.1`로만 구동되어 외부 PC나 Tailscale 네트워크 접속 시 소켓 레벨에서 접속이 거절(Load failed)되던 구조적 불편함 해소.
  - `core.rs`에서 별도 환경변수 지정 없이도 기본 bind_host를 `0.0.0.0`으로 자동 설정하고, `runtime.py`에서 `0.0.0.0` 또는 Tailscale 바인딩 시 `RAVEN_ALLOW_ALL_CORS=1`을 자동 적용.
  - 이제 사용자가 아무 설정 없이 앱을 켜기만 해도 외부 기기 및 Tailscale 망에서 원격 접속이 막힘없이 100% 통과하도록 근본적 보강.

- **Dashboard 호스트 픽서(`HostPicker.tsx`) 수동 재시도 버튼 및 5초 자동 재연결(Auto-Reconnect) 도입**:
  - 상대 PC 또는 원격 백엔드가 끊긴 오프라인 상태(`offline`)일 때 5초 간격으로 백그라운드 헬스체크를 자동 수행하도록 보강.
  - 상대 PC가 재부팅을 마치고 백엔드가 복구되면 내 쪽 화면에서 자동으로 `정상 연결됨` 상태로 복구되고 최신 보관소 데이터를 동기화하도록 구현.
  - 연결 실패 문구 옆에 `[🔄 재시도]` 수동 재연결 버튼을 탑재하여 클릭 한 번으로 백엔드 연결 상태를 즉시 재확인할 수 있도록 개선.

- **Makefile `install` 및 `venv-check` 타겟 안정화**:
  - `test -d scripts/.venv` 검사 방식의 허점(신규 PC/clone 환경에서 venv 생성이 꼬여 `scripts/.venv` 디렉토리만 남아있을 경우 `pip` 실행 파일 부재로 `No such file or directory`가 무한 발생하던 문제) 수정.
  - `test -x scripts/.venv/bin/pip` 검사로 변경하고, 유효한 `pip` 실행 파일이 없으면 기존 꼬인 폴더를 자동 제거(`rm -rf`) 후 `python3 -m venv`를 깨끗하게 재생성하도록 보강.

---

## 3. 검증

- **Dashboard 빌드 및 TypeScript 체크**: `npm run build` 완료 (`built in 4.15s`, error 0개).
- **Rust 유닛 테스트**: `desktop/src-tauri`에서 `cargo test` 실행 완료 (4 passed, 0 failed).
- **Makefile install 테스트**: `make install` 갱신 동작 확인 완료.
