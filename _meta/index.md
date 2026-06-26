---
title: Wiki Index
created: 2026-06-25
updated: 2026-06-25
type: rule
tags: [system, meta, index]
sources: []
confidence: high
---

# Wiki Index

> 코드베이스 자기 자신의 카탈로그. vault = `~/vaults/default/` (분리됨, M2).
> 마지막 업데이트: 2026-06-25 (M2 multi-vault 출시)

---

## 시스템 문서 (운영자가 읽는 것)

### 현재 (v0.2 multi-vault)
- [[raven-guide]] — vault 사용자 가이드 (사람 + 에이전트 공통)
- [[raven-faq]] — 자주 묻는 질문
- [[raven-architecture]] — 4-Layer 아키텍처 (M2, 최신)
- [[SCHEMA-v0.2-multivault]] — vault 외부 스키마 (.registry.json, AgentScope, env)
- [[decisions-d7-d9-multivault]] — M2 결정 (vault 분리 / multi-vault / Python adapter)

### M1 결정/스키마 (보존)
- [[SCHEMA]] — vault 내부 규약 v2.4 (frontmatter, type, tag, governance)
- [[RULES]] — cross-cutting 운영 정책
- [[architecture-5layer]] — v0.1 5-Layer 아키텍처 (보존, v0.2는 raven-architecture 참조)
- [[decisions-d1-d6]] — M1 결정 매트릭스 (D1-D6)

### 운영/배포
- [[deployment]] — VPS + Tailscale 배포 절차
- [[dr-runbook]] — 재해 복구 Runbook (RPO 1h / RTO 30m)
- [[ai-roadmap]] — AI 활용 로드맵 (M3-M6)

### 설계 입력
- [[requirements]] — 사용자 요구사항 (니즈 6 / 제약 5)
- [[wiki-persona]] — 사용자 페르소나
- [[wiki-scenario]] — MVP 시나리오
- [[mvp-prd]] — 자체구축 위키 MVP PRD
- [[m1-completion-report]] — M1 완료 보고

### 원본 자료 (불변)
- [karpathy-llm-wiki-2026.md](_meta/raw/articles/karpathy-llm-wiki-2026.md) — Karpathy "LLM Wiki" gist (2026-04-04)

### 다이어그램
- [architecture.html](_meta/architecture.html) — 통합 아키텍처 (브라우저로 열기)

---

## 코드베이스 위치

> **중요**: vault 데이터는 `~/vaults/default/`에 있음. 코드베이스는 raven/dashboard/mcp/scripts 자산만.

- 코드베이스: `~/Desktop/Dev/Project/Raven/`
- vault: `~/vaults/default/`
- vault registry: `~/vaults/.registry.json`

자세한 위치는 `raven-guide §vault 구조` 참조.

---

## 마이그레이션 메모

### v0.1 (5-layer) → v0.2 (4-layer, multi-vault)
- 단일 vault → **multi-vault** (`~/.registry.json` 중앙 인덱스)
- vault = 코드베이스 내부 → **`~/vaults/<name>/` 외부 분리**
- 인터페이스: CLI + GUI + MCP → **CLI + GUI + Python + HTTP (4-way)**
- 결정: `decisions-d7-d9-multivault`
- 아키텍처: `raven-architecture`

### v1 → v2.4 (M1)
- `concepts/`, `entities/`, `comparisons/` → **`content/` 단일** + `type:` frontmatter
