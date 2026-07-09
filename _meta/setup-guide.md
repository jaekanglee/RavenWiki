---
title: Raven Setup Guide — Clean Install & Uninstall
created: 2026-07-01
updated: 2026-07-01
type: howto
tags: [setup, install, uninstall, admin]
confidence: high
---

# Raven Setup Guide — Clean Install & Uninstall

> **BLUF**: 다른 PC에서 Raven repo를 새로 클론한 뒤 **Docker 기준으로 바로 구동**하거나, 로컬 개발 환경을 **깨끗하게 재구성**하거나, 기존 로컬 산출물과 컨테이너를 **잔여물 없이 정리**할 때 이 문서를 따르십시오. 에이전트에게 넘길 때도 이 문서의 명령만 실행하면 되도록 현재 코드 기준으로 정렬했습니다.

---

## 1. 클린 설치 (Clean Install)

기존의 꼬인 의존성이나 캐시를 제거하고 Raven 스택을 깨끗한 상태에서 다시 올립니다.

### 1-0. 사전 조건

다른 PC에서 처음 세팅하는 경우 먼저 repo와 vault 경로를 준비합니다.

```bash
# 1. Raven repo clone
git clone <your-raven-repo-url>
cd Raven

# 2. 환경 파일 준비 (혼자 쓰는 개인/집 환경이면 house, 팀과 함께 쓰는 사내망이면 company)
cp .env.example.house .env
# cp .env.example.company .env   # 팀원과 함께 사내망에서 쓰는 경우

# 3. .env 확인
# - RAVEN_VAULTS_DIR: 다른 PC에서는 보통 ${HOME}/Raven 그대로 사용
# - PORT_API / PORT_MCP_HTTP / PORT_DASHBOARD: 필요시 충돌 없는 값으로 조정

# 4. vault 루트 준비 (없으면 생성)
mkdir -p "${HOME}/Raven"
```

### 1-1. Docker 기반 (공식 권장)

Docker를 사용하여 OS에 구애받지 않고 API/MCP/Dashboard를 함께 구동합니다. **현재 공식 권장 경로는 이것입니다.**

```bash
# 1. 기존 컨테이너 및 로컬 이미지 정리
docker compose down -v --rmi local

# 2. 클린 빌드 + 기동
make rebuild

# 3. 상태 확인
docker compose ps
curl http://127.0.0.1:${PORT_API:-8765}/api/vaults

# 4. 필요시 SHA 확인 (stale 이미지 검증)
docker exec raven-api cat /app/.git_sha
```

기동 후 표면:

- Dashboard: `http://localhost:5173`
- API: `http://localhost:8765/api/vaults`
- MCP HTTP: `http://localhost:8766/mcp`
- CLI: `docker compose exec api docker-entrypoint.sh cli <args>`

### 1-2. 로컬 호스트 (venv + Node.js) 기반

로컬 호스트에 직접 Python venv와 Node 의존성을 구성합니다. **Docker 미사용 개발/디버그용 보조 경로**입니다.

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

# 4. 테스트/CLI 스모크 체크
make test
scripts/.venv/bin/python -m raven.cli --help

# 5. 로컬 백그라운드 기동
make run-local

# 6. 상태 확인
curl http://127.0.0.1:8765/api/vaults
tail -f tmp/api.log tmp/dashboard.log
```

중지:

```bash
make stop-local
```

---

## 2. 클린 언인스톨 (Clean Uninstall)

Raven 시스템 및 백그라운드 등록 프로세스를 OS 환경에서 잔여물 없이 완전히 격리 및 삭제합니다.

> [!WARNING]
> **주의 (데이터 보존)**: 언인스톨을 진행하더라도 사용자의 지식이 담긴 실제 마크다운 Vault 데이터(`~/Raven` 혹은 별도 지정 경로)는 기본적으로 **삭제되지 않고 보존**됩니다. 문서 데이터까지 완전히 날려야 하는 경우 별도로 수동 삭제하셔야 합니다.

### 2-1. Docker 스택 삭제

Docker로 생성된 모든 리소스를 청소합니다.

```bash
# 컨테이너 정지, 로컬 볼륨/네트워크/이미지 정리
docker compose down -v --rmi all
```

### 2-2. 로컬 호스트 산출물 제거 (현재 표준)

현재 코드베이스 기준의 로컬 개발 산출물과 백그라운드 실행 흔적을 제거합니다.

```bash
# 1. 로컬 실행 중이면 중지
make stop-local 2>/dev/null || true

# 2. 로컬 가상환경 및 빌드 산출물 삭제
rm -rf scripts/.venv
rm -rf dashboard/node_modules dashboard/dist
rm -rf tmp/

# 3. (선택) 보관소 메타 인덱스(SQLite DB) 및 백업 지우기
# 각 vault 디렉토리(예: ~/Raven/personal/) 내부의 wiki.db 및 backups/ 디렉토리
find ~/Raven -name "wiki.db" -delete
find ~/Raven -type d -name "backups" -exec rm -rf {} +
```

### 2-3. 레거시 OS 서비스 흔적 제거 (예전 `wiki-*` service 템플릿 사용 시만)

현재 `_meta/install.sh`는 **Docker-first Raven 설치 래퍼**입니다. 아래 정리 절차는 그 이전에 `deploy/launchd/com.wiki.dashboard.plist`, `deploy/systemd/wiki-*.service` 같은 **예전 `wiki-*` service 템플릿**을 직접 사용했던 경우에만 필요합니다.

```bash
# macOS LaunchAgent 흔적 제거
launchctl unload ~/Library/LaunchAgents/com.wiki.dashboard.plist 2>/dev/null || true
rm -f ~/Library/LaunchAgents/com.wiki.dashboard.plist

# Linux systemd 서비스 중지 및 비활성화
sudo systemctl stop wiki-dashboard 2>/dev/null || true
sudo systemctl stop wiki-mcp 2>/dev/null || true
sudo systemctl disable wiki-dashboard 2>/dev/null || true
sudo systemctl disable wiki-mcp 2>/dev/null || true

# Linux systemd 설정 파일 제거 및 daemon 리로드
sudo rm -f /etc/systemd/system/wiki-dashboard.service
sudo rm -f /etc/systemd/system/wiki-mcp.service
sudo rm -f /etc/systemd/system/wiki-backup.service
sudo rm -f /etc/systemd/system/wiki-backup.timer
sudo systemctl daemon-reload
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

### 3-3. 에이전트에게 그대로 넘길 최소 절차

다른 PC의 에이전트에게는 아래만 전달해도 됩니다.

```bash
git clone <your-raven-repo-url>
cd Raven
cp .env.example.house .env
mkdir -p "${HOME}/Raven"
make rebuild
docker compose ps
curl http://127.0.0.1:8765/api/vaults
```

성공 기준:

- `docker compose ps` 에서 `api`, `mcp-http`, `dashboard` 가 `Up`
- `curl /api/vaults` 가 JSON 반환
- 브라우저에서 `http://localhost:5173` 접속 가능
