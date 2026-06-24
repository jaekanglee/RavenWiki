---
title: LLM Wiki (Karpathy 패턴)
created: 2026-06-24
updated: 2026-06-24
type: concept
tags: [concept, system, karpathy, llm-wiki]
sources: [raw/articles/karpathy-llm-wiki-2026.md]
confidence: high
---

# LLM Wiki (Karpathy 패턴)

## 정의

> LLM이 **점진적으로 빌드하고 유지보수하는 영구적 위키** — RAG와 달리 매번 답을 재구성하지 않음.

원본: [Karpathy, "LLM Wiki" gist (2026-04-04)](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)
(원본은 [[raw/articles/karpathy-llm-wiki-2026]] 에 저장)

## 핵심 아이디어 (The core idea)

> "위키는 영구적이고, 복합축적되는 산물이다."

- **RAG**: 매번 raw에서 검색해서 답 생성 → **축적 없음**
- **LLM Wiki**: LLM이 raw를 읽고 → entity/concept 페이지 빌드 → cross-ref 유지 → **한 번 컴파일, 계속 재사용**

비유:
> "Obsidian은 IDE, LLM은 프로그래머, 위키는 코드베이스."

## 3-Layer 아키텍처

| 레이어 | 설명 | 누가 다룸 |
|---|---|---|
| **Raw sources** | 불변의 1차 자료 (article, paper, image) | 사용자 큐레이션 |
| **Wiki** | LLM이 생성/유지하는 markdown 페이지들 | LLM 전용 |
| **Schema** | vault 규약 (`SCHEMA.md` / `AGENTS.md` / `CLAUDE.md`) | 인간+LLM 공동 진화 |

## 3가지 핵심 연산

### 1. Ingest
새 소스 → LLM이 읽고 → 위키 페이지 10-15개 자동 갱신

### 2. Query
위키에 질문 → LLM이 페이지들 합성 → **답을 다시 위키에 file back** (가치 있으면)

### 3. Lint
정기적으로 LLM이 health check: 모순, stale, orphan, broken link, missing cross-ref

## Index & Log

- **index.md**: 콘텐츠 카탈로그. LLM은 매 ingest마다 갱신, query 때 먼저 읽음
- **log.md**: 시간순 액션 로그. append-only, grep 가능

## 왜 효과적인가 (Why it works)

위키 유지보수의 귀찮은 건 **읽기/생각이 아니라 bookkeeping**:
- cross-ref 업데이트
- 요약 최신화
- 모순 발견/표기
- 일관성 유지

인간은 bookkeeping에서 지쳐 위키를 포기한다. LLM은 안 지친다 → 유지보수 비용 0에 수렴.

인간의 역할: 소스 큐레이션 + 분석 방향 + 좋은 질문
LLM의 역할: 나머지 전부

## Karpathy가 든 비유

> Vannevar Bush의 Memex (1945) — 개인 큐레이션 지식 저장소, associative trails.
> Bush가 풀지 못한 건 "누가 maintenance를 하나" → LLM이 그걸 한다.

## 우리 시스템에서의 적용 (Obsidian 없이)

| Karpathy 제안 | 우리 채택 여부 | 대안 |
|---|---|---|
| Obsidian | ❌ | `wiki-dashboard` 자체 뷰어 |
| Obsidian Sync | ❌ | git push |
| Obsidian Web Clipper | ❌ | 자체 chrome ext (S5 시나리오) |
| Dataview | ❌ | 자체 BM25 검색 |
| Graph View | ❌ | D3 force 자체 렌더 |
| `[[wikilinks]]` | ✅ (호환) | 우리 뷰어도 파싱 |
| index.md | ✅ | 그대로 |
| log.md | ✅ | 그대로 |
| 3-layer (raw/wiki/schema) | ✅ | 그대로 |

**원칙**: Karpathy의 **패턴은 차용**, 도구는 우리 것이.

## 한계 / 비판 (반드시 인지)

[[content/beyond-karpathy-llm-wiki]] (Jônadas Techio)의 핵심 비판:
> "지배력 없는 LLM 컴파일러는 평균으로 회귀한다. 결과는 정확하지만 죽어있다."

해결: **Cognitive Governance** — schema에 **어떻게 사고할지** 규칙 추가
- 모순 찾기 강제
- antagonist 표면화
- cross-disciplinary 연결 강제
- "책 뒷면 요약" 거부 가드

## 우리 시스템에서의 Governance

[[SCHEMA]]에 다음 규칙 포함:
- 모든 페이지는 `[[wikilinks]]` ≥ 2 (고립 금지)
- 모순 발견 시 `contested: true` + `contradictions:` 명기
- `confidence: low` 페이지는 lint에서 플래그
- 200줄 초과 시 분리 강제

## 관련
- [[content/rag-vs-llm-wiki]] — 왜 RAG가 아닌가
- [[content/beyond-karpathy-llm-wiki]] — 비판과 Cognitive Governance
- [[SCHEMA]] — 우리 vault 규약
- [[_meta/mvp-prd]] — 시스템 PRD
- [[raw/articles/karpathy-llm-wiki-2026]] — 원본 소스
