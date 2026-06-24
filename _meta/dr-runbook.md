---
title: 재해 복구 Runbook (DR)
created: 2026-06-25
updated: 2026-06-25
type: rule
tags: [system, meta, dr, backup]
---

# 재해 복구 Runbook (DR)

> **한 줄 요약**: 4가지 DR 시나리오 + 복구 명령어 (copy-paste 가능) + 분기 훈련 일정

---

## 개요

- **RPO (Recovery Point Objective)**: ≤ 1시간
- **RTO (Recovery Time Objective)**: ≤ 30분
- **3-2-1 백업 규칙**: 3개 사본 / 2개 매체 / 1개 오프사이트

## 백업 자산

| 대상 | 위치 | 주기 | 복구 시점 |
|---|---|---|---|
| vault markdown | git remote (GitHub) | 매 commit | 1시간 전 |
| vault local | Time Machine | 일 1회 | 1일 전 |
| VPS disk | VPS provider 스냅샷 | 주 1회 | 1주 전 |
| wiki.db | `wiki.db.backup` (일 1회 cron) | 일 1회 | DB만 (markdown에서 rebuild 가능) |

> wiki.db는 gitignore 대상 — markdown이 SoT이고 DB는 빌드 산출물이므로 git history에 없음. 단, lint/검색 빠른 복구를 위해 별도 cron 백업 권장.

---

## DR 시나리오

### S1. VPS 디스크 손상 (가장 빈번)

**예상 시간**: 30분

```bash
# 1. 새 VPS 생성 (Hetzner/Vultr, Ubuntu 24.04)
# 2. Tailscale 설치
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up

# 3. vault clone
git clone https://github.com/jakelee/wiki.git ~/wiki
cd ~/wiki

# 4. DB 재빌드
cd scripts
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
python3 build_db.py

# 5. 서비스 기동 (M4 배포 단계 완료 가정)
cd ..
docker compose up -d

# 6. 검증
curl -sf http://localhost:5173/healthz && echo "OK"
```

### S2. GitHub 장애 (rare)

**예상 시간**: 1시간

```bash
# 옵션 A: 로컬 백업에서 push
cd ~/wiki
git remote add backup-gitlab https://gitlab.com/jakelee/wiki.git
git push backup-gitlab main

# 옵션 B: GitHub 복구 대기 후 재push
```

> **사전 준비**: GitLab (또는 다른 provider)에 미러 remote를 두면 GitHub 장애 시 즉시 전환 가능. (W6 검토)

### S3. 로컬 + VPS 동시 손상 (worst case)

**예상 시간**: 10분

```bash
# GitHub만 살아있으면 됨
git clone https://github.com/jakelee/wiki.git ~/wiki
cd ~/wiki
python3 scripts/build_db.py
# 끝. 로컬에서 즉시 사용 가능.
```

### S4. vault 데이터 오염 (가장 흔함 — 사용자 실수)

**예상 시간**: 5분

```bash
# 1. 시점 파악
cd ~/wiki
git log --oneline -20

# 2. 잘못된 commit 식별 (예: abc1234)
# 옵션 A: revert (안전, history 보존)
git revert abc1234

# 옵션 B: hard reset (강력, history 손실)
git reset --hard HEAD~1   # 직전 commit이 문제면

# 3. wiki.db 재빌드 (오염된 frontmatter/링크가 DB에 들어갔을 수 있음)
python3 scripts/build_db.py

# 4. lint로 검증
python3 scripts/lint.py
```

> **팁**: `git revert`가 안전 — `git reset --hard`는 push 후엔 권장하지 않음 (다른 클론과 불일치).

---

## 복구 훈련 (분기 1회)

> 목표: RTO 30분 / RPO 1시간을 실제로 검증. 안 하면 못 함.

| 시점 | 시나리오 | 검증 항목 |
|---|---|---|
| 2026-09 | S1 시뮬레이션 | 새 VPS 만들어서 clone → dashboard 접근 |
| 2026-12 | S3 시뮬레이션 | GitHub만으로 복구 → lint 0 critical |
| 2027-03 | S4 시뮬레이션 | revert 실습 → wiki.db 재생성 |
| 2027-06 | S2 시뮬레이션 | GitHub 일시 차단 → GitLab mirror push |

---

## 마지막 복구 성공

- (없음 — 첫 분기 훈련 후 기록)

---

## wiki.db 백업 cron (M5 작업)

```bash
# scripts/backup_db.sh
#!/bin/bash
set -e
WIKI_DIR="$HOME/wiki"
DB="$WIKI_DIR/wiki.db"
BACKUP="$WIKI_DIR/wiki.db.backup"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)

# rotate (keep last 7)
if [ -f "$BACKUP" ]; then
  mv "$BACKUP" "$WIKI_DIR/wiki.db.backup.$TIMESTAMP"
fi
ls -t "$WIKI_DIR"/wiki.db.backup.* 2>/dev/null | tail -n +8 | xargs -r rm

# 새 백업
cp "$DB" "$BACKUP"
```

```ini
# ~/.config/systemd/user/wiki-backup.timer
[Unit]
Description=Daily wiki.db backup

[Timer]
OnCalendar=*-*-* 03:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

```ini
# ~/.config/systemd/user/wiki-backup.service
[Service]
ExecStart=/home/jakelee/wiki/scripts/backup_db.sh
```

---

## 관련

- [[SCHEMA]] — vault 규약
- [[RULES]] — 운영 정책 (백업 부분)
- [[_meta/architecture-5layer]] — 5-Layer (Layer 5: Backup)
- [[_meta/deployment]] — VPS 배포 절차 (S1 복구에 필요)
- [[_meta/decisions-d1-d6]] — D4 Git remote 결정
