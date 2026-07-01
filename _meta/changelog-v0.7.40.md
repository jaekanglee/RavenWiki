# raven v0.7.40 — 검색 결과 및 대시보드 이슈 링크 클릭 시 라우팅 버그 수정

> **핵심**: 상단 네비게이션 검색바와 요약 페이지의 이슈 목록에서 특정 문서를 클릭했을 때, URL에 보관소(:vault) 파라미터가 누락되어 `Not found: concepts/...` 형태의 404 에러 화면이 노출되던 라우팅 버그를 정정했습니다.

릴리스 일자: 2026-07-01
이전: v0.7.39

---

## 1. 배경 및 현상

* **버그 제보**: 문서 뷰어가 열려 있는 상태에서 상단 검색창에 키워드를 검색해 나온 결과를 클릭할 때, URL이 `/page/concepts/flutter-active-target`과 같이 `:vault` 세그먼트 없이 라우팅되는 버그가 발생했습니다.
* **원인**:
  * React Router의 페이지 경로 정의가 `/page/:vault/*`로 지정되어 있어, 첫 번째 슬래시 뒤 세그먼트가 `:vault` 값으로 인식됩니다.
  * `Layout.tsx` 및 `SearchBar.tsx` 내부에서 클릭 액션 시 `/page/${vault}/${slug}`가 아닌 `/page/${slug}`로 잘못 리다이렉트함으로써, 슬러그의 첫 부분(예: `concepts`)이 보관소명으로 인식되어 잘못된 탐색을 시도했습니다.
  * 동일하게 `DashboardDigest.tsx`의 린트 이슈 목록에서도 `/page/${iss.slug}`로 vault 세그먼트가 빠진 링크가 렌더링되고 있었습니다.

---

## 2. 변경 사항

### 2-1. 상단 네비게이션 검색창 라우팅 수정 (`Layout.tsx`, `SearchBar.tsx`)

* **`Layout.tsx`**: SearchBar의 `onSelect` 콜백 내 리다이렉트 경로를 `window.location.assign(\`/page/\${vault}/\${s}\`)`로 수정하여 현재 활성화된 vault 파라미터가 URL 경로에 포함되도록 했습니다.
* **`SearchBar.tsx`**: `onSelect` prop이 없을 때의 자체 폴백 navigate 경로도 `\`/page/\${vault}/\${slug}\``로 동기화 수정했습니다.

### 2-2. 대시보드 요약 화면 이슈 링크 수정 (`DashboardDigest.tsx`)

* 린트 및 요약 카드 내의 개별 이슈 상세 링크 대상을 `\`/page/\${vault}/\${iss.slug}\``로 변경하여 정상적으로 해당 보관소의 페이지 뷰어로 진입하게끔 수정했습니다.

---

## 3. 검증 결과

| 항목 | 결과 | 비고 |
|---|---|---|
| `npm run build` (tsc 포함) | **Success** | 대시보드 컴파일 및 빌드 정상 통과 |
| `pytest tests/` 전체 | **490 passed, 1 skipped** | 테스트 통과 및 회귀 버그 없음 확인 |
| `git status` 변경 목록 일치 | **Success** | `Layout.tsx`, `SearchBar.tsx`, `DashboardDigest.tsx` 변경 |

---

## 4. 다음 단계

* 라우팅 경로 생성 유틸리티 함수(e.g., `makePageUrl(vault, slug)`)를 공통으로 구조화하여 향후 유사한 라우팅 실수 방지.
