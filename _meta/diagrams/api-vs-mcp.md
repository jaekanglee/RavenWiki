# Raven: API vs MCP 진입점 비교 (v0.7.8+)

## 1. 진짜 구조 — API가 write, MCP는 protocol adapter

```mermaid
flowchart TB
    subgraph 사람_인터페이스 [사람 (직접)]
        UI[Dashboard<br/>localhost:5173]
        CLI[CLI<br/>scripts/.venv/bin/python -m raven.cli]
    end

    subgraph 에이전트_인터페이스 [에이전트 (MCP client)]
        MCP[MCP Server<br/>localhost:8766<br/>:8766/mcp]
        Cursor[Cursor / Claude<br/>Desktop / Hermes]
    end

    subgraph 백엔드 [단일 write 경로]
        API[API<br/>localhost:8765]
        CORE[raven.core<br/>(write contract)]
    end

    UI -->|"HTTP POST/GET<br/>JSON"| API
    CLI -->|"직접 호출<br/>Python adapter"| API
    Cursor -->|"stdio / HTTP"| MCP
    MCP -->|"내부적으로<br/>API 호출 (동일)"| API
    API --> CORE
    CORE -->|vault/<br/>log.md<br/>wiki.db| FS[(vault/<br/>filesystem)]

    classDef 사람 fill:#e1f5ff,stroke:#01579b
    classDef 에이전트 fill:#fff3e0,stroke:#e65100
    classDef 백엔드 fill:#f3e5f5,stroke:#4a148c
    class UI,CLI 사람
    class MCP,Cursor 에이전트
    class API,CORE,FS 백엔드
```

## 2. 진실 (사용자 north star)

- **API = write 경로** (사람 + 에이전트 모두 동일)
- **MCP = API의 protocol adapter** (에이전트용 — JSON-RPC over stdio/HTTP)
- **Dashboard = 사람용 UI** (read/write, API 호출)
- **CLI = 사람/스크립트용** (직접 API 또는 Python adapter)

**결론: 4개 진입점 ❌. 3개 (CLI/API/Dashboard) + 1개 protocol adapter (MCP).**

## 3. Write 경로 비교

| 진입점 | 사용자 | Write 경로 | MCP client 필요? |
|---|---|---|---|
| Dashboard | 사람 | Dashboard → API → core.write | ❌ |
| CLI | 사람/스크립트 | CLI → API 또는 직접 core.write | ❌ |
| **MCP** | 에이전트 | MCP → API → core.write | ✅ (MCP client) |
