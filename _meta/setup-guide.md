---
title: Raven Setup Guide — Clean Install & Uninstall
created: 2026-07-01
updated: 2026-07-01
type: howto
tags: [setup, install, uninstall, admin]
confidence: high
---

# Raven Setup Guide — Clean Install & Uninstall

> **BLUF**: 이 문서는 Raven 시스템을 다른 PC에 이전하거나 기존 환경을 초기화하고 싶을 때 안전하고 완벽하게 초기 구동 상태로 되돌리는 클린 설치(Clean Install) 및 잔여 설정을 모두 정리하는 클린 언인스톨(Clean Uninstall) 절차를 안내합니다.

---

## 1. 클린 설치 (Clean Install)

기존의 꼬인 의존성이나 캐시를 모두 제거하고 완전히 깨끗한 상태에서 Raven 스택을 구동합니다.

### 1-1. Docker 기반 (공식 권장)

Docker를 사용하여 OS에 구애받지 않고 일괄 실행 환경을 초기 셋업합니다.

```bash
# 1. 기존 컨테이너 및 볼륨, 로컬 이미지 완전 제거
docker compose down -v --rmi local

# 2. 환경 변수 초기화 (.env 파일이 없다면 복사)
cp .env.example .env

# 3. .env 내 RAVEN_VAULTS_DIR 경로가 유효한지 확인 (기본값: ~/Raven)
# 필요시 vi .env 등으로 편집

# 4. Git SHA를 빌드 아규먼트로 전달하여 클린 빌드 및 기동
make rebuild
```

### 1-2. 로컬 호스트 (venv + Node.js) 기반

로컬 호스트에 직접 파이썬 가상환경과 Node 의존성을 셋업하는 절차입니다.

```bash
# 1. 기존 빌드 및 가상환경, Node 모듈 강제 초기화
make nuke
cd dashboard && rm -rf node_modules dist && cd ..

# 2. Python 가상환경 재구축 및 의존성 설치
make install

# 3. Dashboard Node 의존성 설치 및 정적 빌드
cd dashboard
npm install
npm run build
cd ..

# 4. 초기 데이터베이스 빌드 및 정적 JSON export 실행
source scripts/.venv/bin/activate
python scripts/build_db.py
python scripts/export_static.py
```

---

## 2. 클린 언인스톨 (Clean Uninstall)

Raven 시스템 및 백그라운드 등록 프로세스를 OS 환경에서 잔여물 없이 완전히 격리 및 삭제합니다.

> [!WARNING]
> **주의 (데이터 보존)**: 언인스톨을 진행하더라도 사용자의 지식이 담긴 실제 마크다운 Vault 데이터(`~/Raven` 혹은 별도 지정 경로)는 기본적으로 **삭제되지 않고 보존**됩니다. 문서 데이터까지 완전히 날려야 하는 경우 별도로 수동 삭제하셔야 합니다.

### 2-1. Docker 스택 삭제

Docker로 생성된 모든 리소스를 청소합니다.

```bash
# 컨테이너 정지, 볼륨 삭제, 연관 네트워크 및 생성 이미지 일괄 삭제
docker compose down -v --rmi all
```

### 2-2. macOS 로컬 흔적 제거 (LaunchAgent 포함)

macOS 호스트 세팅 시 상주하도록 등록한 LaunchAgent와 흔적을 제거합니다.

```bash
# 1. LaunchAgent 서비스 언로드 및 plist 파일 삭제
launchctl unload ~/Library/LaunchAgents/com.wiki.dashboard.plist 2>/dev/null || true
rm -f ~/Library/LaunchAgents/com.wiki.dashboard.plist

# 2. 로컬 가상환경 및 빌드 산출물 삭제
rm -rf scripts/.venv
rm -rf dashboard/node_modules dashboard/dist
rm -rf tmp/

# 3. (선택) 보관소 메타 인덱스(SQLite DB) 및 백업 지우기
# 각 vault 디렉토리(예: ~/Raven/personal/) 내부의 wiki.db 및 backups/ 디렉토리
find ~/Raven -name "wiki.db" -delete
find ~/Raven -type d -name "backups" -exec rm -rf {} +
```

### 2-3. Linux 로컬 흔적 제거 (systemd 포함)

Linux 호스트 세팅 시 상주하도록 등록한 systemd 서비스와 흔적을 제거합니다.

```bash
# 1. systemd 서비스 중지 및 비활성화
sudo systemctl stop wiki-dashboard 2>/dev/null || true
sudo systemctl disable wiki-dashboard 2>/dev/null || true

# 2. systemd 설정 파일 및 daemon 리로드
sudo rm -f /etc/systemd/system/wiki-dashboard.service
sudo systemctl daemon-reload

# 3. 로컬 가상환경 및 의존성 삭제
rm -rf scripts/.venv
rm -rf dashboard/node_modules dashboard/dist
rm -rf tmp/
```

---

## 3. 문제 해결 및 팁 (Troubleshooting)

### 3-1. 포트 충돌 발생 시
기본 포트(`8765`, `8766`, `5173`)가 다른 프로세스에 의해 이미 점유되어 있을 경우, 서비스 기동이 실패합니다.
* **조치**: `.env` 파일 내의 `PORT_API`, `PORT_MCP_HTTP`, `PORT_DASHBOARD` 값을 충돌하지 않는 임의의 포트(예: 18765 등)로 수정한 뒤, Docker compose 혹은 로컬 서버를 다시 시작합니다.

### 3-2. "Lite bootstrap failed" 경고가 뜰 때
새로운 보관소(`raven vault create`)를 만들 때 규약 템플릿(SCHEMA.md 등) 복사가 실패하는 현상입니다.
* **원인**: Docker 환경에서 코드가 수정되었음에도 이전 Docker 이미지 레이어가 캐시되어 예전 버전의 템플릿 탐색 로직이 박혀 있는 경우 발생합니다.
* **조치**: `make rebuild` 또는 `docker compose build --no-cache --build-arg GIT_SHA=$(git rev-parse --short HEAD)` 명령을 통해 캐시를 완전히 무시하고 다시 빌드하십시오.
