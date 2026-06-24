---
title: Andrej Karpathy
created: 2026-06-25
updated: 2026-06-25
type: person
tags: [person, ai, karpathy, llm-wiki]
sources: [raw/articles/karpathy-llm-wiki-2026.md]
confidence: high
---

# Andrej Karpathy

## 한 줄 소개

> 카르파시 — OpenAI 공동창업, Tesla AI 국장 역임, 현재 Eureka Labs 창업.
> LLM Wiki 패턴의 원저자. 우리 시스템의 출발점.

## 우리 시스템과의 관계

[[content/llm-wiki]] — "LLM이 점진적으로 빌드하고 유지보수하는 영구적 위키" 패턴.
2026년 4월 gist로 공개 (우리 [[raw/articles/karpathy-llm-wiki-2026]]에 저장).

**우리 시스템 = Karpathy 패턴의 변형**:
- ✅ 차용: 3-Layer (raw/wiki/schema), index/log, wikilinks
- ❌ 거부: Obsidian 의존, 유료 플러그인
- 🆕 추가: Cognitive Governance ([[content/beyond-karpathy-llm-wiki]]), 자체 도구

## 주요 기여 (우리 시스템에 영향)

### 1. LLM Wiki 패턴 (2026-04-04)
- gist로 공개: <https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f>
- **핵심 통찰**: "위키는 영구적이고, 복합축적되는 산물이다."
- 인간은 bookkeeping에서 지쳐 위키를 포기 → LLM은 안 지친다
- "Obsidian = IDE, LLM = 프로그래머, wiki = 코드베이스"

### 2. Compiler 비유
- **RAG** = JIT 검색 (just-in-time)
- **LLM Wiki** = AOT 통합 (ahead-of-time) — 한 번 빌드, 재사용
- 우리 [[content/rag-vs-llm-wiki]] 표에 정리

### 3. 3-Layer 아키텍처
| 레이어 | 역할 | 우리 채택 |
|---|---|---|
| Raw sources | 불변 1차 자료 | ✅ (git 추적) |
| Wiki | LLM이 빌드/유지 | ✅ (`content/`) |
| Schema | vault 규약 | ✅ (`SCHEMA.md`, `RULES.md`) |

### 4. Vannevar Bush 비유
- Memex (1945) — 개인 큐레이션 지식 저장소
- Bush가 풀지 못한 "누가 maintenance를 하나" → LLM이 한다

## 우리 시스템에서 인용

[[content/llm-wiki]]에 정리된 핵심 인용:
> "RAG는 매번 raw에서 검색해서 답 생성 → 축적 없음"
> "LLM Wiki는 LLM이 raw를 읽고 → entity/concept 페이지 빌드 → cross-ref 유지 → 한 번 컴파일, 계속 재사용"

## 한계 — 우리가 보완한 부분

Karpathy 패턴 그대로 따르면 **"정확하지만 죽어있는 페이지 300개"** ([[content/beyond-karpathy-llm-wiki]]).

**Karpathy가 비운 것**: "어떻게 통합할 것인가" (governance).
→ 우리가 Cognitive Governance를 추가 ([[SCHEMA]] §Governance).

## Karpathy의 다른 영향 (참고)

- nanoGPT (2023) — GPT를 300줄로 재구현
- Neural Networks: Zero to Hero (YouTube 시리즈)
- Eureka Labs (2024~) — AI-native 교육 플랫폼
- Tesla Autopilot의 vision-only 접근

→ 우리 wiki 시스템에는 직접 영향 없음 (LLM Wiki만).

## 관련

- [[content/llm-wiki]] — Karpathy 패턴 정리
- [[content/beyond-karpathy-llm-wiki]] — 패턴에 대한 비판 (Cognitive Governance)
- [[content/rag-vs-llm-wiki]] — Karpathy 패턴 vs RAG 비교
- [[raw/articles/karpathy-llm-wiki-2026]] — 원본 소스
