---
title: Changelog v0.7.158
created: 2026-07-09
updated: 2026-07-09
type: rule
tags: [api, database, dashboard, frontend, test, lint]
---

# v0.7.158 — Phase 5: 의미 관계 기반 논리 정합성 검증 및 추론 고도화

## BLUF
Phase 5를 성공적으로 안착시킴에 따라, 의미 관계의 대칭 논리 검증(implements ↔ implemented_by) 및 깨진 의존성(depends_on 대상이 rejected/archived 상태) 감지 린트 규칙을 탑재하고, 지식 그래프 뷰 상에서 붉은색 경고 Halo 효과 및 엣지 강조 시각화를 고도화했습니다. 또한, Louvain 알고리즘과 ForceAtlas2 레이아웃에 에지 가중치 연동 모델을 적용하여 5대 의미 관계 중심의 성운형 군집화(Semantic Modularity Layout)를 완착시켰습니다.

## 무엇을 했는가

| 변경 | 파일 | 효과 |
|---|---|---|
| 대칭 관계 및 깨진 의존성 린트 | `raven/core/lint.py` | `check_semantic_relations` 내에 implements ↔ implemented_by 상호 관계 검증 및 depends_on 대상이 rejected/archived 인 경우 린트 경고 리포트하는 로직 추가 |
| 그래프 가중치 연산 고도화 | `raven/core/graph.py` | `louvain_communities`에 가중치 기반 라벨 전파(Weight Sum)를 적용하고 `forceatlas_layout`의 선형 인력(Attraction)에 에지 가중치를 곱해 5대 의미 관계의 물리적 밀착 유도 |
| 그래프 API 메타 및 플래그 연동 | `raven/api/server.py` | graph API에서 노드 상태 frontmatter(status, issue_status, archived)를 파싱하고, `depends_on` 대상이 rejected/archived 상태일 때 노드/엣지에 `broken_dependency=True` 태그 부여. 5대 관계 가중치(5.0)를 레이아웃과 커뮤니티 엔진에 공급 |
| 그래프 붉은색 경고 Halo 시각화 | `dashboard/src/components/GraphCanvas.tsx` | `broken_dependency` 노드 외곽에 붉은색 경고 링(Halo) 효과(반경 size + 4.5)를 투사하고, 엣지 및 화살표를 경고용 붉은색(#ef4444)으로 하이라이트 렌더링 |
| 린트 자동 검증 테스트 추가 | `tests/test_semantic_relations_lint.py` | 대칭성 누락 경고 및 깨진 의존성 린트 경고의 정상 작동을 검증하는 `test_symmetric_relations_and_broken_dependency_lint` 테스트 추가 |
| API 및 그래프 통합 테스트 추가 | `tests/test_graph_reorganization.py` | API를 통해 rejected issue / archived 의존 관계에 대해 노드와 엣지 플래그가 정확히 반환되는지 확인하는 `test_api_vault_graph_broken_dependency_and_weights` 테스트 추가 |

## 왜 했는가 (4 저장 신호)

- **재사용 가능성**: 가중치가 처리되는 Louvain / ForceAtlas 물리 엔진 모델과 붉은색 경고 Halo 렌더러 컴포넌트를 완전히 재사용 가능하도록 설계하여, 미니맵 등 다른 그래프 뷰 인터페이스에서도 즉각 적용 가능함.
- **인수인계**: 이 문서와 테스트 코드를 완성하여 다음 세션의 AI/사람 개발자가 의미망의 논리적 정합성(대칭/의존)이 무너지는 리스크를 조기에 발견하고 검증할 수 있는 품질 안전망을 인계함.
- **scope/provenance 추적 필요성**: `depends_on` 의존 관계에 문제가 생겨 지식 전파의 구멍이 생겼을 때, 사용자가 지식 그래프 상의 붉은색 경고 Halo를 클릭하여 인과의 시작점이 어디서 끊겼는지 한눈에 파악할 수 있도록 도모함.

## 검증

- **단위/통합 테스트**: `make test` 실행 -> 완료 ✅
- **정적 타입 체크**: `make typecheck` 실행 -> Passed ✅
