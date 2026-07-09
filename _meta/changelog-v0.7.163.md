---
title: Changelog v0.7.163
created: 2026-07-10
updated: 2026-07-10
type: rule
tags: [curator, mcp, api, dashboard, test]
---

# v0.7.163 — Phase 10: AI 기반 관계 근거 확장, AI 진단 어드바이스 생성 및 도메인 뷰 대표 레이블 자동화

## BLUF
지식 네트워크의 자동 관계 맺기 능력을 확장하기 위해 `implements`(구현체) 및 `related`(연관) 타입까지 자동 근거 추출기(`evidence.py`)를 고도화했습니다. 또한 규칙 기반 진단에 LLM 및 구체적 Fallback 조언 문장을 생성하는 AI Advice Generator 모듈(`ai_advice.py`)을 구축하고 REST API와 MCP 툴(`wiki_get_ai_advice`)에 각각 연동했습니다. 마지막으로 Domain View 캔버스에서 Louvain 커뮤니티 그룹이 단순히 숫자로 출력되는 문제를 해결하기 위해, 최상위 중요 노드와 고빈도 키워드를 분석해 의미론적 대표 레이블(예: Authentication & Token)을 도적으로 렌더링하는 자동 명명 필터를 `GraphCanvas.tsx`에 탑재 완료했습니다.

## 무엇을 했는가

| 변경 | 파일 | 효과 |
|---|---|---|
| AI 기반 관계 근거 자동 추출 엔진 확장 (Curator Extension v2) | `raven/curator/evidence.py` | `implements` (클래스 상속 및 인터페이스 구현부 감지) 및 `related` (교차 태그 및 본문 고빈도 키워드 매칭) 관계 추가 시 evidence/reason을 자동으로 도출하도록 추론 로직 고도화 |
| 관계 근거 자동 추출 유닛 테스트 | `tests/curator/test_evidence.py` | `implements`와 `related` 관계의 자동 근거 추출 기능이 소스 코드 및 본문 메타데이터 분석을 통해 정상 추출되는지 유닛 테스트 구현 완료 |
| AI Advice Generator 모듈 구축 | `raven/core/ai_advice.py` | 규칙 기반 지식 네트워크 진단 결과를 컨텍스트로, LLM API(Gemini) 또는 구체적 Fallback 가이드 템플릿을 활용해 맞춤형 큐레이션 실시간 조언을 도출하는 핵심 모듈 구축 |
| REST API AI 어드바이스 엔드포인트 신설 | `raven/api/server.py` | `/api/vaults/{name}/ai-advice` GET 엔드포인트를 추가하여 대시보드 및 외부에서 AI 맞춤 조언 데이터를 조회할 수 있도록 지원 |
| MCP AI 어드바이스 조회 툴 신설 | `raven/mcp/cli.py` | `wiki_get_ai_advice` MCP 툴을 추가하여 외부 자율 에이전트(헤르메스 등)가 AI 어드바이스를 직접 활용할 수 있도록 지원 |
| AI 어드바이스 모듈 및 툴 연동 테스트 | `tests/test_advice.py` | 신설된 API 엔드포인트와 MCP 툴이 AI 조언 및 `ai_message`를 포함한 진단 리스트를 정상 반환하는지 테스트 케이스 추가 검증 완료 |
| Domain View 커뮤니티 대표 도메인 자동 레이블링 | `dashboard/src/components/GraphCanvas.tsx` | Louvain 커뮤니티 클러스터링 결과(Community 0, 1 등)에 속한 노드들 중 PageRank `importance`가 가장 높은 최상위 중요 노드의 타이틀과 제목 내 고빈도 키워드를 분석하여, 배경 onion bound 영역에 대표 의미 중심 레이블(예: Community 0 (Authentication & Token))을 자동 표시하는 렌더링 필터 구현 |

## 왜 했는가 (4 저장 신호)
- **재사용 가능성**: `implements` 및 `related` 등 더 넓은 강타입 관계에 대해서도 왜 연결되었는지 구체적인 근거(evidence)를 자동으로 산출하므로, 다른 에이전트들이나 사용자가 구축된 Zettelkasten 지식 그래프를 신뢰하고 재활용할 수 있는 기반을 넓혔습니다.
- **인수인계**: 새로운 AI Advice API 및 MCP 툴을 연동하여 다음 큐레이션 에이전트에게 상황 밀착형 큐레이션 해결 가이드를 제공함으로써, 볼트 자동 정비 루프의 자동화 수준을 한 단계 높였습니다.
- **실패/리스크 기록**: 단순히 `Community 0`, `Community 1`과 같은 기계적 숫자로만 도메인이 나누어져 무엇을 의미하는지 한눈에 파악하기 어렵던 시각적 가독성 한계를 의미 중심 자동 레이블 필터링으로 극복했습니다.

---

## 추가 작업 (Gardening UI 고도화, LOD 줌 최적화, M4 Hybrid Search 파이프라인 설계)

### 무엇을 추가로 했는가

| 변경 | 파일 | 효과 |
|---|---|---|
| 대시보드 Gardening UI 고도화 및 1-click 자율 치유 UX 탑재 | `dashboard/src/routes/DashboardDigest.tsx` | `/api/vaults/{name}/ai-advice` API를 대시보드에 연동하여 AI 맞춤 큐레이션 조언(`ai_message`)을 세련되게 부각하여 표시하고, 고립/연결부족 노드 옆에 'Quick Fix' 버튼을 탑재하여 클릭 한 번으로 추천 타깃 문서와 `uses` 관계를 맺어주는 1-click 자율 치유 UX 완성 |
| 대시보드 관계 생성 및 AI 조언 API 클라이언트 추가 | `dashboard/src/lib/api.ts` | `/api/vaults/{name}/relations` POST API 및 `/api/vaults/{name}/ai-advice` GET API에 대응하는 `addRelation` 및 `fetchAIAdvice` 클라이언트 함수 구현 |
| REST API relations 생성 엔드포인트 구현 | `raven/api/server.py` | 대시보드에서 `wiki_relation_add` 쓰기 도구를 연동할 수 있도록 `/api/vaults/{name}/relations` POST 엔드포인트 및 Pydantic Payload 모델을 추가하고 예외 처리 구축 |
| relations 생성 API 유닛 테스트 추가 | `tests/test_advice.py` | `/api/vaults/{name}/relations` POST API 호출이 정상적으로 해당 마크다운 문서의 frontmatter와 DB 테이블에 의미 관계 및 근거를 주입하는지 `test_relation_add_api` 작성 및 회귀 방지 |
| Domain View Onion Bound 레이블 LOD 줌 최적화 | `dashboard/src/components/GraphCanvas.tsx` | 줌 스케일(`scale < 0.85`)에 반응하여 축소 수준이 높을 때만 대표 도메인 레이블이 화면 크기에 맞춰 크고 선명하게 투사되도록 HUD 스타일(투명도, 크기, 텍스트 그림자 등)을 제어하고, 줌 인 상태에서는 텍스트를 제거하여 노드 가독성을 보호하는 최적화 탑재 |
| M4 대비 Hybrid Search 파이프라인 설계 및 구현 | `raven/core/hybrid_search.py` | 로컬 한국어 임베딩(`ko-sroberta`, `bge-m3-ko`)을 sqlite-vec 기반 `page_vec` 테이블에 연동하고, FTS5 BM25 스코어(가중치 0.6)와 벡터 거리(가중치 0.4)를 결합하여 하이브리드 가상 쿼리 랭킹을 산출하는 핵심 하이브리드 검색 파이프라인 모듈 신설 |
| Hybrid Search 유닛 테스트 추가 | `tests/test_hybrid_search.py` | 로컬 임베딩 mock fallback 동작 및 sqlite-vec 확장 부재 시 BM25 단독 검색으로 우아하게 Fallback하여 정상 결과를 리턴하는지 라이프사이클 검증 유닛 테스트 구현 완료 |

### 왜 추가로 했는가 (4 저장 신호)
- **재사용 가능성**: FTS5 BM25와 임베딩 벡터 결합 검색 파이프라인을 구축해 로컬 지식의 의미론적 Hybrid Search를 가능하게 하여 M4 RAG 기능의 핵심 지식 검색 파트를 재사용 가능하게 하였습니다.
- **인수인계**: 대시보드의 Gardening/Advice 패널에 AI가 큐레이션해준 `ai_message` 가이드를 가독성 높게 표시하고, 1-click 자율 치유 단추(Quick Fix)를 제공하여 에이전트의 추천을 사람이 대시보드 상에서 쉽게 수락해 지식 그래프 정비 루프를 완수할 수 있게 구성했습니다.
- **실패/리스크 기록**: 줌 수준에 따른 HUD LOD 필터를 도입하여 노드와 커뮤니티 대표 텍스트 레이블이 겹쳐서 가독성이 훼손되던 UI 버그성 현상을 시각 정보 밀도 감쇠를 통해 완전히 해소했습니다.

