---
title: Changelog v0.7.162
created: 2026-07-10
updated: 2026-07-10
type: rule
tags: [mcp, curator, dashboard, frontend, test]
---

# v0.7.162 — Phase 9: 자율 치유 실무 검증, AI 기반 관계 근거 자동 추출 및 타임라인 Adaptive Scale 적용

## BLUF
의미 관계 형성을 자율화하고 가독성을 강화하기 위해, `uses` 및 `depends_on` 관계 생성 시 두 문서의 본문 및 소스 코드를 분석하여 관계 근거(`evidence`)와 이유(`reason`)를 자동으로 추출하는 AI 기반 인퍼런스 엔진을 Curator 모듈에 탑재했습니다. 또한 고립 노드 진단(`wiki_get_advice`)과 관계 갱신(`wiki_relation_add`)을 결합한 자율 치유 루프를 통합 테스트로 실증하고, 타임라인 뷰의 X축 겹침 문제를 해결하기 위한 동적 밀집도 분산 오프셋 및 시간/일 단위 Adaptive 격자 가이드라인 필터를 도입했습니다.

## 무엇을 했는가

| 변경 | 파일 | 효과 |
|---|---|---|
| AI 기반 관계 근거 자동 추출 엔진 탑재 | `raven/curator/evidence.py` | `uses`, `depends_on` 관계 추가 시 소스 코드 내 import 라인 발굴, 본문 Text Span(제목, aliases, wikilink 등) 매칭, 그리고 fallback wikilink 조작을 통해 evidence/reason을 자동으로 도출하는 추론 모듈 구현 |
| MCP `wiki_relation_add` 툴 확장 | `raven/mcp/tools/write.py` | `evidence` 및 `reason`이 생략되거나 빈 값으로 올 때, `uses`/`depends_on` 타입인 경우 자동 인퍼런스 엔진을 호출하여 채운 후 멱등성 및 정합성을 검증하도록 툴 로직 고도화 |
| 자율 치유 루프 엔드투엔드 통합 검증 | `tests/test_self_healing_validation.py` | 고립 노드가 진단 엔진에서 검출되고, 에이전트가 이를 감지하여 `wiki_relation_add`로 관계를 자동 형성함으로써 고립 상태가 해제되는 일련의 자율 치유 라이프사이클을 실증하는 통합 테스트 작성 |
| 관계 도구 및 자동 추출 유닛 테스트 | `tests/test_mcp_relations.py` | 기존 validation 테스트를 implements 관계로 엄밀하게 분리하고, 자동 추출 모듈의 import/Text-span/Fallback/가드 시나리오를 검증하는 테스트 케이스 추가 |
| Timeline View 동적 시간 축 개선 (Adaptive Scale) | `dashboard/src/components/GraphCanvas.tsx` | X축의 밀집도를 일(Day)/시간(Hour) 단위 격자로 분석하고, 겹치는 노드를 유연하게 가로로 분산시키는 오프셋 필터 탑재. 또한 시간 범위에 따라 15분, 2시간, 일 단위로 눈금을 다이내믹하게 조정하는 Adaptive Grid 가이드라인 렌더링 구현 |

## 왜 했는가 (4 저장 신호)
- **재사용 가능성**: 자동으로 관계의 근거(evidence)를 본문과 소스 코드에서 발굴해냄으로써, 향후 다른 에이전트들이나 사용자가 왜 이 문서들이 연결되었는지 그 맥락을 즉시 확인할 수 있게 보장합니다.
- **인수인계**: 자율 치유 워크플로우를 코드로 실증하는 통합 테스트를 추가하여, 다음 큐레이션 루프를 이어받을 에이전트들이 무결하게 해당 메커니즘을 상속할 수 있게 하였습니다.
- **실패/리스크 기록**: 하루에 수십 개의 문서가 몰려서 작성될 때 타임라인 뷰에서 노드가 겹쳐 뭉개지던 시각적 가독성 저하 리스크를 동적 분산 오프셋과 격자 간격 필터로 안전하게 해소했습니다.
