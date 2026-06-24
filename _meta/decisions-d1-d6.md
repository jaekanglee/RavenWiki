---
title: 결정사항 (Decisions D1-D6)
created: 2026-06-25
updated: 2026-06-25
type: rule
tags: [system, meta, decisions]
sources: [raw/articles/karpathy-llm-wiki-2026.md]
confidence: high
---

# 결정사항 (Decisions D1-D6)

> **한 줄 요약**: D1-D6 아키텍처 결정 + M0-M6 마일스톤 + R1-R6 리스크 & 완화

> 원본: [[_meta/system-design]] (412줄) → 분리됨 (M1 W5). 백업: `/tmp/system-design-backup.md`.

---

## 결정 매트릭스

| # | 결정 | 권장 | 기각 |
|---|---|---|---|
| D1 | Frontend 프레임워크 | **Svelte 5** | React (무거움) / Astro (SSG 약함) / Elm (러닝커브) |
| D2 | MCP 구현 언어 | **Python (FastMCP)** | Node.js (헤르메스 통합 ↓) |
| D3 | VPS 위치 | **일본** | 한국 (provider 좁음) / 미국 (150ms+) |
| D4 | Git remote | **GitHub private** | Gitea (VPS 장애 시 같이 죽음) |
| D5 | 인증 방식 | **Tailscale only** | +Authentik (1인에 과함) |
| D6 | 도메인 사용 | **MagicDNS** | 자체 도메인 (비용+자동화 부담) |

---

## D1 — Frontend: Svelte 5

**근거**: ~10KB 번들 (vs React 45KB) / Obsidian-feel UI / 한국어 자료 / 1인 DX 충분

## D2 — MCP: Python (FastMCP)

**근거**: 헤르메스(wiki-orchestrator)와 동일 언어 / build_db.py/lint.py와 같은 venv / FastMCP는 Anthropic 공식 SDK

## D3 — VPS 위치: 일본 (Tokyo/Osaka)

**근거**: 한국→~50ms / Hetzner·Vultr 모두 리전 / 정치·법적 안정성 양호

> Hetzner는 EU만 가능 → Vultr Tokyo 또는 Sakura Cloud 검토

## D4 — Git Remote: GitHub private (1차)

**근거**: 1GB 무료 (현재 < 5MB) / HTTPS push / DR S3 자동 충족 / Gitea 이관 30분

## D5 — 인증: Tailscale only (1차)

**근거**: 5명 무료로 충분 / 공개포트 0개 / MagicDNS + TLS 자동 / Authentik은 사용자 ≥ 3명일 때

## D6 — 도메인: MagicDNS (1차)

**근거**: `wiki-vps.tailXXXX.ts.net` 자동 / TLS 자동 / 도메인 등록 $0 / Tailscale 회사 신뢰

---

## 리스크 & 완화

| # | 리스크 | 영향 | 완화 |
|---|---|---|---|
| R1 | VPS 해킹 | 데이터 유출 | 공개포트 0, Tailscale만, 2FA |
| R2 | VPS provider 장애 | 24h 다운 | GitHub에서 즉시 clone, 다른 provider |
| R3 | LLM이 평범한 요약만 생성 | wiki 품질 저하 | governance 규칙 ([[SCHEMA]]), lint로 자동 탐지 |
| R4 | vault 비대화 (1만 페이지+) | 검색/렌더 느려짐 | 페이지 분리 강제, 청크 인덱스 |
| R5 | 내가 휴가 → 자동화 작동 안 함 | wiki outdated | cron lint, wiki-curator 일 1회 |
| R6 | MCP API 변경 | 호환성 깨짐 | spec 안정화 후 구현, fallback |

---

## 마일스톤 (Phase별)

### M0 — 설계 ✅ (2026-06-24 완료)

- 5-layer 아키텍처 정의
- MVP PRD/페르소나/시나리오
- LLM Wiki 패턴 + 비판 정리
- 모델 프로필별 배분

### M1 — Data Layer ✅ (2026-06-25 완료)

- SCHEMA.md v2.4 고도화
- 26 페이지 작성 (15 content + 5 _meta + 6 root)
- wiki-architect가 RULES.md 작성
- `build_db.py` (SQLite v2.4 schema, FTS5) — TDD 16 통과
- `lint.py` (9 lint rules, read-only) — TDD 18 통과

### M2 — MCP Server (1-2주)

- FastMCP로 8개 tools 구현
- 로컬에서 헤르메스가 호출 테스트
- stdio transport 완성
- StreamableHTTP (Tailscale) 추가

### M3 — Dashboard MVP (2-3주)

- Svelte 5 + Vite 셋업
- sidebar + search + markdown render
- 로컬에서 동작 확인
- [[content/bm25-search]] MiniSearch 통합
- Vector Search 검토 (M3-M4 경계)

### M4 — Hosting (1주)

- VPS 세팅 (Hetzner/Vultr 일본)
- Tailscale 설치 ([[_meta/deployment]])
- Caddy + docker-compose + systemd
- GitHub webhook 배포

### M5 — Backup / DR + PWA (1주)

- GitHub Actions 자동 push
- VPS 스냅샷 cron
- DR runbook 작성 + 분기 훈련 ([[_meta/dr-runbook]])
- PWA 설정 (모바일)

### M6 — Polish (3달)

- Graph view (D3 force)
- 다른 프로젝트 1개 추가 (시스템 재사용 검증)
- 운영 다듬기 (관측 가능성, 메트릭)
- AI 기능 ([[_meta/ai-roadmap]])

---

## 성공 지표 (90일)

| # | 지표 | 목표 |
|---|---|---|
| K1 | vault 페이지 수 | ≥ 100 |
| K2 | 평균 outbound [[wikilinks]] | ≥ 2.0 |
| K3 | lint 모순 0건 | 100% |
| K4 | Dashboard 폰에서 사용 | 1일 1회+ |
| K5 | 다른 프로젝트 1개 추가 | 동작 검증 |
| K6 | DR 복구 훈련 | 분기 1회 통과 |
| K7 | 비용 | ≤ $10/월 |

---

## 결정 후 다음 단계

- [x] **D1-D6 결정** — W5에서 모두 결정 완료
- [ ] 다이어그램 검증 (`architecture.html` 브라우저로 열기)
- [x] **M1 시작 (Data Layer)** — W1-W5 완료 (2026-06-24~25)
- [ ] M2 시작 (MCP Server)

---

## 관련

- [[_meta/requirements]] — 요구사항
- [[_meta/architecture-5layer]] — 5-Layer 아키텍처
- [[_meta/ai-roadmap]] — AI 활용 로드맵 (M3-M6 상세)
- [[_meta/mvp-prd]] — 초기 PRD
- [[SCHEMA]] — vault 규약
