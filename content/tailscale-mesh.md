---
title: Tailscale Mesh VPN
created: 2026-06-25
updated: 2026-06-25
type: concept
tags: [concept, system, tailscale, security]
sources: [_meta/system-design.md]
confidence: high
---

# Tailscale Mesh VPN

## 정의

> [Tailscale](https://tailscale.com/) — WireGuard 기반의 **mesh VPN**. 장치들을 자동으로 안전하게 연결.
> 개인 사용 무료 (5명/100대 장치까지), MagicDNS + 내부 TLS + zero-config.

핵심: 전통적 hub-and-spoke VPN(중앙 서버 거치기)이 아니라 **P2P mesh** — 장치끼리 직접 연결.

## 일반 VPN과 차이

| 차원 | 일반 VPN (OpenVPN/WireGuard 서버) | Tailscale Mesh |
|---|---|---|
| **토폴로지** | hub-and-spoke (중앙 경유) | P2P mesh (장치끼리 직접) |
| **인증서/키** | 수동 발급/갱신 | 자동 (derp/control plane) |
| **MagicDNS** | 별도 설정 필요 | 자동 (장치명 = 호스트명) |
| **NAT traversal** | 포트포워딩 필요 | DERP relay로 자동 통과 |
| **공개 포트** | VPN 서버에 필요 (보안 위험) | **0개** (outbound only) |
| **TLS** | Let's Encrypt 수동 발급 | Tailscale 내부 TLS 자동 |
| **비용 (개인)** | VPS $5/월 + 인증서 | **$0** |

**결론**: Tailscale = **공개포트 0 + 인증서 0 + 도메인 0** = 보안 표면 최소화.

## MagicDNS

Tailscale 네트워크 안에서 장치명을 자동으로 IP로 resolve:

```
wiki-vps       → 100.x.y.z       (VPS)
jake-macbook   → 100.x.y.z       (내 노트북)
jake-iphone    → 100.x.y.z       (내 폰)
```

→ 별도 `/etc/hosts` 편집 ❌, 도메인 구매 ❌

## 우리 사용법 (VPS + 폰 + 로컬)

3개 노드만 있으면 충분 ([[_meta/system-design]] §2.4):

```
┌─ Tailscale MagicDNS ─────────────────────┐
│  wiki-vps      → 100.x.y.z              │
│  wiki-dashboard → 100.x.y.z:5173        │
│  wiki-mcp       → 100.x.y.z:8765        │
└─────────────────────────────────────────┘
         ↑                          ↑
    iPhone (Tailscale 앱)     Claude iOS / Codex
    → Safari/PWA              → MCP HTTPS
```

**접속 시나리오**:
1. **노트북에서**: `ssh wiki-vps` (Tailscale SSH)
2. **폰에서 wiki 읽기**: Safari → `http://wiki-vps:5173`
3. **Claude iOS**: MCP 설정 → server URL `http://wiki-vps:8765`

## 공개포트 0의 의미

우리 VPS의 방화벽:
- 인바운드: **모두 DROP** (Tailscale 인터페이스 제외)
- 아웃바운드: Tailscale control plane(443)만 허용

→ VPS가 해킹당해도 **Tailscale 네트워크 안의 장치만 접근 가능**
→ 해커가 Tailscale 장치를 얻으려면 내 폰/노트북을 동시에 해킹해야 함
→ [[_meta/system-design]] R1 리스크 완화

## DERP relay

직접 P2P 연결 실패 시(양쪽 NAT 등) Tailscale의 **DERP relay 서버**가 중계:
- 위치: 전 세계 30+ (한국 근처: 도쿄/싱가포르)
- 자동 선택 — 사용자는 모름
- 속도 손실: 직접 연결의 ~20%

**우리 케이스**: VPS는 퍼블릭 IP → DERP 거의 안 씀. 폰(모바일 NAT) → VPS는 직접 가능.

## 왜 Tailscale인가 (vs Cloudflare Tunnel / WireGuard 자체구축)

| 후보 | 장점 | 단점 | 결정 |
|---|---|---|---|
| **Tailscale** | 무료, zero-config, MagicDNS | control plane 의존 | ✅ 채택 |
| Cloudflare Tunnel | 무료, CDN | 도메인 필요, 계정 lock-in | ❌ |
| 자체 WireGuard | 완전 통제 | 설정/키 관리 직접 | ❌ (운영 부담) |
| Nebula (overlay) | 오픈소스 | 생태계 작음 | ❌ |

## 비용

- **Personal**: $0/월 (5명/100장치까지)
- **Team**: $6/월 (추가 SSO/audit)
- 우리 = Personal로 충분

## 한계 / 주의

- Control plane 장애 시 새 연결 불가 (기존 연결은 유지)
- Tailscale 회사 자체 신뢰 필요 (zero-knowledge E2EE 옵션은 유료)
- 우리 VPN 자체는 WireGuard지만 control plane SaaS에 의존

## 관련

- [[content/mcp-server]] — Tailscale 위에서 동작하는 MCP
- [[_meta/system-design]] — Layer 4 (Hosting) 설계
- [[SCHEMA]] — MCP 권한 + Tailscale 인증
- [[_meta/system-design]] — R1 리스크 (VPS 해킹) 완화
