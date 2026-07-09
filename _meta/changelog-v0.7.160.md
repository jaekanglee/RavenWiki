---
title: Changelog v0.7.160
created: 2026-07-10
updated: 2026-07-10
type: rule
tags: [api, database, dashboard, frontend, test]
---

# v0.7.160 — Phase 7: 지식 네트워크 분석 고도화 및 AI 진단 어드바이스 패널 도입

## BLUF
Phase 6의 추천 스키마 기초 위에, 순수 파이썬으로 PageRank 및 Betweenness Centrality 그래프 분석 알고리즘을 자체 구현하여 wiki.db에 캐싱하는 동적 속성 산출 파이프라인을 구축했습니다. 이를 바탕으로 대시보드 그래프 뷰의 노드 크기(importance) 및 테두리 스타일(centrality) 시각화 위계를 고도화하였으며, 지식 네트워크 진단 결과를 미려한 글래스모피즘 카드로 제시하는 AI 조언(Advice) 패널을 대시보드 메인 홈(Daily Digest)에 탑재했습니다.

## 무엇을 했는가

| 변경 | 파일 | 효과 |
|---|---|---|
| 그래프 분석 알고리즘 구현 | `raven/core/analytics.py` | 외부 라이브러리 의존성 없이 순수 파이썬으로 PageRank(지식 중요도), Betweenness Centrality(매개 중앙성/브릿지), Louvain Communities(커뮤니티 탐색) 알고리즘을 구현하고, wiki.db에 동적 속성을 일괄 갱신하는 파이프라인 탑재 |
| DB 스키마 및 빌더 확장 | `scripts/build_db.py`<br>`raven/core/db.py` | `pages` 테이블에 `importance`, `centrality`, `community` 컬럼을 추가하고, 빌드(혹은 inline 빌드) 완료 후 분석 알고리즘이 2-pass로 갱신을 수행하도록 연동. 구형 DB 발견 시 마이그레이션을 강제하는 schema drift 가드 강화 |
| 추천 엔진 및 API 확장 | `raven/core/recommend.py`<br>`raven/api/server.py` | 추천 응답 및 `/api/vaults/{name}/graph` 노드 메타에 캐싱된 importance, centrality 값을 포함하여 반환하도록 연동. 지식 네트워크 진단 목록을 리턴하는 `/api/vaults/{name}/advice` API 엔드포인트 신설 |
| 프론트엔드 API 및 타입 확장 | `dashboard/src/types.ts`<br>`dashboard/src/lib/api.ts` | `GraphNode` 인터페이스에 importance, centrality 속성을 반영하고, AI 조언 목록을 비동기로 로드할 `fetchAdvice` 헬퍼 함수 추가 |
| 그래프 시각화 위계 고도화 | `dashboard/src/components/GraphCanvas.tsx` | 그래프 캔버스에서 노드의 크기를 PageRank 중요도에 비례하도록 동적으로 산출하고, 테두리 굵기 및 밝기 강도를 매개 중앙성(centrality)과 결합하여 주요 허브/브릿지 문서를 시각적으로 즉시 식별할 수 있도록 개선 |
| AI 진단 어드바이스 카드 도입 | `dashboard/src/routes/DashboardDigest.tsx` | 보관소 메인 대시보드 홈(Daily Digest) 상단에 AI 네트워크 분석 결과(브릿지 노드, 비대한 컬렉션 분할 권장, 고립 노드, 연결 부족 중요 지식)를 프리미엄 글래스모피즘 테마의 카드로 출력하고, 원클릭 문서 이동 연동 완료 |
| 회귀 방지 통합 테스트 구축 | `tests/test_recommendations.py`<br>`tests/test_advice.py` | 추천 데이터에서 실값 바인딩 여부를 검증하고, 브릿지/고립 관계 진단 규칙이 정상 동작하여 API가 카드를 올바르게 빌드하는지 입증하는 단위/통합 테스트 완비 |

## 왜 했는가 (4 저장 신호)

- **재사용 가능성**: `analytics.py` 에 구축된 PageRank 및 Centrality 연산 로직은 MCP 및 CLI 진입점에서도 지식 네트워크 진단이나 정원 가꾸기(Gardening) 자동 연동용 핵심 유틸리티로 언제든 재사용 가능하도록 패키지 레벨로 설계되었습니다.
- **인수인계**: Post-MVP 분석 모델 구현 사양을 완전히 마크하여 backend, API, frontend를 매끄럽게 연결하였고, 신설된 `test_advice.py`를 통해 향후 다른 에이전트나 작업자가 기능 수정 시 발생할 수 있는 잠재적 리스크에 대한 안전망을 확보했습니다.
- **맥락 추적**: "왜 이 문서가 중요하며 어떤 역할을 하는지"를 시각적으로 차별화(Radius, Border, Glow)하여 지식망의 복잡도를 사용자가 쉽게 인지하고 탐색하도록 유도하며, 고립 노드 및 거대 노드에 대해 구체적인 진단 사유를 조언 카드로 피드백해 정보 구조의 건전성을 자가 개선할 수 있도록 돕습니다.

## 검증

- **테스트 통과**: `make test` 실행하여 새로 구축한 `test_advice_logic` 및 추천 logic 테스트를 포함해 총 748 Passed 성공적으로 완수 ✅
- **프론트엔드 정합성**: `make typecheck` 실행 시 TypeScript 컴파일 에러 없이 온전하게 Passed 확인 ✅
