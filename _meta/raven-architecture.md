---
title: 4-Layer 아키텍처 (M2)
created: 2026-06-30
updated: 2026-06-30
type: rule
tags: [system, meta, architecture, raven]
sources: [docs/architecture.md]
confidence: high
---

# Raven 4-Layer 아키텍처 (M2, 최신)

> **BLUF**: Raven은 마크다운 파일(Source of Truth)을 근간으로 하는 로컬 지향(local-first) PKM 도구이며, **4계층 구조(Data, Core Engine, Interface/Adapter, Client/UX)**를 통해 인간 사용자(Dashboard/CLI)와 AI 에이전트(MCP 표준 프로토콜) 모두에게 정합성 있고 격리된 지식 통합 환경을 제공합니다.

---

## 1. 4-Layer 아키텍처 개요

Raven은 데이터와 로직, 진입점을 명확히 분리하기 위해 아래와 같이 **4개 계층(Layer)**으로 설계되었습니다.

```mermaid
flowchart TB
    subgraph Layer4 [Layer 4: Client & UX Layer (사용자/에이전트)]
        Dash[React Dashboard<br/>localhost:5173]
        CLI[Typer CLI<br/>raven cli]
        Agent[AI 에이전트<br/>Claude / Hermes / Cursor]
    end

    subgraph Layer3 [Layer 3: Interface & Communication Layer (진입점)]
        API[HTTP API Server<br/>FastAPI / localhost:8765]
        MCP[MCP Server<br/>FastMCP / localhost:8766]
    end

    subgraph Layer2 [Layer 2: Core Engine Layer (비즈니스 로직)]
        direction TB
        Registry[registry.py<br/>Vault 발견/관리]
        VaultClass[vault.py<br/>Vault CRUD/핸들러]
        DBBuilder[db.py / build_db.py<br/>SQLite 인덱싱]
        Linter[lint.py<br/>14가지 무결성 검증]
        Linker[link.py<br/>Wikilink 파싱/감사]
        Lock[lock.py<br/>파일 락 동시성 제어]
        Log[log.py<br/>log.md 기록기]
    end

    subgraph Layer1 [Layer 1: Vault Data Layer (진실의 원천 - SoT)]
        direction LR
        MD[content/*.md<br/>마크다운 파일]
        SysDoc[_meta/system/<br/>SCHEMA/RULES/AGENTS]
        SQL[wiki.db<br/>SQLite Index Cache]
        LogMD[log.md<br/>작업 감사 로그]
        RegistryJson[.registry.json<br/>중앙 레지스트리]
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
    DBBuilder --> SQL
    VaultClass --> MD
    VaultClass --> SysDoc
    VaultClass --> LogMD
    Registry --> RegistryJson

    %% Styling
    classDef l4 fill:#e1f5ff,stroke:#01579b,stroke-width:2px;
    classDef l3 fill:#fff3e0,stroke:#e65100,stroke-width:2px;
    classDef l2 fill:#f3e5f5,stroke:#4a148c,stroke-width:2px;
    classDef l1 fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px;
    
    class Dash,CLI,Agent l4;
    class API,MCP l3;
    class Registry,VaultClass,DBBuilder,Linter,Linker,Lock,Log l2;
    class MD,SysDoc,SQL,LogMD,RegistryJson l1;
```

자세한 아키텍처 상세 설명 및 데이터 흐름은 [docs/architecture.md](file:///Users/jaekanglee/Desktop/Dev/Project/Raven/docs/architecture.md) 문서를 참조하십시오.

---

## 2. 계층별 요약

1. **Layer 1: Vault Data (SoT)**
   - 마크다운 파일(content/)과 운영 규칙(_meta/system/), 그리고 `.vault.json`이 최종 진실의 원천입니다.
   - 관계형/FTS5 전문 검색 성능을 위해 SQLite 인덱스 캐시(`wiki.db`)를 유지합니다.
2. **Layer 2: Core Engine (`raven.core`)**
   - 볼트 생명주기 및 CRUD, DB 자동 빌더, 14개 린터, 파일 락 동시성 제어, append-only 활동 감사 로그를 다룹니다.
3. **Layer 3: Interface & Communication**
   - Dashboard 연동을 위한 **FastAPI HTTP API (Port 8765)** 및 AI 에이전트 연동을 위한 **FastMCP Server (Port 8766)**를 제공합니다.
4. **Layer 4: Client & UX**
   - 인간 사용자를 위한 **React Dashboard** 및 **Typer CLI**, 그리고 **AI 에이전트**로 구성됩니다.
