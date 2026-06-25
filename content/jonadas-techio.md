---
title: Jônadas Techio
created: 2026-06-25
updated: 2026-06-25
type: person
tags: [person, ai, llm-wiki, governance]
sources: []
confidence: medium
---

# Jônadas Techio

## 한 줄 소개

> 하벨리아나(Haveliana) — "절대 해변은 하지 마라" 류의 격언/사고 실험으로 알려진 작가.
> 2026년 4월 Karpathy의 LLM Wiki 패턴에 대한 결정적 비판을 제기.

→ 본명/세부 신원은 [[_meta/raw/articles/]]에 미수집. 직접 콘텐츠로만 평가.

## Cognitive Governance 비판

> 출처: "Beyond Karpathy's LLM-Wiki: The Necessity of Cognitive Governance" (2026-04-11)
> <https://www.jonadas.com/writing/essays/beyond-karpathys-llm-wiki>

**핵심 주장**: LLM의 자연스러운 중력은 **합의/평균**. governance 없이는 **정확하지만 죽은** 페이지가 양산된다.

### 세 가지 핵심 비판

#### 1. "지배력 없는 컴파일러는 평균으로 회귀한다"
- LLM = 컴파일러 (Karpathy 비유)
- 컴파일러에게 **지배(governance) 없으면** 평균 결과물
- "위키백과 풍 entry" — 정확하지만 무미건조

#### 2. Docile Compiler 문제
- "정리해줘" → 백과사전 반환
- "무엇인지"만 있고 "무엇과 싸우는가" 없음
- 지적 노동 사라짐 (그게 본질인데)

#### 3. HN 댓글 (qaadika)
- "AI 질문으로 채운 knowledge base는 'personal'하지 않다"
- → 사용자의 목소리가 사라짐

## 우리 시스템에 미친 영향

[[content/beyond-karpathy-llm-wiki]]에 정리된 영향:

| 우리 결정 | Jônadas 영향 |
|---|---|
| **[[SCHEMA]] §Governance 추가** | "어떻게 사고할지" schema에 박기 |
| `[[wikilinks]]` ≥ 2 강제 | 고립 페이지 방지 (governance 자동화) |
| `contested: true` + `contradictions:` | 모순 무시 방지 |
| `confidence: low` lint 플래그 | 약한 claim 굳어지지 않게 |
| 200줄 초과 분리 강제 | 깊이 우선, 표면 요약 ❌ |
| 모든 페이지 "왜 중요한가" 강제 | 본질 유지 |

→ [[SCHEMA]] §Lint 자동 탐지의 9개 규칙이 모두 Jônadas 영향.

## Cognitive Governance 4원칙 (요약)

[[content/beyond-karpathy-llm-wiki]]에서 추출:

1. **모순/적대자 찾기 강제** — "이 페이지의 반대 논거는?"
2. **생략 표면화** — "여기서 빠진 것은?" (`contradictions:` 필드)
3. **cross-disciplinary 연결 강제** — wikilinks로 다른 도메인과 연결
4. **책 뒷면 요약 거부** — "X는 ~이다" 류 표면 요약 ❌

## 우리 시스템에서의 차별점

```
Karpathy 패턴:    자동 유지보수  ──→  정확하지만 죽음
                      │
                      ▼  + Jônadas
우리 시스템:    자동 유지보수 + Cognitive Governance
                      │
                      ▼
                 정확 + 비판적 사고 유지
```

→ lint가 governance 위반 자동 탐지 → curator가 갱신.

## 한계 / 미결정

- Cognitive Governance 자체를 자동화하기 어려움 (LLM의 governance 평가도 LLM...)
- 일부 규칙(`confidence: low` lint)은 휴리스틱 — false positive 가능
- Jônadas의 다른 글/작품은 [[_meta/raw/articles/]]에 미수집 (M0 이후 추가 가능)

## 관련

- [[content/llm-wiki]] — Karpathy 원본 패턴 (우리가 차용)
- [[content/beyond-karpathy-llm-wiki]] — Jônadas 비판 상세 정리
- [[content/andrej-karpathy]] — 원저자 Karpathy
- [[SCHEMA]] — Governance 규칙 구현
