---
title: "검색 결과: \"LLM Wiki 패턴이란?\" (2026-06-24)"
created: 2026-06-25
updated: 2026-06-25
type: query
tags: [query, llm-wiki, karpathy]
sources: [content/llm-wiki.md, content/beyond-karpathy-llm-wiki.md, content/rag-vs-llm-wiki.md]
confidence: high
---

# 검색 결과: "LLM Wiki 패턴이란?" (2026-06-24)

> 사용자 질문: **"LLM Wiki 패턴이란 무엇인가? 왜 효과적인가?"**
> 위임: wiki-writer → 종합 → 본 페이지로 file-back.

## 한 줄 답변

> **LLM이 점진적으로 빌드하고 유지보수하는 영구적 위키** — RAG와 달리 매번 답을 재구성하지 않고 **한 번 컴파일, 계속 재사용** ([[content/llm-wiki]]).

## 출처 페이지 종합

### 1. [[content/llm-wiki]] — 패턴 정의

**핵심 통찰** (Karpathy):
- 위키는 **영구적이고, 복합축적되는 산물**
- 인간은 bookkeeping에서 지쳐 위키를 포기
- LLM은 안 지친다 → 유지보수 비용 0에 수렴

**3-Layer 아키텍처**:
- Raw sources (불변 1차 자료)
- Wiki (LLM이 빌드/유지)
- Schema (vault 규약)

**3가지 핵심 연산**:
1. **Ingest**: 새 소스 → LLM이 읽고 → 페이지 10-15개 갱신
2. **Query**: 질문 → 페이지들 합성 → 답을 위키에 file-back
3. **Lint**: 정기 health check (모순, stale, orphan, broken)

### 2. [[content/beyond-karpathy-llm-wiki]] — 비판 + Governance

**Jônadas Techio의 핵심 비판**:
- "정확하지만 죽어있는 페이지 300개 = 정리된 하드드라이브"
- LLM은 **평균으로 회귀** (training distribution의 무게중심)
- "위키백과 풍 entry"가 양산됨
- 지적 노동이 사라짐 — 본질은 "왜 중요한가"인데 요약은 "무엇인가"만

**해결: Cognitive Governance**:
- 모순/적대자 찾기 강제
- 생략 표면화
- cross-disciplinary 연결 강제
- "책 뒷면 요약" 거부 가드

### 3. [[content/rag-vs-llm-wiki]] — RAG와 비교

| 차원 | RAG | LLM Wiki |
|---|---|---|
| 연산 시점 | query time (JIT) | ingest time (AOT) |
| 상태 | 무상태 | **유상태** |
| 비용 | 매번 검색 | 1회 컴파일 + 재사용 |
| 모순 처리 | 모름 | 위키에 명시 기록 |

**결론**: 도메인 깊이/누적이 필요하면 LLM Wiki.

## 왜 효과적인가 (3가지 축)

### 축 1: 자동 유지보수
- 인간이 bookkeeping에서 포기 → LLM은 안 지침
- cross-ref, 요약 최신화, 모순 발견 — 자동
- 인적 비용 → 거의 0

### 축 2: 1회 컴파일, N회 재사용
- raw 1000개 → 페이지 100개로 압축
- query마다 검색하지 않고 페이지 읽기만
- 100번 이상 query 시 비용 회수 ([[content/rag-vs-llm-wiki]])

### 축 3: Cognitive Governance로 깊이 유지
- [[SCHEMA]]에 "어떻게 사고할지" 박아넣음
- lint가 governance 위반 자동 탐지
- "책 뒷면 요약" 거부 → "왜 중요한가" 강제

## 우리 시스템에서의 적용

[[_meta/system-design]] §0에서 결정:
- ✅ 패턴 차용 (3-Layer, index/log, wikilinks)
- ❌ Obsidian 의존 거부 (자체 dashboard)
- 🆕 Cognitive Governance 추가 (Jônadas)
- 🆕 4 wiki 프로필로 운영 ([[content/hermes-agent]])

## 다른 도구/패턴과의 관계

| 패턴 | 관계 |
|---|---|
| **RAG** | LLM Wiki의 **선행** (단, 한계 보완) |
| **Fine-tuning** | 다른 종류의 customization (대안) |
| **Obsidian** | Karpathy가 사용, 우리는 거부 ([[content/llm-wiki]] §우리 시스템) |
| **NotebookLM** | RAG 기반, LLM Wiki와 정반대 |

## 인용 가능한 핵심 문장

> "Obsidian은 IDE, LLM은 프로그래머, 위키는 코드베이스." (Karpathy)

> "LLM의 자연스러운 중력은 합의. governance는 저항." (Jônadas)

## 더 읽을 거리

- [[content/llm-wiki]] — Karpathy 원본 패턴 상세
- [[content/beyond-karpathy-llm-wiki]] — 비판 + Cognitive Governance
- [[content/rag-vs-llm-wiki]] — RAG와 상세 비교
- [[content/andrej-karpathy]] — 원저자
- [[content/jonadas-techio]] — 비판자
- [[_meta/raw/articles/karpathy-llm-wiki-2026]] — 원본 gist

## 메타

- 작성일: 2026-06-25
- 위임자: wiki-writer (사용자 질문 종합)
- trigger: query time (사용자가 묻고 LLM이 합성한 결과를 file-back)
- [[content/llm-wiki]] §3가지 핵심 연산 중 "Query → file-back" 사례
