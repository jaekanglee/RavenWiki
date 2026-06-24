---
title: MCP vs REST API
created: 2026-06-25
updated: 2026-06-25
type: comparison
tags: [comparison, system, mcp, ai]
sources: [_meta/system-design.md]
confidence: high
---

# MCP vs REST API

## 한 줄 비교

> **REST API** = 기계-기계 인터페이스 (모든 클라이언트 가능)
> **MCP** = LLM-기계 인터페이스 (LLM이 도구로 호출, 표준 schema)

## 7가지 차원 비교

| 차원 | REST API | MCP |
|---|---|---|
| **호출 주체** | 사람/모든 클라이언트 | LLM 에이전트 |
| **인터페이스** | HTTP endpoint + JSON | tools (함수) + resources (데이터) |
| **스키마** | OpenAPI (선택) | JSON Schema (필수, 자동 노출) |
| **LLM 통합** | 별도 tool calling 변환 필요 | **네이티브** (LLM이 직접 호출) |
| **discovery** | 문서/SDK 별도 | protocol이 자동 노출 |
| **transport** | HTTP only | stdio + StreamableHTTP |
| **인증** | 자유 (Bearer/API key/OAuth) | 자유 (Tailscale ID 가능) |

## tools vs endpoints

| | REST endpoint | MCP tool |
|---|---|---|
| **정의** | URL + HTTP method + JSON body | 함수 이름 + 인자 schema + 리턴 schema |
| **예시** | `POST /api/search {q: "MCP"}` | `wiki_search(query: str) → list[Hit]` |
| **LLM이 쓰려면** | OpenAPI → JSON Schema → tool calling 매핑 | **그대로** tool |
| **에러 처리** | HTTP status code | protocol-level error response |

**핵심 차이**: MCP는 LLM에게 **schema가 즉시 노출**됨. REST는 변환 계층 필요.

## 우리 선택 (MCP, 왜?)

[[content/mcp-server]]에서 결정. 핵심:

### 1. 표준 인터페이스
- **Claude iOS**가 MCP 지원 → 내 위키에 바로 연결
- **Codex CLI**가 MCP 지원 → 다른 도구에서도 동작
- **Hermes Agent**가 MCP 클라이언트 → subagent 호출 통일
- → 한 번 만들면 모든 AI에서 사용 ([[content/hermes-agent]])

### 2. LLM-native 도구 정의
- function calling schema를 그대로 노출
- LLM이 "MCP 서버가 어떤 도구 제공하는지" 자동 파악
- REST였다면: OpenAPI spec → JSON 변환 → LLM prompt 주입 (수동)

### 3. transport 옵션
- **stdio**: 로컬 (Hermes → MCP 직접 파이프, 빠름)
- **StreamableHTTP**: 원격 (Claude iOS, VPS)
- REST는 HTTP only (stdio 불가)

### 4. 미래 확장성
- MCP는 **protocol** — 구현체는 여러 언어 (Python FastMCP, Node MCP SDK, Rust 등)
- spec 안정화 진행 중 (2025~2026)
- 우리는 Python FastMCP ([[_meta/system-design]] D2 결정)

## REST가 더 나은 경우

| 상황 | 추천 |
|---|---|
| 사람/모바일 앱 클라이언트 | REST |
| 공개 API (외부 개발자 통합) | REST |
| LLM 호출 0% (순수 백엔드) | REST |
| **LLM 에이전트가 주 클라이언트** | **MCP** |
| 도구 카탈로그 자동 노출 중요 | MCP |

## 트레이드오프 인정

| MCP의 한계 | 우리 완화 |
|---|---|
| spec 아직 진화 중 (R6 위험) | 버전 고정 + fallback REST endpoint 병행 |
| LLM 외 클라이언트 코드 더 필요 | 우리 dashboard는 직접 호출 (REST layer 자체 구축) |
| ecosystem 어림 (2026 현재) | spec 안정화 추적, 필요 시 자체 구현 |

## 우리 시스템의 듀얼 인터페이스

**1차 = MCP** (AI 클라이언트)
**2차 = REST** (대시보드 등 직접 호출용, 필요 시 구현)

```
[Hermes subagent / Claude iOS / Codex]
    ↓ MCP (StreamableHTTP)
   ┌──────────┐
   │ wiki-mcp │  ← 1차
   └────┬─────┘
        │ 내부 호출
        ▼
    wiki.db

[React Dashboard (개발/MVP 단계)]
    ↓ 직접
    wiki.db (또는 REST layer 추가 시)
```

## 결정 사항

| # | 결정 | 선택 |
|---|---|---|
| D-API-1 | 메인 인터페이스 | MCP (M2) |
| D-API-2 | 구현체 | Python FastMCP |
| D-API-3 | transport | stdio (로컬) + StreamableHTTP (원격) |
| D-API-4 | 인증 | Tailscale identity (추가 토큰 ❌) |
| D-API-5 | REST 보조 | dashboard 직접 호출 (M3) |

## spec 진동 대응 (R6 리스크)

MCP spec 변화에 대비:
- 버전을 `wiki-mcp` 시작 로그에 명시
- spec breaking change 추적 (Anthropic changelog)
- fallback: 일부 tools는 REST endpoint로 동시 노출 가능 ([[_meta/system-design]] R6 완화)

## 관련

- [[content/mcp-server]] — MCP 서버 상세 구현
- [[content/hermes-agent]] — MCP 클라이언트 플랫폼
- [[content/ssg-vs-spa]] — UI가 백엔드 호출 방식
- [[content/tailscale-mesh]] — MCP 인증/transport 보안
- [[_meta/system-design]] — Layer 2 설계, R6 리스크
