---
title: 위키 시스템 MVP — Product Requirements Document
created: 2026-06-24
updated: 2026-06-24
type: prd
tags: [prd, system, harumoa, meta]
sources: [raw/articles/karpathy-llm-wiki-2026.md]
confidence: medium
---

# 위키 시스템 MVP — PRD

## 한 줄 요약

> **"마크다운 + git만으로 돌아가는, Obsidian 없이도 쓸 만한 개인 지식 베이스"**

## 왜 만드는가

### 문제 (Problem)

1. **도구 종속**: Obsidian이 좋은 도구지만, Sync/Publish는 유료, 호환성·데이터 주권에 한계
2. **RAG의 한계**: 매번 같은 소스에서 답을 재구성. 축적 없음
3. **수동 위키의 한계**: cross-reference 업데이트가 사람을 지치게 함
4. **LLM이 도와줘도 결과가 평범**: governance 없는 자동 요약 = "책 뒷면 요약"

### 기회 (Opportunity)

- LLM Wiki 패턴(Karpathy 2026-04) — **컴파일 후 reuse**, not 매번 재구성
- markdown + git = 무료, 영구적, 도구 독립
- [[wiki-architect]] / [[wiki-curator]] / [[wiki-writer]] / [[wiki-dashboard]] 4개 Phase 프로필로
  반복 작업 자동화

## 목표 (Goals)

| # | 목표 | 성공 기준 |
|---|---|---|
| G1 | **vault 일관성** | 모든 페이지가 [[wiki-schema]] (SCHEMA.md) 준수 |
| G2 | **ingest 비용 감소** | 한 소스당 평균 10-15페이지 자동 업데이트 |
| G3 | **자체 뷰어 작동** | Obsidian 없이도 그래프/검색/사이드바 가능 |
| G4 | **도메인 독립** | harumoa 외 다른 프로젝트도 같은 시스템으로 동작 |
| G5 | **모순 자동 탐지** | lint pass에서 contradiction 발견 시 인간 알림 |

## 비목표 (Non-Goals)

- ❌ **Obsidian 호환 100%** — `[[wikilinks]]`는 옵션, .obsidian/ 폴더 무시
- ❌ **유료 동기화** — git push로 충분
- ❌ **모바일 앱** — 1차 MVP는 데스크탑 (웹/CLI)
- ❌ **실시간 협업** — git conflict 해결은 인간이
- ❌ **이미지 OCR** — raw text만 다루는 게 1차 범위

## 페르소나

자세한 페르소나는 [[wiki-persona]] 참조.

| 페르소나 | 핵심 니즈 |
|---|---|
| 🧑‍💻 **개인 개발자 (Primary)** | "내 머릿속 지식을 정리하고 싶다. Obsidian 안 살고 싶다." |
| 📚 **리서처 (Secondary)** | "논문/아티클을 누적하고 싶다. synthesis가 자동으로." |
| 👥 **소규모 팀 (Future)** | "팀 위키가 항상 outdated인데 LLM이 유지해줬으면." |

## 사용자 시나리오

자세한 시나리오는 [[wiki-scenario]] 참조.

| 시나리오 | 핵심 플로우 |
|---|---|
| S1. 새 소스 ingest | raw에 파일 → "처리해줘" → 10-15페이지 자동 업데이트 |
| S2. 위키 검색/탐색 | "Graph View 보여줘" / "이 엔티티 어디 정의돼있어?" |
| S3. 모순 발견 | lint가 page A/B 모순 보고 → 인간이 결정 |
| S4. 새 프로젝트 시작 | vault에 새 디렉토리 → 같은 SCHEMA 재사용 |

## 시스템 아키텍처 (개요)

```
[사용자] ─┬─→ [wiki-orchestrator] ─→ [4 Phase 프로필]
          │     (Telegram DM)           ├─ architect (스키마/구조)
          │                             ├─ curator (정리/이관/index)
          │                             ├─ writer (문서 작성)
          │                             └─ dashboard (UI/시각화)
          └─→ [자체 뷰어] ←── [vault/]
                 │              ├─ entities/, concepts/
                 ├─ 검색         ├─ comparisons/, queries/
                 ├─ 그래프 뷰    └─ raw/, _meta/
                 └─ Mermaid
```

## 기술 스택 (제안, 미확정)

| 레이어 | 후보 | 비고 |
|---|---|---|
| **저장소** | markdown + git | 무료, 영구, SoT |
| **뷰어 (1차)** | 정적 사이트 (VitePress? Docusaurus?) | 자체 호스팅 |
| **검색** | BM25 (자체) → 추후 vector | qmd 참고, 의존 ❌ |
| **그래프** | vis-network or D3 force | 자체 렌더링 |
| **클리퍼** | chrome ext (자체) | 1차 MVP 제외 가능 |
| **자동화** | cron + LLM | 주기적 lint pass |

## MVP 성공 지표 (90일)

1. **vault 100페이지 도달** — harumoa 프로젝트 문서 100페이지
2. **링크 밀도 ≥ 2.0** — 페이지당 평균 outbound 2개
3. **모두 [[wiki-architect]]/[[wiki-curator]]/[[wiki-writer]]/[[wiki-dashboard]]로 처리된 1사이클**
4. **자체 뷰어에서 그래프/검색 작동**
5. **다른 프로젝트 1개** 추가해서 같은 시스템으로 동작 검증

## 마일스톤

- **M0 (이번 세션)**: SCHEMA/PRD/Persona/Scenario 작성 ✅
- **M1 (1주)**: vault 디렉토리 + RULES.md, harumoa 페이지 10개
- **M2 (2주)**: 자체 뷰어 1차 (검색 + 그래프)
- **M3 (3주)**: ingest 자동화 (URL → raw → 10-15페이지)
- **M4 (1달)**: lint 자동화 (모순/stale/orphan)
- **M5 (3달)**: 다른 프로젝트 1개 추가 → 시스템 검증

## 리스크 & 완화

| 리스크 | 영향 | 완화 |
|---|---|---|
| LLM이 평범한 요약만 만듦 | High | [[wiki-scenario]] S3의 governance 규칙 적용 |
| 자체 뷰어 개발 지연 | Medium | 1차는 정적 사이트, TUI도 옵션 |
| 카르파시 패턴이 우리 도메인에 안 맞음 | Medium | 1차 MVP는 harumoa 한정으로 검증 |
| vault 비대해져서 성능 저하 | Low | lint로 페이지 분리/아카이브 자동화 |

## 관련

- [[llm-wiki]] — Karpathy 원본 패턴 정리
- [[rag-vs-llm-wiki]] — 왜 RAG가 아닌 LLM Wiki인가
- [[wiki-persona]] — 사용자 페르소나
- [[wiki-scenario]] — MVP 시나리오
- [[wiki-schema]] — vault 규약
