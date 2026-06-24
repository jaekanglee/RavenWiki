---
title: 5-Layer 아키텍처
created: 2026-06-25
updated: 2026-06-25
type: rule
tags: [system, meta, architecture]
sources: [raw/articles/karpathy-llm-wiki-2026.md]
confidence: high
---

# 5-Layer 아키텍처

> **한 줄 요약**: Data / MCP / Dashboard / Hosting / Backup — 5개 레이어로 구성된 Tailscale-meshed, MCP-native 위키 시스템

> 원본: [[_meta/system-design]] (412줄) → 분리됨 (M1 W5). 백업: `/tmp/system-design-backup.md`.

---

## Layer 1 — Wiki Data Structure (SoT)

**목적**: 영구적, 검증 가능한, 사람이 읽을 수 있는 진실의 원천

| 컴포넌트 | 역할 | 빌드 주체 |
|---|---|---|
| `*.md` + YAML frontmatter | 페이지 본문 | `wiki-writer` |
| `wiki.db` (SQLite) | 인덱스 (slug/tags/links, FTS5, v_backlinks view) | `wiki-curator` 자동 생성 |
| git | 모든 변경 추적/롤백 | 사용자 (커밋) |

**핵심 결정**:
- DB는 SoT가 **아님** (markdown = SoT, DB = Query Index)
- DB는 검색 성능이 필요할 때만 (10k 페이지 이상)
- frontmatter는 wiki-architect가 강제 검증 (lint)
- W2에서 `scripts/build_db.py` 구현 완료 (SQLite v2.4 schema, FTS5, 16 TDD)

---

## Layer 2 — MCP Server

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

**왜 MCP인가**: 헤르메스 죽어도 다른 AI가 같은 도구로 작업 가능 / Claude iOS 앱에서 내 위키 검색 / 한 번 만들면 다른 위키 재사용

**자세한 MCP 개념**: [[content/mcp-server]]

---

## Layer 3 — Dashboard (자체 UI)

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

**왜 직접 만드나** (vs Obsidian): 키바인딩 자유 / 검색 알고리즘 내 맘대로 / Mermaid 자유 / 폰 UI 학습 가치 / 0% 락인

**자세한 아키텍처 대안**: [[content/react-spa-architecture]], [[content/ssg-vs-spa]]

---

## Layer 4 — Hosting (VPS + Tailscale)

**목적**: 24/7 가용성 + 안전한 외부 접근

**VPS 사양 (요약)**: 2 vCPU / 4GB / 40GB / Ubuntu 24.04 / 일본 / ~$5-10/월 (Hetzner/Vultr). 자세한 절차: [[_meta/deployment]]

```
┌─ Tailscale MagicDNS ─────────────────────┐
│  wiki-vps       → 100.x.y.z              │
│  wiki-dashboard → 100.x.y.z:5173         │
│  wiki-mcp       → 100.x.y.z:8765         │
└─────────────────────────────────────────┘
       ↓                                ↓
  iPhone (Tailscale 앱)         Claude iOS / Codex
  → Safari/MCP                  → HTTPS
```

**핵심 보안**: VPS는 **공개 포트 0개** / 인증 = Tailscale identity / 도메인 불필요 / Let's Encrypt 불필요

**배포 플로우**: 로컬 commit → git push → VPS webhook → git pull → systemctl restart → healthcheck OK

---

## Layer 5 — Backup / Disaster Recovery

**목적**: 어떤 재해도 데이터를 잃지 않는다

**3-2-1 규칙**:
- **3**: 원본 + 사본 2개
- **2**: 다른 매체 2개 (local disk + GitHub)
- **1**: 오프사이트 1개 (GitHub)

**상세 절차**: [[_meta/dr-runbook]]

---

## 데이터 플로우 (End-to-End)

### Ingest 플로우 (자료 1개 추가)

```
[사용자] URL/file → Telegram → wiki-orchestrator
   ↓ wiki-writer (ingest tool)
① raw에 저장 (sha256 frontmatter)
② 핵심 추출 + discussion
③ N개 페이지 생성/갱신
   ↓ wiki-curator
④ wiki.db rebuild (build_db.py)
⑤ lint 통과 확인 (lint.py)
⑥ log.md append
⑦ git commit + push
   ↓
VPS (webhook pull)         GitHub (origin)
   ↓
systemctl restart dashboard (if changed)
   ↓
/healthz OK → 새 자료 즉시 반영
```

### Query 플로우 (사람이 폰/웹에서 사용)

`wiki://vps:5173` → wiki.db 로드 (BM25 FTS5) → "JWT 인증" 검색 → top 10 → 페이지 클릭 → markdown 렌더 → Graph 탭 → D3 force subgraph

### MCP 플로우 (AI 호출)

[AI: Claude iOS] "내 위키에서 RAG 패턴 설명 찾아줘" → MCP HTTP+SSE (Tailscale) → `wiki-mcp:8765/tools/call/wiki_search` → `{ results: [...pages] }` → AI 종합 → 사용자에게 답변

---

## 비용 분석

| 항목 | 비용 | 비고 |
|---|---|---|
| VPS (Hetzner/Vultr) | ~$5-10/월 | 2vCPU/4GB/40GB |
| Tailscale / GitHub / 도메인 / TLS | $0 | 모두 무료 티어 |
| **합계** | **~$5-10/월** | |

vs Obsidian Sync: $8/월 × 12 = $96/년 / vs Notion Plus: $10/월 × 12 = $120/년

→ **1년차에 $60-115 절약 + 내 입맛 + 데이터 주권**

---

## 관련

- [[_meta/requirements]] / [[_meta/decisions-d1-d6]] / [[_meta/deployment]] / [[_meta/dr-runbook]]
- [[content/mcp-server]] / [[content/tailscale-mesh]] / [[content/react-spa-architecture]]
