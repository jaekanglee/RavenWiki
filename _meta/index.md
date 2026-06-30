---
title: Wiki Index
created: 2026-06-25
updated: 2026-06-30
type: rule
tags: [system, meta, index]
sources: []
confidence: high
---

# Wiki Index

> 코드베이스 자기 자신의 카탈로그. Raven은 사람 1차 local-first
> Zettelkasten-inspired Markdown PKM이며, vault는 기본적으로 `~/Raven/<name>/`에 둔다.
> 마지막 업데이트: 2026-06-30 (v0.7.x North Star + Lite bootstrap 표면 정렬)

---

## 현재 제품 정의

> **Raven = Zettelkasten-inspired PKM + Obsidian-style 앱 표면 + agent/LLM Wiki optional layer.**
> 에이전트 없이도 사람이 Dashboard/CLI로 Obsidian처럼 직접 쓰고,
> 원할 때만 LLM Wiki 패턴(raw/log/agent rules)을 켜서 AI 에이전트가
> Raven vault를 활용하게 한다.

### 고정 진입점 4개

| 진입점 | 역할 | 위치 |
|---|---|---|
| CLI | 운영자/자동화 control plane | `raven/cli/` |
| HTTP API | Dashboard backend / 외부 자동화 | `raven/api/` |
| Dashboard | 사람용 탐색/편집 UX, Obsidian 앱 역할 | `dashboard/` |
| MCP | LLM 클라이언트 표준 진입점 | `raven/mcp/` |

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

### 최신 changelog
- [[changelog-v0.7.27]] — 대시보드 완성도 제고 및 백링크·활성 락 연동 UI 개편
- [[changelog-v0.7.26]] — Dashboard 사이드바 UI/UX 개편 및 리팩토링
- [[changelog-v0.7.25]] — Knowledge Gardening 및 Write Guardrail
- [[changelog-v0.7.24]] — Dashboard Wizard 및 Portal
- [[changelog-v0.7.3]] — Lite bootstrap PROJECT-WORKFLOW 템플릿
- [[changelog-v0.7.2]] — Lite bootstrap 사용자 표면 일관성
- [[changelog-v0.7.1]] — Lite bootstrap AGENTS.md 도구 표면 재작성
- [[changelog-v0.7.0]] — Karpathy LLM Wiki +α 가이드

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

> **중요**: vault 데이터는 코드베이스 바깥 `~/Raven/<name>/`에 둔다.
> 코드베이스는 raven/dashboard/mcp/scripts 자산만 가진다.

- 코드베이스: `~/Desktop/Dev/Project/Raven/`
- vault root: `~/Raven/`
- 예시 vault: `~/Raven/harumoa`, `~/Raven/raven-dev`
- vault registry: Raven registry 설정 기준 (`raven where`로 확인)

자세한 위치는 `README.md` 빠른 시작과 `raven where` 출력 기준으로 확인.

---

## 마이그레이션 메모

### v0.6.37 → v0.7.x (North Star 재정렬)
- 강한 "LLM Wiki self-host" 톤 → **사람 1차 Zettelkasten-inspired PKM + Obsidian-style 앱 표면 + LLM Wiki +α 옵션**
- Lite bootstrap 5종은 사용자 vault 표면만 설명
- Dashboard는 사람이 직접 쓰는 앱 역할, MCP/Agent는 optional layer

### v0.1 (5-layer) → v0.2 (4-layer, multi-vault)
- 단일 vault → **multi-vault** (`~/.registry.json` 중앙 인덱스)
- vault = 코드베이스 내부 → **`~/vaults/<name>/` 외부 분리**
- 인터페이스: CLI + GUI + MCP → **CLI + GUI + Python + HTTP (4-way)**
- 결정: `decisions-d7-d9-multivault`
- 아키텍처: `raven-architecture`

### v1 → v2.4 (M1)
- `concepts/`, `entities/`, `comparisons/` → **`content/` 단일** + `type:` frontmatter
