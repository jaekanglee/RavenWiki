# raven v0.7.31 — 사이드바 미니 건강 위젯(SidebarStatsWidget) 구현

> **핵심**: 사용자가 대시보드 내 어느 화면에 있든 현재 선택한 보관소의 건강도를 항상 실시간으로 모니터링할 수 있도록 **사이드바 미니 건강 위젯(SidebarStatsWidget)**을 구현해 사이드바 하단에 배치했습니다. 보관소의 총 페이지 수, 깨진 링크 수, 활성 락 수를 가시화하여 건강 상태에 기민하게 반응하고 대응할 수 있도록 UI/UX 완성도를 높였습니다.

릴리스 일자: 2026-07-01
이전: v0.7.30

---

## 1. 변경 사항

### 1-1. SidebarStatsWidget 컴포넌트 설계 및 배치
* **`dashboard/src/components/Sidebar.tsx`**:
  * 라이프사이클 훅 지원을 위해 `useEffect` 훅을 추가로 임포트했습니다.
  * 보관소의 상태(`/api/vaults/{name}/stats`)와 락 현황(`/api/vaults/{name}/locks`)을 병렬로 fetch하여 상태값(총 페이지, 깨진 링크 개수, 활성 락 갯수)을 실시간 바인딩하는 `SidebarStatsWidget` 컴포넌트를 설계했습니다.
  * 이 미니 건강도 위젯을 사이드바 하단(테마 스위처 바로 위쪽 영역)에 배치하여, 보관소가 전환될 때마다 해당 보관소의 상태가 동적으로 실시간 업데이트되어 미려하게 시각화되도록 UI 레이아웃을 고도화했습니다.
  * 깨진 링크나 활성 락이 1개 이상 존재할 경우 빨간색(`--color-danger`) 혹은 파란색(`--color-primary`) 강조 테마를 적용하여, 사용자가 지식 정원의 불비 사항을 사이드바에서 직관적으로 알아채고 클릭해 조치할 수 있는 안내 장치를 완비했습니다.

---

## 2. 검증 결과

| 항목 | 결과 | 비고 |
|---|---|---|
| tsc compile | **Success** | `npx tsc -b --noEmit` 타입 검증 통과 |
| backend pytest | **488 passed, 1 skipped** | 전체 API 및 Core 회귀 테스트 통과 확인 ✅ |

---

## 3. 다음 단계
* **v0.7.32**: Dashboard Sidebar 상단의 Vault Picker 디자인 개선 및 보관소별 즐겨찾기(Favorite) 토글 기능 추가.
