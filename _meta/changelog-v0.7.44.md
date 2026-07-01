# raven v0.7.44 — 다른 PC로의 세팅 이식성 개선 및 설정 버그 수정

> **핵심**: Raven 레포지토리를 다른 PC로 복사하여 세팅할 때 발생하던 로컬 호스트 의존성 빌드(`make install`) 및 시스템 설치 스크립트(`_meta/install.sh`)의 경로 오류를 수정하여 환경 이식성을 크게 향상시켰으며, 환경 이전과 초기화를 돕는 클린 설치/언인스톨 가이드를 작성했습니다.

릴리스 일자: 2026-07-01
이전: v0.7.43

---

## 1. 배경 및 기획

* **로컬 호스트 개발 환경 세팅 오류 수정**:
  * **상황**: `make install` 명령을 실행해 로컬 가상환경(`venv`) 및 의존성을 구성하려 할 때, 루트 디렉토리에 `pyproject.toml`이나 `setup.py`가 존재하지 않아 빌드 및 editable install(`pip install -e .`)이 실패했습니다.
  * **원인**: 의존성 정의 파일(`pyproject.toml`)이 루트가 아닌 `scripts/` 디렉토리에 있었기 때문입니다.
  * **해결 방안**: `Makefile`에서 `pip install -e .` 대신 `pip install -e ./scripts`를 호출하도록 경로를 올바르게 명시했습니다.
* **PEP 508 버전 표기법 오류 수정**:
  * **상황**: `make install` 실행 중 `scripts/pyproject.toml` 내의 `mcp[cli]>=1.x` 표기가 PEP 508 규격에 맞지 않아 패키지 검증 단계에서 에러를 유발했습니다.
  * **해결 방안**: 버전 요구사항을 PEP 508 규격에 맞는 `mcp[cli]>=1.0` 형태로 변경했습니다.
* **시스템 설치 스크립트 경로 버그 수정**:
  * **상황**: macOS/Linux 시스템 세팅을 수행하는 `_meta/install.sh` 실행 시, OSTYPE에 따른 플랫폼별 설치 스크립트를 찾지 못해 구동 도중 중단되는 오류가 있었습니다.
  * **원인**: `$SCRIPT_DIR/install/macos.sh` 형태로 불러오고 있었으나, 실제 `install` 폴더는 `_meta/` 내부가 아니라 프로젝트 루트에 위치하고 있어 경로가 불일치했습니다.
  * **해결 방안**: 소싱 경로를 `$SCRIPT_DIR/../install/...`로 변경하여 프로젝트 루트의 `install` 디렉토리를 정상적으로 가리키도록 수정했습니다.
* **클린 설치 & 언인스톨 문서 가이드 추가**:
  * **기획 배경**: 세팅 이전 작업을 보다 안전하고 반복 가능하게 수행할 수 있도록, 기존 환경을 말끔히 정리하는 Clean Install/Uninstall 명령어 및 macOS LaunchAgent/Linux systemd 완전 제거 흐름을 가이드로 제공하고자 문서화를 도입했습니다.

---

## 2. 변경 사항

### 2-1. `Makefile` 로컬 인스톨 경로 수정 ([Makefile](file:///Users/jaekanglee/Desktop/Dev/Project/Raven/Makefile#L29))
* `make install` 타겟의 `pip install -e .` 구문을 `pip install -e ./scripts` 로 변경하여 `pyproject.toml`이 위치한 실제 디렉토리를 참조하게 했습니다.

### 2-2. `pyproject.toml` 의존성 규격 수정 ([scripts/pyproject.toml](file:///Users/jaekanglee/Desktop/Dev/Project/Raven/scripts/pyproject.toml#L8))
* PEP 508 규격을 맞추기 위해 `mcp[cli]>=1.x` 를 `mcp[cli]>=1.0` 으로 변경했습니다.

### 2-3. 설치 스크립트 소스 경로 수정 ([_meta/install.sh](file:///Users/jaekanglee/Desktop/Dev/Project/Raven/_meta/install.sh#L35-L37))
* `_meta/install.sh` 에서 `install/macos.sh` 및 `install/linux.sh` 를 로드할 때 상위 디렉토리를 참조하도록 `../` 경로를 보완하였습니다.

### 2-4. 클린 셋업/제거 가이드 문서 작성 ([_meta/setup-guide.md](file:///Users/jaekanglee/Desktop/Dev/Project/Raven/_meta/setup-guide.md))
* Docker Compose 볼륨/이미지 정리 명령어 및 OS별 상주 서비스(LaunchAgent, systemd) 해제 절차, 포트 충돌 및 bootstrap 캐시 문제 대처법을 수록한 통합 매뉴얼을 구축했습니다.

---

## 3. 검증 결과

| 항목 | 결과 | 비고 |
|---|---|---|
| 로컬 인스톨 테스트 (`make install`) | **Success** | `scripts/.venv` 가상환경 구성 및 패키지 설치 완료 |
| 백엔드 테스트 (`make test`) | **490 passed, 1 skipped** | 전체 회귀 테스트 통과 확인 |

---

## 4. 다음 단계

* 다른 깨끗한 환경(Docker 컨테이너 내부 또는 신규 PC)에서 `_meta/install.sh` 및 `Makefile`이 완벽하게 초기 구동되는지 지속적인 피드백 확인 및 필요시 CLI 안내 문구 최적화.
