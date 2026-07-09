---
title: Changelog v0.7.159
created: 2026-07-10
updated: 2026-07-10
type: rule
tags: [api, database, dashboard, frontend, test]
---

# v0.7.159 — Phase 6: 관련 문서 추천 시스템 구축 및 지식 네트워크 분석 기반 마련

## BLUF
Phase 6을 완수함에 따라, Co-citation(공동 인용)과 Tag Overlap(태그 중복) 계산 알고리즘에 기반한 의미론적 관련 문서 추천 엔진을 탑재하고, 이를 연동하는 FastAPI API 엔드포인트와 대시보드 문서 뷰 UI를 안착시켰습니다. 추천 문서의 연관성 점수 및 상세한 산출 근거 뱃지(공동 인용 횟수, 중복 태그 개수)를 시각화하여 사용자의 지식 탐색 맥락을 대폭 강화하였고, 향후 Dynamic Node Properties(importance, centrality) 확장을 고려한 API 응답 규격을 설계했습니다.

## 무엇을 했는가

| 변경 | 파일 | 효과 |
|---|---|---|
| 추천 엔진 개발 | `raven/core/recommend.py` | 특정 문서 X에 대해 5대 의미 관계망의 공동 피인용(Co-citation) 횟수 및 태그 중복(Tag Overlap) 개수를 결합하여 상위 5개 연관 문서를 선별하는 추천 로직 구현 (status=rejected 필터링 포함) |
| Core exports 갱신 | `raven/core/__init__.py` | 패키지 수준에서 `recommend_module`을 외부에서 안전하게 가져올 수 있도록 내보내기 추가 |
| API 엔드포인트 추가 | `raven/api/server.py` | `/api/vaults/{name}/pages/{slug:path}/recommendations` 엔드포인트 신설. route 매칭 충돌을 방지하기 위해 catch-all `{slug:path}` 위에 배치 |
| 타입 및 API 헬퍼 정의 | `dashboard/src/types.ts`<br>`dashboard/src/lib/api.ts` | 프론트엔드 단의 `Recommendation` 모델 타입을 정의하고, 백엔드로부터 추천 데이터를 Fetch해올 `fetchRecommendations` 비동기 헬퍼 구현 |
| 대시보드 문서 뷰 연동 | `dashboard/src/routes/PageView.tsx` | 문서 상세 페이지 하단에 "함께 읽어볼 만한 문서" 패널을 렌더링. 각 추천 항목의 스코어 및 뱃지를 미려한 카드 레이아웃과 Hover 효과로 구현 |
| 추천 기능 검증 테스트 | `tests/test_recommendations.py` | 추천 가중치 연산 및 정렬, rejected 문서 필터링 로직, 그리고 API JSON 응답 규격을 엄격하게 검증하는 단위/통합 테스트 추가 |

## 왜 했는가 (4 저장 신호)

- **재사용 가능성**: `recommend.py` 모듈과 `fetchRecommendations` 헬퍼는 대시보드뿐만 아니라 MCP 도구 등 차후 지식 추천이나 분석이 요구되는 다른 진입점에서도 즉시 재사용할 수 있도록 설계되었습니다.
- **인수인계**: Post-MVP 분석 모델로 나아가기 위한 기초 설계(`importance`, `centrality` 속성의 API 구조 선반영)와 이를 증명하는 테스트 코드를 완비하여 후속 개발을 위한 안정적인 인프라를 인계합니다.
- **scope/provenance 추적 필요성**: 단순히 추천 목록을 보여주는 것에 그치지 않고, "어떤 태그가 겹쳤는지", "어떤 문서와 함께 인용되었는지" 추천 근거 뱃지를 구체적으로 명시함으로써 사용자가 노드 간의 숨겨진 맥락적 연관성을 쉽게 추적할 수 있도록 기여합니다.

## 검증

- **백엔드 테스트**: `make test` 실행 -> 748 passed (추가된 추천 테스트 포함 전체 통과) ✅
- **프론트엔드 타입 체크**: `make typecheck` 실행 -> TypeScript compilation Passed ✅
- **프론트엔드 빌드**: `npm run build` 실행 -> Vite production build Passed ✅
