---
title: 4-Layer 아키텍처 (M2, v0.7.68)
created: 2026-06-30
updated: 2026-07-06
type: rule
tags: [system, meta, architecture, raven]
sources:
  - docs/architecture.md
  - _meta/decisions/adr-2026-07-04-schemasys-index-correction.md
confidence: high
---

# Raven 4-Layer 아키텍처 (M2, v0.7.68)

> **BLUF**: Raven은 마크다운 파일(Source of Truth)을 근간으로 하는 로컬 지향(local-first) PKM 도구이며, **4계층 구조(Data, Core Engine, Interface/Adapter, Client/UX)**를 통해 인간 사용자(Dashboard/CLI)와 AI 에이전트(MCP 표준 프로토콜) 모두에게 정합성 있고 격리된 지식 통합 환경을 제공합니다.
>
> **v0.7.66+ 갱신**: raw/ 폴더 정책, multi-vault MCP routing, Tier integrity lint, raw/ API X-Actor 가드 4가지가 v0.7.50~68 누적 반영. 세부 다이어그램 + 데이터 흐름은 [docs/architecture.md](docs/architecture.md) 참조 (7/5 갱신).

---

## 1. 4-Layer 아키텍처 개요

Raven은 데이터와 로직, 진입점을 명확히 분리하기 위해 아래와 같이 **4개 계층(Layer)**으로 설계되었습니다.

```mermaid
flowchart TB
    subgraph Layer4 [Layer 4: Client & UX Layer (사용자/에이전트)]
        Dash[React Dashboard<br/>localhost:5173<br/>+ /raw panel v0.7.50+]
        CLI[Typer CLI<br/>raven cli<br/>+ workspace v0.7.54+]
        Agent[AI 에이전트<br/>Claude / Hermes / Cursor]
    end

    subgraph Layer3 [Layer 3: Interface & Communication Layer (진입점)]
        API[HTTP API Server<br/>FastAPI / localhost:8765<br/>+ raw/ 4 endpoints v0.7.50+<br/>+ X-Aactor 가드 v0.7.69]
        MCP[MCP Server<br/>FastMCP / localhost:8766<br/>+ multi-vault routing v0.7.6x]
    end

    subgraph Layer2 [Layer 2: Core Engine Layer (비즈니스 로직)]
        direction TB
        Registry[registry.py<br/>Vault 발견/관리<br/>+ multi-vault v0.7.6x]
        VaultClass[vault.py<br/>Vault CRUD/핸들러<br/>+ agents allowlist v0.7.37]
        DBBuilder[db.py / build_db.py<br/>SQLite 인덱싱<br/>+ per-type _index/ v0.7.48]
        Linter[lint.py<br/>14가지 무결성 검증<br/>+ Tier integrity #14 v0.7.66+]
        Linker[link.py<br/>Wikilink 파싱/감사]
        Lock[lock.py<br/>v0.7.42 physical lock enforcement]
        Contracts[contracts.py<br/>write_page 단일 진입점 v0.7.67]
        Log[log.py<br/>log.md 기록기]
    end

    subgraph Layer1 [Layer 1: Vault Data Layer (진실의 원천 - SoT)]
        direction LR
        MD[content/*.md<br/>마크다운 파일]
        SysDoc[_meta/agents/<br/>SCHEMA/TOOLS<br/>+ _meta/system/ 운영자]
        SQL[wiki.db<br/>SQLite Index Cache]
        LogMD[log.md<br/>작업 감사 로그]
        RegistryJson[.registry.json<br/>중앙 레지스트리]
        Raw[raw/ v0.7.50+<br/>1차 소스<br/>사람 full CRUD]
    end

    %% Interactions
    Dash -->|"HTTP (REST/JSON)"| API
    CLI -->|"직접 라이브러리 참조<br/>또는 HTTP API 호출"| API
    CLI -->|"직접 호출"| VaultClass
    Agent -->|"JSON-RPC (stdio/HTTP)"| MCP

    MCP -->|"HTTP API 호출"| API
    API -->|"Core API 호출"| VaultClass

    VaultClass --> Registry
    VaultClass --> Lock
    VaultClass --> Log
    VaultClass --> Contracts
    Contracts --> VaultClass
    DBBuilder --> SQL
    VaultClass --> MD
    VaultClass --> SysDoc
    VaultClass --> LogMD
    VaultClass --> Raw
    Registry --> RegistryJson
    Linter --> MD
    Linter --> SysDoc
    Lock --> MD
    Lock --> Raw

    %% Styling
    classDef l4 fill:#e1f5ff,stroke:#01579b,stroke-width:2px;
    classDef l3 fill:#fff3e0,stroke:#e65100,stroke-width:2px;
    classDef l2 fill:#f3e5f5,stroke:#4a148c,stroke-width:2px;
    classDef l1 fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px;

    class Dash,CLI,Agent l4;
    class API,MCP l3;
    class Registry,VaultClass,DBBuilder,Linter,Linker,Lock,Log,Contracts l2;
    class MD,SysDoc,SQL,LogMD,RegistryJson,Raw l1;
```

자세한 아키텍처 상세 설명 및 데이터 흐름은 [docs/architecture.md](docs/architecture.md) 문서를 참조하십시오.

---

## 2. 계층별 요약 (v0.7.68 기준)

1. **Layer 1: Vault Data (SoT)**
   - 마크다운 파일(content/), 운영 규칙(_meta/agents/ Lite bootstrap + _meta/system/ 운영자 확장), `.vault.json`, **raw/ 폴더 (v0.7.50+, 1차 소스)**, log.md가 최종 진실의 원천.
   - **content/_index/ (v0.7.48+)**: 자동 카탈로그 영역. `type` 박지 않음 (system area, ADR-2026-07-04).
   - SQLite 인덱스 캐시(`wiki.db`)는 빌드 산출물 (gitignore).
2. **Layer 2: Core Engine (`raven.core`)**
   - **vault/registry**: multi-vault 발견/관리 (v0.7.6x+)
   - **vault.py**: Vault CRUD + agents allowlist (v0.7.37, opt-in write policy)
   - **db/index_builder**: per-type _index/ 자동 생성 (v0.7.48+, graph hub fan-out 방지)
   - **lint**: 14 lint (v0.7.66+) — Tier integrity #14 추가
   - **lock**: v0.7.42+ physical lock (multi-actor 동시성 강제)
   - **contracts**: v0.7.67+ write_page 단일 진입점 (모든 write 도구 강제)
   - log.md append-only
3. **Layer 3: Interface & Communication**
   - **HTTP API (8765)**: Dashboard backend. v0.7.50+ raw/ 4 endpoints (GET/PUT/DELETE /raw). v0.7.69+ raw/ X-Actor 가드 (사람 운영자만 write)
   - **MCP (8766)**: v0.7.8+ AI 에이전트 표준. v0.7.6x+ multi-vault routing (1 server = 모든 vault)
   - v0.7.67+ 평가 P0/P1/P2 개편: contracts.write_page 단일화, Tier integrity 검증, lint 캐싱
4. **Layer 4: Client & UX**
   - **React Dashboard (5173)**: SPA, /workspace 라우트 (v0.7.54+), /raw panel (v0.7.50+)
   - **Typer CLI**: workspace 명령 (v0.7.54+)
   - **AI 에이전트 (Claude/Hermes/Cursor)**: MCP 표준으로만 접근 (v0.7.8+ Python adapter 제거)

---

## 3. v0.7.66+ 주요 변경 (Tier 1 / Tier 2 / 정책)

| 변경 | 영향 | 평가 |
|---|---|---|
| **raw/ 폴더 정책 (v0.7.50+)** | Layer 1 데이터 모델 확장, Layer 3/4 UI 추가 | ADR-2026-07-02 |
| **multi-vault MCP routing (v0.7.6x)** | Layer 3 MCP 단일화 | ADR-2026-07-03 |
| **physical lock enforcement (v0.7.42)** | Layer 2 lock.py 강화 | 멀티에이전트 §3 honesty |
| **agents allowlist opt-in (v0.7.37)** | Layer 2 vault.py write policy | |
| **per-type _index/ 자동 카탈로그 (v0.7.48)** | Layer 2 db/index_builder | D10 (graph hub fan-out) |
| **Lite bootstrap 2-file (v0.7.65)** | Layer 1 _meta/agents/ 2-file | ADR ebcde83 |
| **Tier integrity lint #14 (v0.7.66+)** | Layer 2 lint 14개 | 평가 B#12 정정 |
| **write_page 단일 진입점 (v0.7.67)** | Layer 2 contracts.py | 평가 P0#1 |
| **raw/ X-Actor 가드 (v0.7.69)** | Layer 3 API write 가드 | 평가 §7 |
| **content/_index/ system area (v0.7.69)** | Layer 1 자동 카탈로그 격리 | ADR-2026-07-04 |

→ **§15.2 RAG 자가 평가**: Raven은 vendor-neutral (Hermes/Claude/Sonnet 등 어떤 LLM에도 동작), `raw/`는 사람 1차 운영, `MCP`는 단일 표준.

---

## 4. 의존성 방향 (단방향)

```
Layer 4 (Client) → Layer 3 (Interface) → Layer 2 (Core) → Layer 1 (Data)
   ↓                  ↓                    ↓               ↓
사용자 인터랙션    HTTP API/MCP         비즈니스 로직     SoT (md files)
```

**단방향 규칙**:
- Layer 2 → Layer 3 호출 ❌ (Core가 Interface를 모름)
- Layer 2 → Layer 4 호출 ❌ (Core가 Client를 모름)
- Layer 1 → Layer 2 호출 ❌ (Data가 Core를 모름)
- Layer 3 → Layer 1 직접 호출 ❌ (Interface가 Data 직접 접근 — 항상 Layer 2 거침)

→ 단방향 의존성으로 **테스트 용이성** + **교체 가능성** (예: Dashboard를 새 프론트엔드로 교체 시 Layer 2 영향 없음).
