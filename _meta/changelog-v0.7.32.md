# raven v0.7.32 — 보관소 즐겨찾기(Favorite Vaults) 토글 기능 구현

> **핵심**: 다중 보관소 환경(Multi-vault)을 운용하는 사용자들의 조작 편의성을 높이기 위해 **보관소 즐겨찾기(Favorite Vaults) 토글** 기능을 도입했습니다. 사이드바의 보관소 선택 셀렉터 옆에 별 모양(★) 토글 버튼을 추가하고, 즐겨찾기된 보관소는 Vault Picker 드롭다운 목록의 가장 최상단으로 우선 정렬 배치되도록 스펙을 보강했습니다.

릴리스 일자: 2026-07-01
이전: v0.7.31

---

## 1. 변경 사항

### 1-1. 보관소 즐겨찾기(Favorites) 추적 및 로컬 저장 연동
* **`dashboard/src/components/Sidebar.tsx`**:
  * 로컬 브라우저 세션 간에 즐겨찾기 보관소 목록이 유실되지 않도록 `localStorage`와 연동되는 `readFavoriteVaults`, `writeFavoriteVaults` 헬퍼 함수를 추가했습니다.
  * 보관소의 즐겨찾기 여부를 추적하고 제어하는 `favorites` 상태와 토글용 `toggleFavorite` 핸들러 함수를 구성했습니다.

### 1-2. 즐겨찾기 보관소 최상단 정렬 및 UI 별표(⭐) 부착
* **`dashboard/src/components/Sidebar.tsx`**:
  * 보관소 드롭다운 목록(`select` 요소)을 렌더링하기 전 즐겨찾기(Fav) 보관소가 일반 보관소보다 최상단에 우선 배치되도록 커스텀 정렬(`[...vaults].sort(...)`)을 설계해 적용했습니다. (즐겨찾기 보관소 우선 정렬 -> 기본 보관소 우선 정렬 -> 사전 순 정렬 계층 적용)
  * 드롭다운 목록 각 옵션의 이름 앞에 `⭐` 딱지를 추가하여 사용자가 쉽게 시각적으로 구별할 수 있게 했습니다.
  * Vault Picker 셀렉터 우측에 별표(★) 토글 버튼을 배치하여, 클릭 한 번으로 활성화된 보관소의 즐겨찾기 상태를 실시간 제어하고 정렬 순서가 동적으로 반응하도록 완비했습니다.

---

## 2. 검증 결과

| 항목 | 결과 | 비고 |
|---|---|---|
| tsc compile | **Success** | `npx tsc -b --noEmit` 타입 검증 완료 |
| backend pytest | **488 passed, 1 skipped** | 전체 API 및 Core 회귀 테스트 통과 확인 ✅ |

---

## 3. 다음 단계
* **v0.7.33**: Dashboard의 린트 페이지(`LintPage.tsx`)에 대한 린트 룰별 빠른 필터링 뱃지(Badge) UI를 추가해, 지식 린트 에러들을 종류별로 모아 한눈에 점검할 수 있는 Gardner Linting UX 개선.
