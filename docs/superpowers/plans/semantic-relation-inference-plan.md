---
title: Semantic Relation Inference Engine Plan (v3)
created: 2026-07-09
updated: 2026-07-09
type: rule
tags: [system, meta, ai, plan, graph, mvp, roadmap]
---

# Semantic Relation Inference Engine Plan

> **BLUF**: "문서를 잘 저장하는 것"이 아니라 **"문서를 잘 연결하는 것"**이 Raven의 핵심입니다. 욕심내지 않고 MVP 단계에서는 4개의 핵심 의미 관계(`uses`, `depends_on`, `implements`, `related`)와 지식 추출 파이프라인에 집중하며, 향후 Graph Analytics(중심성, 커뮤니티 분석)로 확장하기 위한 3계층 아키텍처를 정의합니다.

## 1. 아키텍처 원칙: 3계층 분리 (3-Layer Separation)
그래프 엔진이 잘 그려지는 것과 지식이 잘 연결된 것은 완전히 다른 문제입니다. Raven은 이 둘을 명확히 분리합니다.

1. **Knowledge (지식/Fact)**: 문서 그 자체 (예: Authentication, JWT)
2. **Semantic Graph (의미망)**: 지식 간의 관계를 강타입으로 정의 (예: Authentication `uses` JWT). **이 계층이 Raven의 핵심 자산입니다.**
3. **Visualization (표현/View)**: 구축된 의미망을 어떻게 보여줄 것인가. (Markdown Link, Dashboard, Force-Directed Graph, MCP 등)

## 2. 단계별 MVP 로드맵 (Phased MVP Approach)
처음부터 Ontology나 복잡한 알고리즘을 전부 구현하면 실패할 확률이 높습니다. 가장 핵심적인 "지식 추출과 의미 연결"까지만 MVP로 정의하고 점진적으로 확장합니다.

### MVP v1: 지식 추출 파이프라인 (Knowledge Curation)
- 에이전트와 사용자의 대화 세션 등 정제되지 않은 데이터 처리.
- `Raw` ➔ `Curator` ➔ `Proposal` ➔ `Approve` ➔ `Wiki (content/)` 로 이어지는 지식화 기본 워크플로우 확립.

### MVP v2: 최소 노드 정의 (Minimal Node Meta)
- 복잡한 메타데이터 대신 시스템 구동에 필요한 최소한의 메타 정보만 Frontmatter에 정의합니다.
- `id`, `slug`, `type`, `collection`, `status`, `aliases`

### MVP v3: 핵심 의미 관계 엔진 (Core Semantic Relation) 🌟 (Raven의 차별점)
- 수많은 Relation Type을 정의하지 않고, 가장 중요한 **5가지**만 먼저 도입합니다.
  - `uses` (사용함)
  - `depends_on` (의존함)
  - `implements` (구현함)
  - `implemented_by` (구현체 - implements의 역방향)
  - `related` (단순 연관)
- **모든 Relation에는 `evidence`(근거)가 반드시 포함**되어야 합니다. "왜 이 문서가 연결되었는가"에 답할 수 있어야 성공입니다.

### MVP v4: 기본 시각화 (Graph View)
- 복잡한 분석 없이 Obsidian과 동일한 수준의 기본 **Force-Directed Graph** 하나만 우선 제공하여 노드의 밀집도를 시각적으로 확인합니다.

### MVP v5: 대시보드 문서 뷰 (Dashboard View)
- 문서를 열었을 때, 단순 백링크가 아니라 카테고리화된 관계를 보여줍니다.
  - **Uses**: JWT
  - **Depends on**: Architecture
  - **Implemented by**: AuthRepository

---

## 3. Post-MVP: 고급 지식 네트워크 분석 (Knowledge Analytics)
MVP(①~⑤)가 안정화된 이후, 이미 구축된 훌륭한 Semantic Graph 데이터베이스를 바탕으로 **Graph Analytics** 알고리즘을 돌려 노드의 속성을 자가 발전시킵니다.

- **Graph Analytics 알고리즘 적용**: 
  - `PageRank` (지식 중요도)
  - `Betweenness Centrality` (브릿지/허브 역할 분석)
  - `Community Detection` (논리적 도메인 그룹화)
- **동적 노드 속성 (Dynamic Node Properties)**: 
  - 그래프 분석을 통해 `importance`, `centrality`, `community`, `layer`, `freshness` 수치를 계산하여 노드 메타데이터에 반영.
- **다양한 시각화 뷰어 (Advanced Views)**:
  - Concentric View, Timeline, Domain View 등 분석된 메타데이터를 UI 요소(크기, 색상, 투명도, 위치)와 매핑.
- **인사이트 자동 추출**:
  - *"이 문서는 Backend와 Finance를 연결하는 핵심 브리지 문서입니다."*
  - *"이 Collection은 너무 비대합니다. 분리가 필요합니다."* 와 같은 AI 어드바이스 제공.

## 4. 권장 개발 순서 (Development Order)
1. **Vault** (Markdown 관리 시스템)
2. **MCP** (에이전트 연동 표준 진입점) 👈 *Agent가 큐레이션과 관계 설정을 할 수 있는 기반*
3. **Curator** (Raw 데이터에서 지식 추출)
4. **Semantic Relation** (5개 핵심 의미 연결 엔진) 👈 *(여기까지가 사실상 핵심 MVP)*
5. **Dashboard** (관계형 문서 열람 UI)
6. **Graph View** (Force-Directed 시각화)
7. **Analytics** (지식 네트워크 딥 분석)
