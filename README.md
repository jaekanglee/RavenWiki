# Wiki System

> **Obsidian-free 개인/팀 위키.** markdown + git + 자체 뷰어.
> 한 줄 설치로 VPS에 띄우고, 외부에서는 Tailscale로 안전하게 접속.

---

## 빠른 시작 (이미 셋업된 로컬)

```bash
cd ~/Desktop/Dev/Project/Wiki

# 빌드 (vault → DB + 정적 export)
scripts/.venv/bin/python scripts/build_db.py
scripts/.venv/bin/python scripts/export_static.py

# dashboard dev 서버 (HMR)
cd dashboard && npm run dev
# → http://localhost:5173

# MCP server (stdio, 로컬 Hermes)
scripts/.venv/bin/python -m mcp.cli

# MCP server (HTTP, Tailscale 원격)
scripts/.venv/bin/python -m mcp.cli --transport http --host 127.0.0.1 --port 8765
```

---

## 처음 설치

### macOS (개발 머신)

```bash
# 1. Homebrew (https://brew.sh)

# 2. 의존성
brew install python@3.11 node git

# 3. Tailscale (외부 접근용, 선택)
brew install --cask tailscale

# 4. vault clone
git clone https://github.com/<user>/wiki.git ~/Desktop/Dev/Project/Wiki
cd ~/Desktop/Dev/Project/Wiki

# 5. Python venv + dashboard 의존성
python3 -m venv scripts/.venv
scripts/.venv/bin/pip install -e "scripts[dev]"
cd dashboard && npm install && npm run build && cd ..

# 6. 초기 빌드 + 백업
scripts/.venv/bin/python scripts/build_db.py
scripts/.venv/bin/python scripts/export_static.py
scripts/.venv/bin/python scripts/backup_db.py

# 7. (선택) LaunchAgent 등록 — 부팅 시 자동 시작
cp deploy/launchd/com.wiki.dashboard.plist ~/Library/LaunchAgents/
sed -i '' "s|{{VAULT}}|$PWD|g" ~/Library/LaunchAgents/com.wiki.dashboard.plist
launchctl load ~/Library/LaunchAgents/com.wiki.dashboard.plist

# 또는 통합 설치 스크립트 한 줄:
./install.sh
```

### Linux VPS (Hetzner / DO / AWS)

```bash
# ssh 접속 후
sudo apt update && sudo apt install -y git curl
git clone https://github.com/<user>/wiki.git ~/wiki
cd ~/wiki
./install.sh   # OS 자동 감지 (apt/dnf + systemd)
```

`install.sh`가 다음을 모두 수행:

1. 시스템 패키지 설치 (python3, nodejs, npm, git, curl)
2. Tailscale 설치 (선택)
3. Python venv 생성 + `pip install -e "scripts[dev]"`
4. Dashboard `npm install && npm run build`
5. `build_db.py` + `export_static.py` 실행
6. `backup_db.py` 초기 실행
7. systemd 서비스 등록 + enable (`wiki-dashboard`, `wiki-mcp`, `wiki-backup.timer`)

### Windows (WSL2)

WSL2 Ubuntu에서 Linux 절차를 그대로 따른다. LaunchAgent는 WSL에서 미지원이므로
수동으로 `nohup` 백그라운드 실행하거나 systemd 활성화 (`systemd-genie` 등).

---

## 일상 운영

```bash
# 콘텐츠 추가/수정 후
scripts/.venv/bin/python scripts/build_db.py
scripts/.venv/bin/python scripts/export_static.py

# lint 검사 (wikilink 무결성, frontmatter 검증)
scripts/.venv/bin/python scripts/lint.py

# 백업 (수동)
scripts/.venv/bin/python scripts/backup_db.py --keep 14

# 백업 상태 확인
ls -lh backups/

# 원격 VPS 배포 (로컬 → VPS push + VPS rebuild + restart)
VPS=user@100.x.x.x ./scripts/deploy.sh
```

### systemd 관리

```bash
sudo systemctl status wiki-dashboard    # 상태
sudo systemctl restart wiki-dashboard   # 재시작
sudo systemctl stop wiki-dashboard      # 중지
sudo journalctl -u wiki-dashboard -f    # 로그 follow
sudo journalctl -u wiki-mcp -n 100      # 최근 100줄

# 백업 timer 확인
systemctl list-timers wiki-backup.timer
sudo systemctl start wiki-backup.service   # 수동 실행 (테스트)
```

### macOS LaunchAgent 관리

```bash
launchctl list | grep com.wiki          # 등록 확인
launchctl unload ~/Library/LaunchAgents/com.wiki.dashboard.plist
launchctl load ~/Library/LaunchAgents/com.wiki.dashboard.plist
tail -f ~/Desktop/Dev/Project/Wiki/logs/dashboard.log
```

---

## 아키텍처 (5 Layer)

| # | Layer        | 무엇                          | 도구                              |
|---|--------------|------------------------------|----------------------------------|
| 1 | Data         | markdown + SQLite 인덱스      | `scripts/build_db.py`             |
| 2 | MCP          | AI 표준 인터페이스 (5 tools)   | `mcp/` (FastMCP)                  |
| 3 | Dashboard    | React 19 SPA                  | `dashboard/` (vite)              |
| 4 | Hosting      | VPS + Tailscale               | `deploy/` (systemd + launchd)    |
| 5 | Backup       | 일 1회 백업 + rotation        | `scripts/backup_db.py` + timer   |

자세한 내용: [`_meta/architecture-5layer`](_meta/architecture-5layer.md)

```
┌─────────────────────────────────────────────────────────────┐
│  Tailscale (WireGuard)                                      │
│    ↓ HTTPS                                                  │
│  Reverse Proxy (optional, e.g. Caddy)                       │
│    ↓                                                         │
│  ┌──────────────────┐  ┌──────────────────┐                 │
│  │ wiki-dashboard   │  │ wiki-mcp         │                 │
│  │ :5173 (vite)     │  │ :8765 (FastMCP)  │                 │
│  └──────────────────┘  └──────────────────┘                 │
│           ↑                      ↑                          │
│           └────── wiki.db ──────┘                          │
│                  ↑                                          │
│            scripts/.venv (Python)                          │
└─────────────────────────────────────────────────────────────┘
```

---

## 디렉토리

```
wiki/
├── SCHEMA.md, RULES.md, README.md   # 이 파일들
├── content/, _meta/, raw/           # vault (markdown, git-tracked)
├── scripts/                         # 빌드/검증/백업 (Python)
│   ├── build_db.py
│   ├── export_static.py
│   ├── lint.py
│   ├── backup_db.py                 # M5 신규
│   └── deploy.sh                    # M5 신규
├── mcp/                             # MCP server (FastMCP, stdio+http)
├── dashboard/                       # React 19 SPA (vite)
├── deploy/                          # 서비스 정의 (M5 신규)
│   ├── launchd/
│   │   └── com.wiki.dashboard.plist
│   └── systemd/
│       ├── wiki-dashboard.service
│       ├── wiki-mcp.service
│       ├── wiki-backup.service
│       └── wiki-backup.timer
├── install.sh                       # OS 자동 감지 설치 (M5 신규)
├── install/
│   ├── macos.sh
│   └── linux.sh
├── backups/                         # 일자별 백업 (gitignored)
├── logs/                            # 서비스 stdout/err (gitignored)
└── wiki.db                          # Query Index (gitignored, regenerable)
```

---

## 보안 / 노출 전략

- **로컬 개발**: `127.0.0.1:5173` (vite preview, dashboard), `127.0.0.1:8765` (mcp http)
- **외부 접근**: Tailscale (WireGuard) — 공개 포트 0개
  - `tailscale up` 후 `100.x.x.x:5173` / `100.x.x.x:8765` 으로만 접속
  - HTTPS reverse proxy (Caddy) 도 Tailscale 위에서만 노출
- **백업**: `backups/` 디렉토리는 git 제외, VPS에서 외부 스토리지(S3/B2) 동기화 권장

---

## 비용 (추정)

| 항목              | 비용           |
|------------------|---------------|
| VPS (Hetzner CX22) | $5/월        |
| Tailscale Personal | $0           |
| GitHub private    | $0            |
| 도메인 (선택)      | $12/년        |
| **합계**          | **~$5/월**    |

---

## 트러블슈팅

### `vite preview` 가 0.0.0.0 으로 바인딩돼 외부 노출됨

→ systemd unit의 `--host 127.0.0.1` 확인. 변경 시 `sudo systemctl daemon-reload && sudo systemctl restart wiki-dashboard`.

### LaunchAgent 가 부팅 후 안 올라옴

```bash
launchctl print gui/$(id -u)/com.wiki.dashboard  # 진단
log show --predicate 'process == "launchd"' --last 5m
```

`WorkingDirectory` 와 `StandardOutPath` 의 `{{VAULT}}` 치환 여부 확인.

### systemd timer 가 안 돎

```bash
systemctl list-timers wiki-backup.timer   # 다음 실행 시각
journalctl -u wiki-backup.service -n 50   # 최근 실행 로그
sudo systemctl start wiki-backup.service  # 수동 트리거 (테스트)
```

### `pip install -e "scripts[dev]"` 실패

→ Python 3.9+ 필요. `python3 --version` 확인. macOS brew python은 3.11+.

### 백업이 안 만들어짐

→ `wiki.db` 존재 확인 (`ls -lh wiki.db`). 없으면 `build_db.py` 먼저 실행.

---

## 라이센스

MIT (자율 사용, 상업적 이용 허용)

---

## 참고 문서

- [`SCHEMA.md`](SCHEMA.md) — frontmatter + wikilink 규약
- [`RULES.md`](RULES.md) — naming convention, layer 구분
- [`_meta/architecture-5layer`](_meta/architecture-5layer.md) — 5 Layer 상세
- [`dashboard/README.md`](dashboard/README.md) — React 앱 개발 가이드
- [`mcp/README.md`](mcp/README.md) — MCP tools 명세
- [`log.md`](log.md) — 마일스톤 히스토리
