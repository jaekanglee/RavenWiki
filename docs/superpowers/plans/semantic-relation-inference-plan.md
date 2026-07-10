---
title: Semantic Relation Inference Engine Plan (v3)
created: 2026-07-09
updated: 2026-07-10
type: rule
tags: [system, meta, ai, plan, graph, mvp, roadmap, audit]
status: partial
---

# Semantic Relation Inference Engine Plan

> **BLUF**: "문서를 잘 저장하는 것"이 아니라 **"문서를 잘 연결하는 것"**이 Raven의 핵심입니다. 욕심내지 않고 MVP 단계에서는 5개의 핵심 의미 관계(`uses`, `depends_on`, `implements`, `implemented_by`, `related`)와 지식 추출 파이프라인에 집중하며, 향후 Graph Analytics(중심성, 커뮤니티 분석)로 확장하기 위한 3계층 아키텍처를 정의합니다.
>
> **검증 결과 (2026-07-10)**: 일부 UI/analytics 구현은 완료됐지만, DB/build 계층의 relation invariant와 최소 노드 메타 계약이 미완료입니다. 이 계획서는 최종 마감이 아니라 **재작업 대상 partial 상태**입니다.

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

---

## 5. 구현 검증 결과 (2026-07-10 Audit)

이 섹션은 현재 worktree 기준 검증 결과입니다. 결론은 **PARTIAL**입니다.

| 요구사항 | 판정 | 근거 / 남은 문제 |
|---|---:|---|
| 3계층 분리: Knowledge / Semantic Graph / Visualization | ✅ 부분 충족 | MCP relation 도구, DB `relations`, Dashboard/Graph 표현 계층이 분리되어 있음. 다만 DB/build 계층 검증이 약해 Semantic Graph 계층의 불변식이 깨질 수 있음. |
| MVP v1: `Raw` → `Curator` → `Proposal` → `Approve` → `Wiki(content/)` | ⚠️ 미검증 | raw API, draft, curator, review/accept 부품은 있으나 하나의 E2E 테스트로 증명되지 않음. |
| MVP v2: 최소 노드 메타 `id`, `slug`, `type`, `collection`, `status`, `aliases` | ❌ 미완료 | `scripts/build_db.py`의 `pages` schema에는 `slug/title/type/created/updated/path/...`만 있고 `collection/status/aliases`가 canonical field로 없음. API는 `status`를 frontmatter에서 임시 파싱함. |
| MVP v3: relation type 5종 | ✅ 부분 충족 | `wiki_relation_add`는 `uses`, `depends_on`, `implements`, `implemented_by`, `related`만 허용함. |
| MVP v3: 모든 relation에 `evidence` 필수 | ❌ 미완료 | MCP write path에서는 막지만, markdown frontmatter → `build_db.py` → `relations` DB 경로에서는 invalid type과 empty evidence/reason이 그대로 들어갈 수 있음. |
| MVP v4: 기본 Force-Directed Graph View | ✅ 충족 | Dashboard Graph View와 `GraphCanvas`가 기본 force layout을 제공함. |
| MVP v5: 문서 뷰에서 관계 카테고리 표시 | ✅ 충족 | `PageView`가 5개 relation type을 카테고리별로 표시하고 evidence/reason tooltip을 제공함. |
| Post-MVP analytics: PageRank / Betweenness / Community | ✅ 충족 | `raven/core/analytics.py`가 계산 후 `pages`의 `importance`, `centrality`, `community`, `layer`, `freshness`를 업데이트함. |
| Advanced views: Concentric / Timeline / Domain / Layered / Freshness opacity | ✅ 부분 충족 | Graph UI에 view와 시각 매핑이 있으나 dashboard 전체 테스트가 green이 아니고 수동 viewport 검증 증거가 없음. |
| 인사이트 자동 추출 / advice | ✅ 부분 충족 | advice/recommendation 계층은 존재하나 semantic relation plan의 E2E acceptance로 묶인 검증은 부족함. |

### 검증 중 확인한 실패 / 리스크

- **DB relation invariant 미보장**: 임시 vault에서 `type: invalid_type`, `evidence: None`, `reason: None` relation을 frontmatter에 넣고 `scripts/build_db.py`를 실행하면 DB `relations`에 그대로 저장됨.
- **Dashboard regression**: `dashboard`에서 `npm test -- --run` 실행 시 `tests/PageView.graph-scope.test.tsx` 1건 실패. mock에 `fetchRecommendations`가 없어 PageView가 error state로 떨어짐.
- **연관 plan 불일치**: `2026-07-03-vault-bootstrap-redesign.md` 기준 Lite bootstrap은 2종+`log.md`지만 실제 `vault create`는 `_meta/agents/CURATION.md`도 생성함. 이 문제는 본 semantic plan의 직접 구현 범위는 아니지만, "plans 전체 완료" 선언을 막는 교차 리스크임.

### 통과한 검증

- `scripts/.venv/bin/python -m pytest tests/test_graph_reorganization.py tests/test_mcp_relations.py tests/test_db_build_relations.py tests/test_semantic_relations_lint.py tests/test_bootstrap_verify.py -q` → 32 passed.
- `env WIKI_VAULTS_DIR=/private/tmp/raven-pytest-reg-current scripts/.venv/bin/python -m pytest tests -q` → 800 passed, 2 skipped.
- `scripts/.venv/bin/python -m pytest scripts/tests -q` → 40 passed.
- `dashboard`에서 `npx tsc --noEmit` → pass.
- `dashboard`에서 `npm run build` → pass.

---

## 6. 재작업 계획 (Phase Breakdown)

### Phase 0 — 문서 상태 정정

- [x] `status: completed`를 `status: partial`로 낮춘다.
- [x] BLUF의 "4개 relation" 표현을 실제 목표인 5개 relation으로 정정한다.
- [x] audit 결과와 남은 작업을 이 파일에 명시한다.

### Phase 1 — Semantic Graph 계약 하드닝

- [x] relation type 상수를 한 곳에 둔다. MCP, lint, build DB, API가 같은 source of truth를 쓰게 한다.
- [x] `scripts/build_db.py`가 frontmatter `relations`를 읽을 때 relation type 5종만 허용하게 한다.
- [x] `scripts/build_db.py`가 `evidence`와 `reason`이 비어 있는 relation을 DB에 저장하지 않거나 build/lint error로 승격하게 한다.
- [x] `relations` table schema에 가능한 수준의 guard를 추가한다. SQLite 제약이 migration 리스크를 만들면 build-time validation을 우선한다.
- [x] invalid relation type / missing evidence / missing reason frontmatter fixture 테스트를 추가한다.

### Phase 2 — Minimal Node Meta 계약 정리

- [x] `id`, `slug`, `type`, `collection`, `status`, `aliases` 중 실제 canonical source를 결정한다.
- [x] `collection`은 slug 첫 segment 또는 frontmatter field 중 무엇을 SOT로 삼을지 정한다.
- [x] `aliases`를 frontmatter에서 읽어 DB/API/검색에 노출할지 범위를 정한다.
- [x] `pages` DB schema, `GraphNode` type, graph API response를 같은 계약으로 맞춘다.
- [x] node meta contract regression test를 추가한다.

### Phase 3 — Curation Workflow E2E

- [x] raw 자료 생성 또는 fixture 준비.
- [x] raw/draft generation이 proposal artifact를 만드는 경로를 테스트한다.
- [x] review accept가 content page 생성 또는 갱신으로 이어지는 경로를 테스트한다.
- [x] 생성된 content page가 relation metadata와 evidence를 보존하는지 확인한다.
- [x] `Raw` → `Curator` → `Proposal` → `Approve` → `Wiki(content/)` 전체 흐름을 하나의 E2E test로 묶는다.

### Phase 4 — Dashboard Regression 정리

- [x] `PageView.graph-scope.test.tsx` mock에 `fetchRecommendations`를 추가하거나 PageView의 recommendation failure가 page load를 죽이지 않도록 분리한다.
- [x] `npm test -- --run` 전체 green을 회복한다.
- [x] Graph detail tab UI에 대한 최소 렌더링 테스트를 추가한다. 기존 plan의 `vitest --run GraphPage` 요구를 실제 테스트로 맞춘다.
- [ ] 모바일 375px~430px viewport에서 graph detail panel 3열 탭과 mini action toolbar를 수동 검증하고 결과를 기록한다. (2026-07-10: 사용자 지시로 실제 화면/브라우저 검증은 미실행, 코드 테스트만 수행)

### Phase 5 — Final Acceptance Gate

- [x] invalid relation frontmatter가 DB에 들어가지 않음을 임시 vault E2E로 재검증한다.
- [x] `scripts/.venv/bin/python -m pytest tests -q` 통과.
- [x] `scripts/.venv/bin/python -m pytest scripts/tests -q` 통과.
- [x] `dashboard`에서 `npm test -- --run` 통과.
- [x] `dashboard`에서 `npx tsc --noEmit` 통과.
- [x] `dashboard`에서 `npm run build` 통과.
- [ ] 모든 항목이 통과한 뒤에만 `status: completed`와 `tags: [..., completed]`로 되돌린다.
