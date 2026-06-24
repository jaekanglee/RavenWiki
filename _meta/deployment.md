---
title: Deployment — VPS + Tailscale
created: 2026-06-25
updated: 2026-06-25
type: rule
tags: [system, meta, deployment, docker, tailscale]
---

# Deployment — VPS + Tailscale

> **한 줄 요약**: Hetzner CAX11 + Ubuntu 24.04 + Docker Compose + Caddy + Tailscale — git push 한 번으로 배포 끝

---

## VPS 사양

- **OS**: Ubuntu 24.04 LTS
- **사양**: 2 vCPU / 4GB RAM / 40GB SSD (ARM)
- **위치**: 일본 (Hetzner EU만 가능 → Vultr Tokyo 또는 Sakura Cloud 검토)
- **월 비용**: ~$5 (Hetzner CAX11) ~ $10 (Vultr)

> **D3 결정**: 일본 권장 (한국 사용자 ~50ms). 1차 Hetzner 검토했으나 일본 리전 없어 Vultr Tokyo 우선.

---

## 서비스 구성 (docker-compose.yml)

```yaml
# ~/wiki/docker-compose.yml
version: '3.8'

services:
  dashboard:
    build: ./dashboard
    restart: always
    ports:
      - "127.0.0.1:5173:5173"  # Tailscale만 접근 가능

  mcp:
    build: ./mcp
    restart: always
    ports:
      - "127.0.0.1:8765:8765"  # Tailscale만 접근 가능

  caddy:
    image: caddy:2
    restart: always
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile
      - caddy_data:/data
    ports:
      - "80:80"
      - "443:443"
    depends_on:
      - dashboard
      - mcp

volumes:
  caddy_data:
```

> **핵심 보안**: `127.0.0.1` 바인딩 → VPS 외부에서는 접근 불가. Tailscale interface(100.x) 통해서만 접근.

---

## Caddyfile

```
wiki.jakelee.dev {           # 자체 도메인 사용 시
    reverse_proxy dashboard:5173
}
mcp.jakelee.dev {            # MCP endpoint (Tailscale only)
    reverse_proxy mcp:8765
}
```

> **D6 결정**: 1차는 Tailscale MagicDNS (`wiki-vps.tailXXXX.ts.net`). 자체 도메인은 위 Caddyfile 그대로 사용 가능.

---

## Tailscale 설정

```bash
# VPS에 Tailscale 설치
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
# MagicDNS 자동 활성화 → wiki-vps.tailXXXX.ts.net

# ACL (Tailscale admin console):
# group:self → 100.x.y.z:5173, 8765 허용
```

**클라이언트**: macOS/Windows/iOS/Android [Tailscale 앱](https://tailscale.com/download) 설치 → 동일 계정 로그인

> **D5 결정**: Tailscale only (1차). Authentik 같은 추가 인증은 사용자 ≥ 3명일 때 도입.

**자세한 mesh 구조**: [[content/tailscale-mesh]]

---

## GitHub Webhook 배포

```bash
# ~/wiki/scripts/deploy.sh
#!/bin/bash
set -e
cd ~/wiki

echo "[deploy] git pull"
git pull origin main

echo "[deploy] rebuild wiki.db"
cd scripts
source .venv/bin/activate
python3 build_db.py
cd ..

echo "[deploy] restart services"
docker compose restart

echo "[deploy] healthcheck"
sleep 5
curl -sf http://localhost:5173/healthz || exit 1
echo "[deploy] OK"
```

```bash
# webhook endpoint: ~/wiki-webhook.py
# GitHub → POST /webhook → deploy.sh 실행
# (M4에서 simple HTTP 서버 구현)
```

---

## systemd 백업 (cron + timer)

```ini
# /etc/systemd/system/wiki-deploy.service
[Service]
Type=oneshot
ExecStart=/home/jakelee/wiki/scripts/deploy.sh
User=jakelee
WorkingDirectory=/home/jakelee/wiki
```

```ini
# /etc/systemd/system/wiki-deploy.path
[Path]
PathExists=/tmp/wiki-deploy-trigger
```

> 단순 cron 대안: `0 * * * * /home/jakelee/wiki/scripts/deploy.sh` (시간당 1회 pull)

---

## 배포 순서 (M4 작업)

1. **VPS 세팅** — Ubuntu 24.04 새로 설치 / ssh key 등록 / `sudo apt update && upgrade -y`
2. **Tailscale 설치** — `curl -fsSL https://tailscale.com/install.sh | sh && sudo tailscale up`
3. **Docker 설치** — `curl -fsSL https://get.docker.com | sh && sudo usermod -aG docker jakelee`
4. **vault clone** — `git clone https://github.com/jakelee/wiki.git ~/wiki` → `cd scripts && python3 -m venv .venv && pip install -e .`
5. **서비스 기동** — `cd ~/wiki && docker compose up -d` / Caddy 자동 TLS 발급 (자체 도메인 사용 시)
6. **검증** — 폰에서 Tailscale 앱 켜고 `http://wiki-vps.tailXXXX.ts.net:5173` 접근 / `curl http://wiki-vps.tailXXXX.ts.net:8765/tools`

---

## 모니터링 (간단)

```bash
# health check endpoint (dashboard 또는 caddy에 추가)
GET /healthz → 200 OK + wiki.db mtime

# cron (5분마다 외부 watch)
*/5 * * * * curl -sf http://wiki-vps/healthz || notify-telegram "wiki down"
```

**M6에서 Prometheus/Grafana 검토** (지금은 과함).

---

## 비용 (월)

| 항목 | 비용 |
|---|---|
| VPS (Vultr Tokyo 2vCPU/4GB) | ~$10 |
| Tailscale / GitHub / MagicDNS | $0 |
| 자체 도메인 (선택) | $10/년 |
| **합계** | **~$10/월** |

vs Obsidian Sync ($8/월) + Sync Pro ($10/월) → 1년에 $60-120 절약.

---

## 관련

- [[_meta/architecture-5layer]] (Layer 4) / [[_meta/dr-runbook]] (S1: VPS 손상) / [[_meta/decisions-d1-d6]] (D3/D5/D6)
- [[content/tailscale-mesh]] / [[content/mcp-server]]
