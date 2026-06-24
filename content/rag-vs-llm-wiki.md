---
title: RAG vs LLM Wiki
created: 2026-06-24
updated: 2026-06-24
type: comparison
tags: [comparison, system, rag, llm-wiki]
sources: [raw/articles/karpathy-llm-wiki-2026.md]
confidence: high
---

# RAG vs LLM Wiki

| 차원 | RAG | LLM Wiki |
|---|---|---|
| **연산 시점** | query time (just-in-time) | ingest time (ahead-of-time) |
| **상태** | 무상태 (raw 다시 봄) | **유상태 (위키에 누적)** |
| **비용** | 매번 검색 + 생성 | 1회 컴파일 + 재사용 |
| **모순 처리** | 모름 (raw 다 검색) | 위키에 명시적으로 기록 |
| **cross-ref** | query 시점 발견 | ingest 시점에 빌드 |
| **synthesis** | query마다 새로 | 이미 통합된 결과 |
| **확장성** | raw N개 → 검색 비용 N | raw N개 → 위키 M 페이지 (M << N raw) |
| **예시** | NotebookLM, ChatGPT file upload | Karpathy 패턴, 본 시스템 |

## 비유

> **RAG** = 시험 때마다 책 처음부터 다시 읽기
> **LLM Wiki** = 시험 전에 필기 정리 + 상호참조

## 각 차원의 trade-off

### 1. 연산 시점
- **RAG**: 질문할 때 검색 → 매번 "지금 이 질문에 필요한 부분"만 봄
- **LLM Wiki**: 자료 모일 때 컴파일 → 질문할 때 "이미 정리된 페이지" 읽음
- **승**: 도메인 깊이/누적이 필요하면 LLM Wiki

### 2. 비용
- **RAG**: raw 1000개 → query마다 embedding + retrieval (계속 비쌈)
- **LLM Wiki**: ingest 1회 = 비쌈, 이후 query = 페이지 읽기만 (저렴)
- **승**: 장기적으로 LLM Wiki (100번 이상 query하면 회수)

### 3. 모순 처리
- **RAG**: 검색된 raw의 모순을 모름 (LLM이 prompt에서 우연히 발견)
- **LLM Wiki**: lint가 `contested: true` + 양쪽 다 명시
- **승**: LLM Wiki (정확성 추구)

### 4. synthesis 품질
- **RAG**: 5개 raw 합성 → 매번 다시 → 약간씩 다름
- **LLM Wiki**: 이미 통합된 페이지 → 일관성
- **승**: LLM Wiki (단, governance 필요 — [[beyond-karpathy-llm-wiki]])

### 5. freshness
- **RAG**: raw만 업데이트하면 끝
- **LLM Wiki**: raw 업데이트 시 위키도 갱신 필요 (curator 역할)
- **승**: RAG (자동화 어려움 없이)

### 6. cold start
- **RAG**: raw 던지면 바로 query 가능
- **LLM Wiki**: ingest 1회 필요
- **승**: RAG (단기)

## 언제 뭘 쓰나

| 상황 | 추천 |
|---|---|
| raw 자주 변함 (실시간 뉴스 피드) | RAG |
| raw 안정적 (논문, 책, 결정) | **LLM Wiki** |
| 한 번 묻고 마는 Q&A | RAG |
| 반복되는 도메인 | **LLM Wiki** |
| cold start 빨리 필요 | RAG |
| 장기 지식 자산 | **LLM Wiki** |
| 팀 협업 + 일관성 | **LLM Wiki** + governance |

## 우리 시스템의 위치

> **LLM Wiki 패턴 채택 + 자체 도구로 구현 (Obsidian 의존 ❌)**

[[wiki-architect]]가 SCHEMA를 잡고, [[wiki-writer]]가 ingest하며, [[wiki-curator]]가 index/log/lint를 돌리고, [[wiki-dashboard]]가 자체 뷰어로 보여준다.

## 관련

- [[llm-wiki]] — Karpathy 패턴 정리
- [[beyond-karpathy-llm-wiki]] — LLM Wiki의 한계와 governance
- [[mvp-prd]] — 우리 시스템 PRD
- [[wiki-schema]] — 우리 vault 규약
