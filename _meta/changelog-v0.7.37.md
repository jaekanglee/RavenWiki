# raven v0.7.37 — 그래프 인사이트 카드 마우스 오버 포커스 연동

> **핵심**: 그래프 탐색 편의성을 높이기 위해 대시보드 사이드바의 인사이트 카드(핵심 허브, 고립 문서, 타입 분포) 및 선택 노드 상세 정보(인바운드, 아웃바운드, 이웃 노드)에 마우스 오버(Hover) 시, 그래프 상에서도 해당 노드와 연관 엣지(혹은 특정 타입의 모든 노드)가 자동으로 하이라이트되는 연동 기능을 추가했습니다.

릴리스 일자: 2026-07-01
이전: v0.7.36

---

## 1. 배경 및 기획

* **사용자 피드백**: "핵심 허브, 고립 문서, 타입 분포 등 마우스 오버하면 그래프에서도 포커스도 맞춰지면 좋겠다."
* **목적**: 그래프 캔버스와 사이드바 정보 창 간의 인터랙션 일관성을 높여, 유저가 사이드바 정보를 보면서 그래프상의 노드를 빠르게 식별할 수 있도록 지원합니다.

---

## 2. 변경 사항

### 2-1. GraphCanvas 컴포넌트 인터페이스 확장 (`GraphCanvas.tsx`)

* **Props 추가**: `externalHighlightNodeId` 및 `externalHighlightType`을 수신할 수 있도록 Props 인터페이스 확장.
* **Focus 연산 로직 보완**:
  * `externalHighlightNodeId`가 주어지면, 해당 노드와 연결된 엣지 및 이웃 노드들을 하이라이트 노드로 취급하여 활성화(`active: true`).
  * `externalHighlightType`이 주어지면, 캔버스 내 해당 타입인 노드들을 전부 하이라이트 처리.
  * 기존 마우스 오버(`hoveredNode`, `hoveredEdgeId`) 계산 로직과 병합하여 유연하게 반응하도록 `useMemo` 재작성.

### 2-2. GraphPage 컴포넌트 호버 이벤트 매핑 (`GraphPage.tsx`)

* **상태(State) 추가**: `hoveredInsightNodeId` 및 `hoveredInsightType`을 선언하여 마우스 이벤트 상태 추적.
* **이벤트 바인딩**:
  * **핵심 허브 목록 (`topConnected`)**: 각 노드 버튼에 `onMouseEnter` / `onMouseLeave` 바인딩 → `hoveredInsightNodeId` 설정.
  * **고립 문서 목록 (`topOrphans`)**: 각 노드 버튼에 `onMouseEnter` / `onMouseLeave` 바인딩 → `hoveredInsightNodeId` 설정.
  * **타입 분포 목록 (`typeBreakdown`)**: 각 타입 버튼에 `onMouseEnter` / `onMouseLeave` 바인딩 → `hoveredInsightType` 설정.
  * **상세 정보 (인바운드 / 아웃바운드 / 이웃 노드)**: 각 항목 노드에 `onMouseEnter` / `onMouseLeave` 바인딩 → `hoveredInsightNodeId` 설정.
* **필터 초기화 연동**: `resetGraphFilters` 호출 시 호버 관련 외부 하이라이트 상태도 함께 null로 초기화.

---

## 3. 검증 결과

| 항목 | 결과 | 비고 |
|---|---|---|
| `npx tsc -b --noEmit` / `npm run build` | **Success** | 컴파일 및 프로덕션 빌드 통과 (타입 오류 없음) |
| `pytest tests/` 전체 | **489 passed, 1 skipped** | 회귀 에러 0건 확인 |
| `git status` 변경 목록 일치 | **Success** | `GraphCanvas.tsx`, `GraphPage.tsx`, `changelog-v0.7.37.md` 변경 |

---

## 4. 다음 단계

* v0.7.38+: 그래프 로컬 캐싱 및 서버 사이드 연산 캐시 테이블 도입을 통한 대형 볼트 최적화 준비.
