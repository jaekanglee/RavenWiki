# raven v0.7.21 — 대시보드(GUI) UI/UX 개선: 다크 모드 탑재, 사이드 시트 에디터 전환, 린트 구멍 보완

> **핵심**: 대시보드의 투박한 UI/UX 개선을 위해 시스템 테마 연동형 다크 모드와 슬라이딩 사이드 시트 에디터, 14대 린트 라벨 매핑 및 EmptyState 공통 컴포넌트를 반영했습니다.

릴리스 일자: 2026-06-30
이전: v0.7.20

---

## 한 줄 요약

CSS 변수를 활용해 라이트/다크 모드 테마 시스템을 구축하고, 사이드바 하단에 테마 토글 버튼을 추가했습니다. 위키 편집기를 기존 모달(Modal) 방식에서 우측 슬라이드인 사이드 시트(Side Sheet) 레이아웃으로 변경하였으며, 린트 페이지의 누락된 항목 매핑(#13, #14) 및 빈 목록을 위한 공통 `EmptyState` 컴포넌트를 반영했습니다.

---

## 1. 변경 사항

### 1-1. 다크 모드(Dark Mode) 및 전역 트랜지션 탑재
* **`dashboard/src/styles/globals.css`**:
  * `@media (prefers-color-scheme: dark)` 및 `html.dark` 지시어를 추가해 Slate 900 기반의 부드럽고 가독성 높은 다크 모드 컬러 스키마를 탑재했습니다.
  * 모든 대화형 요소(a, button, select, input, .nav-link, .card-flat 등)에 부드러운 트랜지션 효과를 글로벌 부여하여 뻣뻣한 인터랙션을 부드럽게 마감했습니다.
  * `.card-flat` 카드 요소에 마우스 호버 시 위로 슥 뜨는 Hover Lift 트랜지션을 추가해 시각적 깊이를 더했습니다.
* **`dashboard/src/components/Layout.tsx`**:
  * 테마 상태(`theme`: 'light' | 'dark')를 로컬 저장소 및 시스템 기본 설정과 동기화하는 상태 관리 로직을 추가했습니다.
* **`dashboard/src/components/Sidebar.tsx`**:
  * 사이드바 레이아웃 구조를 flex-col 및 독립 스크롤 영역으로 리팩토링하고, 하단에 수동으로 모드를 전환할 수 있는 **테마 토글 버튼**을 배치했습니다. (기존 테스트 코드 컴파일 보존을 위해 `theme` 프로퍼티는 옵셔널 처리하고 기본값 할당)

### 1-2. 우측 슬라이딩 사이드 시트(Side Sheet) 에디터 도입
* **`dashboard/src/components/EditButton.tsx`**:
  * 위키 편집 실행 시 화면을 덮는 팝업 모달 대신, 우측에서 슥 슬라이딩되어 열리는 **사이드 시트(Side Sheet)**를 적용했습니다.
  * 블러 처리된 백드롭(Backdrop)을 적용하여 배경을 닫을 수 있게 하고, 텍스트 에디터 너비를 최적화(max-width 600px)하여 실제 지식 작성 집중도를 개선했습니다.

### 1-3. 린트 페이지 누수 보완 & EmptyState 컴포넌트 추가
* **`dashboard/src/routes/LintPage.tsx`**:
  * `#13` (Cognitive Governance) 및 `#14` (Tier Integrity)의 린트 라벨 매핑이 누락되어 린터 에러 시 번호만 보이던 버그를 고쳤습니다.
  * 린트 개수 제한 범위를 12개에서 14개로 확장하여 모든 린터 결과가 차트와 필터에 정상 노출되게 했습니다.
  * 린트 이슈가 없는 깨끗한 상태일 때, 투박한 문자열 대신 새로 개발한 공통 컴포넌트 `EmptyState`를 렌더링하도록 변경했습니다.
* **`dashboard/src/components/ui/EmptyState.tsx`**:
  * 아이콘, 타이틀, 설명 및 액션 버튼을 담을 수 있는 세련되고 일관된 빈 상태(Empty State) 공통 컴포넌트를 구현했습니다.

---

## 2. 검증 결과

| 항목 | 결과 | 비고 |
|---|---|---|
| tsc compile | **tsc -b --noEmit Passed** | TypeScript 형식 검사 통과 ✅ |
| PWA 빌드 | **npm run build Passed** | production static assets & SW 빌드 성공 ✅ |

---

## 3. 다음 단계
* **v0.7.22 (후보)**: API 응답 `vaults: []` 디버깅
