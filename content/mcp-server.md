---
title: MCP (Model Context Protocol) 서버
created: 2026-06-25
updated: 2026-06-25
type: concept
tags: [concept, system, mcp, ai, python]
sources: [_meta/system-design.md]
confidence: high
---

# MCP (Model Context Protocol) 서버

## 정의

> [Anthropic MCP](https://modelcontextprotocol.io/) — LLM/AI 에이전트가 외부 도구와 데이터 소스에 접근하는 **표준 프로토콜**.
> 한 번 만들면 어떤 AI(헤르메스/Claude/Codex)에서도 같은 방식으로 호출 가능.

핵심 아이디어: LLM마다 API를 다시 짜지 말고, **공통 인터페이스**를 정의하자.

## tools vs resources

MCP는 두 가지 노출 방식을 구분한다:

| 종류 | 역할 | 우리 시스템 예시 |
|---|---|---|
| **Tools** | LLM이 **호출하는 함수** (액션) | `wiki_search`, `wiki_get_page`, `wiki_lint` |
| **Resources** | LLM에 **자동 주입되는 컨텍스트** (read-only 데이터) | `wiki://index`, `wiki://page/{slug}`, `wiki://schema` |

**비유**:
- tools = LLM의 "손" (무언가 한다)
- resources = LLM의 "눈" (무언가를 본다)

## 우리 시스템 (Python FastMCP)

**선택**: Python FastMCP (헤르메스가 Python이므로 통일, [[_meta/system-design]] §2.2 결정)

**Transport**:
- `stdio` — 로컬 (헤르메스 → MCP 직접 파이프)
- `StreamableHTTP` — 원격 (Claude iOS, Codex → VPS via Tailscale)

**Tools (M2에서 구현 예정)**:
```python
def wiki_search(query: str, top_k: int = 10) -> list[SearchHit]
def wiki_get_page(slug: str) -> Page
def wiki_ingest(source: str, mode: str = "auto") -> IngestResult
def wiki_update(slug: str, content: str, frontmatter: dict) -> UpdateResult
def wiki_lint() -> LintReport
def wiki_graph(format: str = "json") -> Graph
def wiki_log(tail_n: int = 20) -> list[LogEntry]
```

**Resources (MCP가 자동 주입)**:
- `wiki://index` — 페이지 카탈로그 (slug + tags + titles)
- `wiki://page/{slug}` — 단일 페이지 전체
- `wiki://graph` — 노드/엣지 JSON
- `wiki://log/recent` — 최근 N개 액션

## Tailscale 인증

원격 호출 시 보안:
- VPS는 **공개 포트 0개** ([[content/tailscale-mesh]])
- MCP 포트(8765)는 Tailscale 인터페이스에만 bind
- 클라이언트 = Tailscale identity (MagicDNS 또는 100.x IP)
- 인증 헤더 생략 가능 — Tailscale 자체가 L3 인증

## 권한 모델 (3단계)

**기본 = read-only** ([[SCHEMA]] §MCP 권한):

```bash
# 기본 (read-only)
python3 -m wiki_mcp.server
# 가능: search, get_page, lint, graph, log
# 불가: update, ingest

# Write 활성화 (명시적 opt-in)
python3 -m wiki_mcp.server --write

# Admin (위험: delete, rename, raw_content 노출)
python3 -m wiki_mcp.server --admin
```

**왜 read-only가 기본인가**:
- AI가 위키를 망가뜨릴 수 있음 (R6 리스크, [[_meta/system-design]])
- 명시적 승격 = 사고 방지
- backup은 어차피 git에 있음 (롤백 가능)

## 왜 MCP인가 (vs 직접 HTTP API)

[[content/mcp-vs-rest-api]]에서 자세히 비교. 핵심만:
1. **클라이언트 표준** — Claude iOS가 MCP 지원하면 내 위키에 바로 연결
2. **tool calling 표준** — LLM의 function call schema를 그대로 사용
3. **spec 안정성** — Anthropic이 spec 관리, 우리는 따라가기만
4. **이식성** — 다른 위키/문서 시스템에도 같은 server 코드 재사용

## 우리 시스템의 위치

```
[Claude iOS / Hermes / Codex]
         │ MCP (HTTP+SSE)
         ▼
   ┌─────────────┐
   │  wiki-mcp    │ ←── Tailscale only
   │  :8765       │
   └──────┬───────┘
          │ SQLite query
          ▼
      wiki.db
```

## 한계 / 미결정

- MCP spec이 아직 빠르게 진화 중 (R6 위험)
- StreamableHTTP 트랜스포트 안정성 검증 필요 (M2 첫 스프린트)
- 인증 없는 stdio 사용 시 로컬 파일 시스템 권한 의존

## 관련

- [[content/llm-wiki]] — LLM Wiki 패턴 (MCP가 위키에 접근하는 표준)
- [[content/rag-vs-llm-wiki]] — RAG vs LLM Wiki
- [[content/tailscale-mesh]] — MCP 보안 전제
- [[content/mcp-vs-rest-api]] — MCP vs REST API 비교
- [[_meta/system-design]] — Layer 2 설계 원문
- [[SCHEMA]] — MCP 권한 모델 정의
