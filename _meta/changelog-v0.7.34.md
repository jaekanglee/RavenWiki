# raven v0.7.34 — 린트 이슈 인라인 자동 수정(Quick Fix) 기능 구현

> **핵심**: 사용자가 지식 보관소의 무결성 오류를 점검함과 동시에 클릭 한 번으로 빠르게 치유할 수 있도록 **린트 이슈 인라인 자동 수정(Quick Fix)** 기능을 린트 보고서 페이지에 추가했습니다. 대표적 린트 오류인 **깨진 위키링크(#1)** 및 **Frontmatter 누락(#10)** 현상에 대해 원클릭 복구 수단을 지원하여, 지식 관리의 편의성과 정합성을 극대화했습니다.

릴리스 일자: 2026-07-01
이전: v0.7.33

---

## 1. 변경 사항

### 1-1. `#1 broken wikilink` 퀵픽스 지원 (복구용 stub 생성)
* **`dashboard/src/routes/LintPage.tsx`**:
  * 린트 카드 목록 중 깨진 위키링크(#1) 규칙에 해당하고 대상(`target`) 문서 경로가 식별된 경우, 행 우측에 `⚡ 퀵픽스 (stub 생성)` 버튼을 노출합니다.
  * 클릭 시 대상 경로에 맞춰 concept 타입의 빈 stub 문서(임시 가이드 문구가 작성된 본문)를 백엔드 `createPage` API로 자동 생성하여, 깨진 연결 관계를 즉시 유효한 상태로 바로잡아 줍니다.

### 1-2. `#10 frontmatter 완전성` 퀵픽스 지원 (기본 헤더 삽입)
* **`dashboard/src/routes/LintPage.tsx`**:
  * Frontmatter 완전성(#10) 규칙에 해당하는 카드 우측에 `⚡ 퀵픽스 (헤더 생성)` 버튼을 노출합니다.
  * 클릭 시 해당 문서를 읽어와 본문 최상단에 필수 frontmatter 메타 속성(`title`, `type`, `created`, `tags`) 기본 템플릿 헤더를 자동으로 추가하고 `updatePage` API로 문서를 업데이트하여 frontmatter 누락을 치료해 줍니다.

### 1-3. LintPage 토스트(Toast) 시스템 탑재
* **`dashboard/src/routes/LintPage.tsx`**:
  * 퀵픽스 비동기 실행 및 성공/실패 여부를 사용자에게 즉각적이고 미려하게 반환하기 위해 `toast` 알림 피드백 구조(2.4s 노출 규칙 준수)를 추가 이식했습니다.
  * 성공 시 린트 리스트 새로고침(`load()`)이 트리거되어, 치료된 오류 항목들이 리스트에서 동적으로 제거되는 매끄러운 사이클을 연출합니다.

---

## 2. 검증 결과

| 항목 | 결과 | 비고 |
|---|---|---|
| tsc compile | **Success** | `npx tsc -b --noEmit` 타입 검증 통과 |
| backend pytest | **488 passed, 1 skipped** | 전체 API 및 Core 회귀 테스트 통과 확인 ✅ |

---

## 3. Next Step
* 현재 대시보드의 주요 화면들(PageView, Graph, Search, Lint, Log, Gardening) 전반에 걸쳐 사용자의 조작 완성도와 가치가 극대화되었습니다. 20개에 달하는 기능/UI 태스크들이 모두 완료되었으므로, 최종 마무리 정리 작업 수행.
