---
title: Changelog v0.7.157
created: 2026-07-09
updated: 2026-07-09
type: rule
tags: [api, database, dashboard, frontend, test]
---

# v0.7.157 — Phase 4: 의미 관계 기반 지식 그래프 시각화 고도화 (Graph View)

## BLUF
Phase 4를 통해 대시보드 그래프 뷰의 의미 관계(relations) 기반 엣지 시각화, 관계 호버 툴팁 및 상호작용 제공, 그리고 관계 유형 필터링 기능을 구현함으로써 지식 그래프 시각화 고도화를 성공적으로 완료하였으며, 관련 API/단위 테스트를 통과시켰습니다.

## 무엇을 했는가

| 변경 | 파일 | 효과 |
|---|---|---|
| API 의미 관계 엣지 노출 | `raven/api/server.py` | `/api/vaults/{name}/graph` 엔드포인트에서 `relations` 테이블을 조회하여 의미 관계를 엣지로 노출하고 일반 wikilink와의 중복을 방지 |
| 그래프 엣지 타입 정의 추가 | `dashboard/src/types.ts` | `GraphEdge` 인터페이스에 `relation_type`, `evidence`, `reason` 선택적 필드 추가 |
| 엣지 스타일 및 툴팁 렌더링 | `dashboard/src/components/GraphCanvas.tsx` | 5대 핵심 의미 관계별 엣지 색상, 실선/점선 패턴, 화살표 방향 및 색상을 차별화하여 렌더링하고, 노드 및 관계 엣지에 마우스 호버 시 상세 정보를 표시하는 HTML 툴팁 연동 |
| 관계 필터 컨트롤 패널 추가 | `dashboard/src/routes/GraphPage.tsx` | 그래프 뷰의 컨트롤 패널에 의미 관계 체크박스 필터를 추가하고, 엣지 필터링에 따라 고립 노드를 동적으로 숨길 수 있도록 필터링 로직 개선 |
| 필터링 비즈니스 로직 확장 | `dashboard/src/lib/graph/derive.ts` | `GraphFilterState`에 `visibleRelations`를 추가하고 `filterGraphView` 내에서 관계형 엣지를 먼저 필터링하고 노드 활성 상태를 동적으로 계산하도록 개편 |
| API 단위 테스트 추가 및 검증 | `tests/test_api.py` | `/graph` API가 의미 관계 엣지를 상세 메타와 함께 성공적으로 가져오고 중복을 제거하는지 확인하는 `test_api_vault_graph_includes_semantic_relations` 통합 테스트 구현 |

## 왜 했는가 (4 저장 신호)

- **재사용 가능성**: 그래프 시각화의 관계 유형 필터링 상태와 엣지 렌더링 설계를 공통 라이브러리(`derive.ts`, `GraphCanvas.tsx`)로 통합하여, 향후 전체화면 모달이나 미니맵 등 모든 그래프 뷰에서 동일한 의미 관계 스타일과 필터링 기능을 즉시 재사용할 수 있도록 도모함.
- **인수인계**: 그래프의 연결선들이 단순 텍스트 링크인지, 핵심 의존성(`depends_on`)이나 쓰임새(`uses`)인지 시각적으로 한눈에 식별할 수 있게 함으로써 다음 세션의 에이전트 및 사람 운영자에게 고도로 시각화된 지식 맥락을 제공함.
- **scope/provenance 추적 필요성**: 관계 엣지에 마우스 호버 시 툴팁을 통해 `evidence`와 `reason`을 즉시 출력함으로써 왜 이 문서들이 이러한 의미적 연관을 맺고 있는지 근거를 쉽게 역추적할 수 있게 함.

## 검증

- **단위/통합 테스트**: `make test` 실행 -> 743 passed ✅
- **정적 타입 및 빌드 검증**: `npx tsc --noEmit` 및 `npm run build` 정적 번들 검증 (Passed) ✅
