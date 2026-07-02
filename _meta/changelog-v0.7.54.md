# raven v0.7.54 — 워크스페이스(CWD) 연동 및 Git Status & Diff 대시보드 통합

> **핵심**: 볼트별로 로컬 소스코드/프로젝트 CWD(워크스페이스)를 연동하는 기능과, 연동된 워크스페이스의 Git 변경 사항(Status 및 Diff)을 대시보드와 CLI에서 실시간으로 확인하고 추적할 수 있는 기능을 추가했습니다.

릴리스 일자: 2026-07-02
이전: v0.7.53

---

## 1. 변경 사항

### 1-1. 볼트 메타데이터 확장 및 Registry 연동
* [raven/core/registry.py](file:///Users/jaekanglee/Desktop/Dev/Project/Raven/raven/core/registry.py)
  * `VaultMeta` 데이터 모델에 `workspace_path` 필드를 추가하고 직렬화/역직렬화를 지원하도록 확장했습니다.
  * `VaultRegistry`에 `update_workspace_path` 메소드를 추가하여 보관소별 워크스페이스 연동 정보를 `.registry.json`과 볼트 내부 `.vault.json`에 동시 업데이트하도록 구현했습니다.
* [raven/core/vault.py](file:///Users/jaekanglee/Desktop/Dev/Project/Raven/raven/core/vault.py)
  * `Vault.create` 메소드가 `workspace_path`를 인자로 받아 초기 생성 시점부터 연동되도록 지원했습니다.

### 1-2. CLI 워크스페이스 관리 명령어 추가
* [raven/cli/__main__.py](file:///Users/jaekanglee/Desktop/Dev/Project/Raven/raven/cli/__main__.py)
  * `vault create` 및 `vault register` 명령어가 `--workspace` (`-w`) 옵션을 지원하도록 확장했습니다.
  * 새 명령어 `raven vault workspace <name> [workspace_path] [--unlink]`를 도입하여 CLI 환경에서 특정 볼트의 워크스페이스 연동을 확인, 변경 또는 해제할 수 있도록 했습니다.

### 1-3. 로컬 호스트 통합 제어 스크립트 및 Makefile 단축 타겟 설정
* [raven.sh](file:///Users/jaekanglee/Desktop/Dev/Project/Raven/raven.sh)
  * 도커를 사용하지 않고 로컬 호스트 프로세스로 실행할 때, 백엔드 API 서버와 대시보드(Vite dev server)를 한 번에 올리고, 내리고, 재시작 및 상태 확인을 할 수 있는 통합 컨트롤 스크립트 `./raven.sh {start|stop|restart|status}`를 추가했습니다.
* [Makefile](file:///Users/jaekanglee/Desktop/Dev/Project/Raven/Makefile)
  * 로컬 환경 실행을 기본(First-class)으로 삼기 위해, 기존 도커 전용이었던 `make up`, `make down`, `make restart` 명령을 로컬 호스트 스택 제어(`raven.sh` 호출)로 전환했습니다.
  * `make status` 명령을 추가하여 로컬 스택 상태를 쉽게 확인할 수 있도록 개선했습니다.
  * 기존 도커 제어 명령은 `make docker-up`, `make docker-down`, `make docker-restart` 등으로 정돈했습니다.

### 1-4. FastAPI 백엔드 Git 연동 엔드포인트 추가
* [raven/api/server.py](file:///Users/jaekanglee/Desktop/Dev/Project/Raven/raven/api/server.py)
  * `GET /api/vaults/{name}` 및 `GET /api/vaults` 응답에 `workspace_path`를 노출하도록 수정했습니다.
  * `POST /api/vaults/{name}/workspace` 엔드포인트를 추가하여 대시보드 UI에서 워크스페이스 설정을 변경할 수 있게 했습니다.
  * `GET /api/vaults/{name}/git/status` 엔드포인트를 추가하여 연동 디렉토리의 Git 브랜치, 커밋 해시, 변경된 파일 리스트를 추적합니다.
  * `GET /api/vaults/{name}/git/diff` 엔드포인트를 추가하여 특정 소스 파일의 diff를 출력하며, 특히 추적되지 않은 파일(Untracked file)의 신규 추가 내용도 diff로 올바르게 표시합니다.

### 1-5. 대시보드(GUI) 워크스페이스 및 프리미엄 Diff 뷰어 구현
* [dashboard/src/types.ts](file:///Users/jaekanglee/Desktop/Dev/Project/Raven/dashboard/src/types.ts)
  * `VaultMeta` 타입에 `workspace_path` 필드를 연동했습니다.
* [dashboard/src/lib/api.ts](file:///Users/jaekanglee/Desktop/Dev/Project/Raven/dashboard/src/lib/api.ts)
  * `fetchGitStatus`, `fetchGitDiff`, `updateWorkspace` API 헬퍼 함수 및 인터페이스들을 추가했습니다.
* [dashboard/src/routes/WorkspacePage.tsx](file:///Users/jaekanglee/Desktop/Dev/Project/Raven/dashboard/src/routes/WorkspacePage.tsx)
  * 새로 설계된 워크스페이스 변경 사항 대시보드 컴포넌트입니다.
  * 연동된 CWD가 없는 경우 친근한 연동 가이드 및 연결 마법사를 표시합니다.
  * 연동 완료 시 Git Status 정보(브랜치, 커밋, 변경 파일 갯수) 및 Modified/Added/Deleted/Untracked 상태별 예쁜 배지를 제공합니다.
  * 파일 선택 시 변경 사항 라인을 컬러링(추가된 줄은 연두색, 삭제된 줄은 분홍색)하여 프리미엄한 Diff View 환경을 제공합니다.
* [dashboard/src/App.tsx](file:///Users/jaekanglee/Desktop/Dev/Project/Raven/dashboard/src/App.tsx)
  * `/workspace` 경로로 진입할 수 있도록 `WorkspacePage` 라우트를 등록했습니다.
* [dashboard/src/components/Layout.tsx](file:///Users/jaekanglee/Desktop/Dev/Project/Raven/dashboard/src/components/Layout.tsx)
  * 상단 네비게이션 탭 바에 "워크스페이스" (💻) 탭을 추가하여 쉽게 접근할 수 있도록 UI를 개선했습니다.

---

## 2. 검증 결과

### 2-1. 통합 테스트 작성 및 전체 테스트 검증
* [tests/test_vault_workspace.py](file:///Users/jaekanglee/Desktop/Dev/Project/Raven/tests/test_vault_workspace.py)
  * 새로운 테스트 세트를 작성하여 Registry 설정, CLI 명령어 동작, API 엔드포인트 무결성을 검증하고, 실제 임시 Git 저장소를 초기화하여 status 및 diff 데이터의 일관성을 검사했습니다.
  * 전체 테스트(546개) 패스 완료: `546 passed, 2 skipped`
* 프론트엔드 정적 타입 검사 통과: `npx tsc -b` 통과

---

## 3. 다음에 가능한 것 (후속 작업)
* **대시보드 내 Git Commit/Stage 기능**: 대시보드 내에서 변경 사항을 바로 스테이징하고 커밋 메시지를 작성해 반영할 수 있는 미니 Git UI 확장 검토.
