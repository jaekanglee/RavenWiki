# raven v0.7.24 — Dashboard 첫 실행 Wizard 자동 안내 및 Portal 회귀 통과

> **핵심**: 첫 실행 시 또는 등록된 vault가 없을 때 대시보드가 자동으로 `NewVaultWizard`로 이동하도록 개선하여 UX 콜드 스타트 문제를 완화하고, EditButton 사이드 시트의 Portal 래핑을 추가하여 포탈 검증 테스트를 정상화시켰습니다.

릴리스 일자: 2026-06-30
이전: v0.7.23

---

## 한 줄 요약

대시보드 로드 시 등록된 vault가 0개인 경우 자동으로 `NewVaultWizard`(/vault/new)로 리다이렉트되도록 하여 앱의 초기 사용성을 극대화하였고, `EditButton` 사이드 시트가 `transform` containing block 영향을 받지 않도록 `createPortal`을 적용해 vitest portal 검사(`All-modals-portal.test.tsx`)를 모두 통과시켰습니다.

---

## 1. 변경 사항

### 1-1. Dashboard 첫 실행 Wizard 자동 리다이렉트
* **`dashboard/src/components/Layout.tsx`**:
  * API 서버로부터 vault 목록 패치가 성공적으로 끝나고 빈 목록(`vaults.length === 0`)이 확인될 경우, `/vault/new` 경로가 아니라면 자동으로 리다이렉트시키기 위해 `loaded` 상태 및 `Navigate` 컴포넌트를 통합했습니다.
  * 신규 vault 생성 시 layout 단의 vaults 목록이 실시간으로 갱신될 수 있도록 `useEffect` 의존성 배열에 `refreshKey`를 추가했습니다.
* **`dashboard/src/components/NewVaultWizard.tsx`**:
  * 새 vault 생성 성공 직후 `setActiveVault` 호출 후 `useOutletContext`로부터 가져온 `refresh` 함수를 실행하여 Layout의 vaults 목록 재조회를 유도함으로써, 생성 후 즉시 redirect 되더라도 홈 리다이렉트 루프에 빠지지 않고 생성된 index 페이지로 안전하게 이동하도록 수정했습니다.

### 1-2. EditButton Portal 래핑 및 포탈 테스트 통과
* **`dashboard/src/components/EditButton.tsx`**:
  * side sheet 패널(`position: fixed`)이 parent 요소의 css transform이나 filter 속성에 의해 레이아웃이 깨질 위험을 제거하기 위해 React `createPortal`을 활용해 `document.body` 직속으로 렌더링되도록 수정했습니다.
  * 이 변경을 통해 깨져 있던 `tests/All-modals-portal.test.tsx` 프론트엔드 테스트가 완벽히 성공으로 복구되었습니다.

---

## 2. 검증 결과

| 항목 | 결과 | 비고 |
|---|---|---|
| pytest | **473 passed, 1 skipped** | 백엔드 테스트 100% 성공 ✅ |
| vitest | **106 passed, 1 skipped** | 프론트엔드 테스트 100% 성공 (Portal 테스트 복구 완료) ✅ |
| Vite build | **built in 1.95s** | 프로덕션 빌드 타입 컴파일 검증 완료 ✅ |

---

## 3. 다음 단계
* **v0.7.25 (후보)**: PWA 오프라인 캐싱 최적화 (sw.js 프리패치 성능 개선)
