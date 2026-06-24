---
title: Beyond Karpathy's LLM-Wiki — Cognitive Governance
created: 2026-06-24
updated: 2026-06-24
type: concept
tags: [concept, system, llm-wiki, governance, criticism]
sources: []
confidence: medium
---

# Beyond Karpathy's LLM-Wiki — Cognitive Governance

> 출처: [Jônadas Techio, "Beyond Karpathy's LLM-Wiki: The Necessity of Cognitive Governance" (2026-04-11)](https://www.jonadas.com/writing/essays/beyond-karpathys-llm-wiki)

## 핵심 비판

> "정확하지만 죽어있는 페이지 300개 = 정리된 하드드라이브"

Karpathy 패턴을 그대로 따르면:
- LLM은 **평균으로 회귀** (training distribution의 무게중심)
- "위키백과" 풍 entry가 양산됨
- **지적 노동이 사라짐** — 본질은 "왜 중요한가"인데 요약은 "무엇인가"만

### HN 댓글 (qaadika)
> "AI 질문으로 채운 knowledge base는 'personal'하지 않다."

## The Compiler Metaphor

| RAG | Karpathy 컴파일러 | 한계 |
|---|---|---|
| just-in-time 검색 | ahead-of-time 통합 | **지배(governance) 없으면 평범화** |
| frantic, erratic | structured, deliberate |  |

Karpathy는 "왜 통합이 좋은가"를 짚었지만, **"어떻게 통합할 것인가"**는 비웠음.

## Docile Compiler 문제

> "LLM에게 '정리해줘'라고 하면 백과사전을 만든다. 평균을 반환한다."

예: Sinek의 Infinite Game 요약 →
- ✅ 정확함
- ❌ 중립적, 철학적 불임
- "무엇인지"만 있고 "무엇과 싸우는가" 없음

## 해결: Cognitive Governance

> LLM의 자연스러운 중력은 **합의** 쪽. governance는 **저항**.

스키마에 **어떻게 사고할지** 명시:
- 모순/적대자 찾기 강제
- 생략(omission) 표면화
- cross-disciplinary 연결
- "책 뒷면 요약" 거부 가드

## 우리 시스템에 적용

[[SCHEMA]]에 다음을 포함:

| 규칙 | 효과 |
|---|---|
| `[[wikilinks]]` ≥ 2 (고립 금지) | 페이지가 다른 맥락과 연결 |
| 모순 발견 시 `contested: true` | 모순이 무시되지 않음 |
| 200줄 초과 분리 강제 | 깊이 우선, 표면적 요약 ❌ |
| `confidence: low` lint 플래그 | 약한 claim이 굳어지지 않음 |
| 모든 페이지에 "왜 중요한가" 섹션 | 본질 유지 |

## 우리 시스템의 차별점

Karpathy의 "유지보수 자동화"는 그대로 + **Jônadas의 "지적 지배"**를 추가:
- LLM이 자동으로 정리하되, **critical thinking을 잊지 않음**
- governance 규칙을 schema에 박아넣음
- lint가 governance 위반 자동 탐지

## 관련
- [[content/llm-wiki]] — Karpathy 원본 패턴
- [[content/rag-vs-llm-wiki]] — RAG와 비교
- [[SCHEMA]] — 우리 vault 규약 (governance 포함)
- [[_meta/mvp-prd]] — 시스템 PRD
