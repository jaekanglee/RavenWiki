---
title: 시스템 설계 — 요구사항 분석 & 5-Layer 아키텍처
created: 2026-06-24
updated: 2026-06-24
type: prd
tags: [prd, system, architecture, meta]
sources: [raw/articles/karpathy-llm-wiki-2026.md]
confidence: high
---

# 시스템 설계 — 요구사항 분석 & 5-Layer 아키텍처

> **한 줄 요약**: 5개 레이어로 구성된, Obsidian-free, Tailscale-meshed, MCP-native 위키 시스템

---

## 1. 사용자 요구사항 (Requirements)

### 1.1 니즈 (Needs)

| # | 니즈 | 근거 |
|---|---|---|
| N1 | **Obsidian 없이 위키 운영** | 유료 구독 거부, 데이터 주권 |
| N2 | **개발자 친화적** | CLI/git/마크다운 중심 |
| N3 | **Tailscale로 안전 외부 접근** | VPS에 직접 공개포트 ❌ |
| N4 | **폰/웹에서 사용** | PWA 또는 모바일 친화 UI |
| N5 | **자동 정리/유지보수** | LLM이 bookkeeping 담당 (Karpathy 패턴) |
| N6 | **표준 인터페이스** | 어떤 AI에서든 같은 방식으로 접근 |

### 1.2 제약 (Constraints)

| # | 제약 | 영향 |
|---|---|---|
| C1 | **월 비용 최소화** (목표: $10 이하) | VPS 사양, 외부 서비스 의존 ❌ |
| C2 | **로컬 개발 가능** | macOS에서 직접 빌드/실행 |
| C3 | **VPS 자체 운영 중** | 인프라 통제 가능 |
| C4 | **1인 사용자** (MVP) | 다중 사용자/권한은 out of scope |
| C5 | **git 사용 가능** | 형상관리 도구로 충분 |

### 1.3 핵심 사용자 인용

> "옵시디언 안 사고, 모티브만 빌려서 내가 직접 만들 거야."
> "구축만 잘 해놓으면 무료고, 내 입맛에 맞게 쓰고."

→ **원칙**: 직접 구축 + 무료 + 커스텀 자유

---

## 2. 5-Layer 아키텍처

### 2.1 Layer 1 — Wiki Data Structure (SoT)

**목적**: 영구적, 검증 가능한, 사람이 읽을 수 있는 진실의 원천

| 컴포넌트 | 역할 | 빌드 주체 |
|---|---|---|
| `*.md` + YAML frontmatter | 페이지 본문 | [[wiki-writer]] |
| `index.json` | 페이지 카탈로그 (slug/tags/links) | [[wiki-curator]] 자동 생성 |
| `search.idx` | BM25 검색 인덱스 (MiniSearch 직렬화) | [[wiki-curator]] 자동 생성 |
| `graph.json` | 노드/엣지 (D3 force용) | [[wiki-curator]] 자동 생성 |
| git | 모든 변경 추적/롤백 | 사용자 (커밋) |

**핵심 결정**:
- DB ❌ (markdown + JSON 파일로 충분)
- DB는 검색 성능이 필요할 때만 (10k 페이지 이상)
- frontmatter는 wiki-architect가 강제 검증 (lint)

### 2.2 Layer 2 — MCP Server

**목적**: 모든 AI(헤르메스/Claude/Codex)가 같은 방식으로 위키에 접근

| 항목 | 내용 |
|---|---|
| 프로토콜 | Anthropic MCP (Model Context Protocol) |
| 구현 | Python FastMCP 또는 Node.js MCP SDK |
| Transport | stdio (로컬) + StreamableHTTP (원격) |
| 인증 | Tailscale identity 헤더 (remote) |

**Tools (AI가 호출하는 함수)**:

```python
# 예시 인터페이스 (MCP tools)
def wiki_search(query: str, top_k: int = 10, project: str | None = None) -> list[SearchHit]
def wiki_get_page(slug: str) -> Page
def wiki_ingest(source: str, project: str, mode: str = "auto") -> IngestResult
def wiki_update(slug: str, content: str, frontmatter: dict) -> UpdateResult
def wiki_lint(project: str | None = None) -> LintReport
def wiki_graph(project: str | None = None, format: str = "json") -> Graph
def wiki_log(tail_n: int = 20, project: str | None = None) -> list[LogEntry]
def wiki_create_project(name: str, schema_ref: str = "default") -> Project
```

**Resources (컨텍스트 자동 주입)**:
- `wiki://index` — 카탈로그
- `wiki://page/{slug}` — 단일 페이지
- `wiki://graph` — 그래프
- `wiki://log/recent` — 최근 활동
- `wiki://schema` — 규약 문서

**왜 MCP인가**:
- 헤르메스가 죽어도 다른 AI가 같은 도구로 작업 가능
- Claude iOS 앱에서 내 위키 검색 가능 (엄청난 가치)
- 한 번 만들면 다른 위키에도 재사용

### 2.3 Layer 3 — Dashboard (자체 UI)

**목적**: 사람(Jake)이 위키를 보고/읽고/탐색하는 인터페이스

**기술 스택 (제안)**:

| 후보 | 장점 | 단점 |
|---|---|---|
| **Svelte 5 + Vite** | 가벼움, 빠른 빌드 | 생태계 좁음 |
| React + Vite | 생태계 풍부 | 무거움 |
| Astro | SSG + island | SPA 느낌 약함 |
| **Elm** | 타입 안정, 학습 가치 | 러닝커브 |

→ **1차 추천: Svelte 5** (가볍고, Obsidian-feel 가능, 내 입맛대로)

**필수 기능**:

| 기능 | 구현 | 우선순위 |
|---|---|---|
| 📂 Sidebar tree | 디렉토리 + frontmatter 기반 | P0 |
| 📝 Markdown render | remark/rehype + 코드/수식/Mermaid | P0 |
| 🔍 Search (BM25) | MiniSearch (자체 빌드) | P0 |
| 🕸 Graph view | D3 force 또는 vis-network | P1 |
| 🌓 Theme + hotkeys | dark/light + vim mode + cmdk | P1 |
| 📲 PWA | service worker + manifest | P1 |
| ✏️ Editor | 별도 페이지 (CodeMirror 6) | P2 |
| 💬 Comments/HL | 선택 (없어도 됨) | P3 |

**왜 직접 만드나** (vs Obsidian):
- 키바인딩 내 맘대로 (vim/emacs/VSCode 스타일)
- 검색 알고리즘 내 맘대로 (BM25, vector, hybrid)
- Mermaid 다이어그램 자유
- 폰에서 내가 만든 UI = 학습 가치 + 자기 만족
- 0% 락인

### 2.4 Layer 4 — Hosting (VPS + Tailscale)

**목적**: 24/7 가용성 + 안전한 외부 접근

**VPS 사양 (제안)**:

| 항목 | 최소 | 권장 | 비용 |
|---|---|---|---|
| CPU | 1 vCPU | 2 vCPU | |
| RAM | 2GB | 4GB | |
| SSD | 20GB | 40GB | |
| OS | Ubuntu 24.04 LTS | 동일 | |
| 위치 | 한국/일본 (저지연) | 동일 | |
| 월 비용 | $5 | $10 | Hetzner/Vultr |

**서비스 구성 (systemd)**:

```ini
# /etc/systemd/system/wiki-dashboard.service
[Service]
ExecStart=/usr/bin/node /opt/wiki/dashboard/dist/server.js
Restart=always
Environment=PORT=5173

# /etc/systemd/system/wiki-mcp.service
[Service]
ExecStart=/usr/bin/uv run /opt/wiki/mcp/server.py
Restart=always
Environment=PORT=8765
```

**Tailscale 구조**:

```
┌─ Tailscale MagicDNS ─────────────────────┐
│  wiki-vps      → 100.x.y.z              │
│  wiki-dashboard → 100.x.y.z:5173        │
│  wiki-mcp       → 100.x.y.z:8765        │
└─────────────────────────────────────────┘
         ↑                          ↑
    iPhone (Tailscale 앱)     Claude iOS / Codex
    → Safari/MCP              → HTTPS
```

**핵심 보안**:
- VPS는 **공개 포트 0개** (Tailscale만)
- 인증 = Tailscale identity
- 도메인 불필요 (MagicDNS)
- Let's Encrypt 불필요 (Tailscale TLS)

**배포 플로우**:
```
로컬 commit → git push → VPS webhook → git pull → systemctl restart
                              ↓
                          healthcheck OK
```

### 2.5 Layer 5 — Backup / Disaster Recovery

**목적**: 어떤 재해도 데이터를 잃지 않는다

**3-2-1 규칙**:
- **3**: 원본 + 사본 2개
- **2**: 다른 매체 2개 (local disk + GitHub)
- **1**: 오프사이트 1개 (GitHub)

| 백업 대상 | 주기 | 저장소 | 복구 시점 |
|---|---|---|---|
| vault 전체 (git push) | hourly | GitHub private repo | 1시간 전까지 |
| VPS 디스크 스냅샷 | weekly | VPS provider | 1주 전까지 |
| 로컬 Time Machine | daily | 외장 SSD/클라우드 | 1일 전까지 |

**RPO / RTO 목표**:

| 지표 | 목표 | 의미 |
|---|---|---|
| RPO (Recovery Point Objective) | ≤ 1시간 | 최대 1시간 작업 손실 |
| RTO (Recovery Time Objective) | ≤ 30분 | 장애 후 30분 내 복구 |

**DR 시나리오**:

| 장애 | 대응 | 예상 시간 |
|---|---|---|
| VPS 디스크 손상 | 새 VPS → git clone → systemd enable | 30분 |
| GitHub 장애 | 로컬 백업에서 push | 1시간 |
| 로컬 + VPS 동시 손상 | GitHub에서 clone (off-site) | 10분 |
| vault 데이터 오염 | `git revert` 또는 `git reset` | 5분 |

**DR Runbook** (`wiki/_meta/dr-runbook.md`):
- 분기 1회 복구 훈련 (실제로 새 VPS에서 clone)
- 마지막 복구 성공 일자 log에 기록

---

## 3. 데이터 플로우 (End-to-End)

### 3.1 Ingest 플로우 (자료 1개 추가)

```
[사용자] URL/file → Telegram → wiki-orchestrator
                                    ↓
                            wiki-writer (ingest tool)
                                    ↓
                  ① raw에 저장 (sha256 frontmatter)
                  ② 핵심 추출 + discussion
                  ③ N개 페이지 생성/갱신
                                    ↓
                            wiki-curator
                  ④ index.json 갱신
                  ⑤ search.idx rebuild
                  ⑥ graph.json 갱신
                  ⑦ log.md append
                  ⑧ git commit + push
                                    ↓
              ┌─────────────────────┴─────────────────────┐
              ↓                                           ↓
    VPS (webhook pull)                          GitHub (origin)
              ↓
    systemctl restart dashboard (if changed)
              ↓
    /healthz OK → 새 자료 즉시 반영
```

### 3.2 Query 플로우 (검색/탐색)

```
[사람] 폰에서 wiki://vps:5173 → Dashboard
                                  ↓
                        index.json 로드 (O(1) 트리)
                        search.idx 로드 (lazy)
                                  ↓
[사람] "JWT 인증" 검색 → BM25 → 상위 10개 결과
                                  ↓
[사람] 페이지 클릭 → markdown 렌더
                                  ↓
[사람] Graph 탭 → D3 force → JWT 노드 중심 subgraph
```

### 3.3 MCP 플로우 (AI 호출)

```
[AI: Claude iOS] "내 위키에서 RAG 패턴 설명 찾아줘"
                              ↓
                  MCP HTTP+SSE (Tailscale)
                              ↓
              wiki-mcp:8765/tools/call/wiki_search
                              ↓
                  { results: [...pages with JWT...] }
                              ↓
                  AI가 종합 → 사용자에게 답변
```

---

## 4. 비용 분석

| 항목 | 비용 | 비고 |
|---|---|---|
| VPS (Hetzner CAX11) | ~$5/월 | ARM 2vCPU/4GB/40GB |
| Tailscale | $0 | Personal 무료 (5명까지) |
| GitHub private | $0 | 1GB까지 무료 |
| 도메인 | $0 | Tailscale MagicDNS |
| TLS 인증서 | $0 | Tailscale 내부 TLS |
| **합계** | **~$5/월** | |

vs Obsidian Sync: $8/월 × 12 = $96/년
vs Notion Plus: $10/월 × 12 = $120/년

→ **1년차에 $60-115 절약 + 내 입맛 + 데이터 주권**

---

## 5. 리스크 & 완화

| # | 리스크 | 영향 | 완화 |
|---|---|---|---|
| R1 | VPS 해킹 | 데이터 유출 | 공개포트 0, Tailscale만, 2FA |
| R2 | VPS provider 장애 | 24h 다운 | GitHub에서 즉시 clone, 다른 provider |
| R3 | LLM이 평범한 요약만 생성 | wiki 품질 저하 | governance 규칙 (SCHEMA), lint로 자동 탐지 |
| R4 | vault 비대화 (1만 페이지+) | 검색/렌더 느려짐 | 페이지 분리 강제, 청크 인덱스 |
| R5 | 내가 휴가 → 자동화 작동 안 함 | wiki outdated | cron lint, wiki-curator 일 1회 |
| R6 | MCP API 변경 | 호환성 깨짐 | spec 안정화 후 구현, fallback |

---

## 6. 마일스톤 (Phase별)

### M0 — 설계 ✅ (현재)
- 5-layer 아키텍처 정의
- MVP PRD/페르소나/시나리오
- LLM Wiki 패턴 + 비판 정리
- 모델 프로필별 배분

### M1 — Data Layer (1주)
- SCHEMA.md 고도화
- harumoa 디렉토리 + 10페이지 ingest
- wiki-architect가 RULES.md 작성
- wiki-curator가 index.json 빌드 자동화

### M2 — MCP Server (2주)
- FastMCP로 5개 tools 구현
- 로컬에서 헤르메스가 호출 테스트
- stdio transport 완성

### M3 — Dashboard MVP (3주)
- Svelte 5 + Vite 셋업
- sidebar + search + markdown render
- 로컬에서 동작 확인

### M4 — Hosting (4주)
- VPS 세팅 (Hetzner)
- Tailscale 설치
- Caddy + systemd 구성
- GitHub webhook 배포

### M5 — Backup / DR (5주)
- GitHub Actions 자동 push
- VPS 스냅샷 cron
- DR runbook 작성 + 테스트
- PWA 설정 (모바일)

### M6 — Polish (3달)
- Graph view
- 다른 프로젝트 1개 추가
- 운영 다듬기

---

## 7. 성공 지표 (90일)

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

## 8. 결정해야 할 것들 (Decisions)

| # | 결정 | 옵션 | 권장 |
|---|---|---|---|
| D1 | Frontend 프레임워크 | Svelte/React/Astro/Elm | Svelte 5 |
| D2 | MCP 구현 언어 | Python (FastMCP) / Node (MCP SDK) | Python (헤르메스와 통일) |
| D3 | VPS 위치 | 한국/일본/미국 | 일본 (저지연+안정) |
| D4 | GitHub private vs Gitea 자체호스팅 | GitHub / Gitea | GitHub (1차, 이관 가능) |
| D5 | 인증 방식 | Tailscale only / + Authentik | Tailscale only (1차) |
| D6 | 도메인 사용 여부 | Tailscale MagicDNS / 자체 도메인 | MagicDNS (1차) |

→ 결정 후 다음 단계 진행

---

## 9. 다음 할 일

- [ ] **D1-D6 결정** (사용자)
- [ ] 다이어그램 검증 (`architecture.html` 브라우저로 열기)
- [ ] M1 시작 (Data Layer)

---

## 관련

- [[mvp-prd]] — 초기 PRD
- [[wiki-persona]] — 페르소나
- [[wiki-scenario]] — 시나리오
- [[wiki-schema]] — 데이터 규약
- [architecture.html](architecture.html) — 통합 아키텍처 다이어그램 (브라우저로 열기)
