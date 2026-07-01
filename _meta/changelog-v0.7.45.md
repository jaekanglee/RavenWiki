# raven v0.7.45 — 문서 편집 시 제목(title) 수정 기능 추가

> **핵심**: Dashboard의 문서 편집(✏️) 기능에서 본문만 수정 가능하던 제한을 해소하여, 제목(title)도 함께 편집·저장할 수 있게 개선했습니다.

릴리스 일자: 2026-07-01
이전: v0.7.44

---

## 1. 배경 및 기획

* **버그 리포트**: 대시보드에서 문서 수정(✏️ 버튼)을 누르면 Side Sheet에 본문 textarea만 표시되어 있어, **제목(title)을 변경할 수 없는 문제** 발생.
* **원인**: `EditButton` 컴포넌트가 `content` 필드만 props로 받아 API에 `{ content }` 만 전달하고 있었음.
* **백엔드 확인**: `PUT /api/vaults/{name}/pages/{slug}` 의 `PageUpdate` 스키마에 `title: Optional[str]` 이 이미 지원되고 있었음 — 프론트엔드 누락만 수정하면 됨.

---

## 2. 변경 사항

### 2-1. `EditButton.tsx` — 제목 편집 필드 추가 ([EditButton.tsx](file:///Users/jaekanglee/Desktop/Dev/Project/Raven/dashboard/src/components/EditButton.tsx))
- `title: string` prop 추가
- `titleVal` state 추가 (편집 열 때 현재 제목으로 초기화)
- Side Sheet 상단에 `<TextField label="제목" .../>` 공통 컴포넌트로 제목 입력 필드 삽입
- `save()` 함수에서 `updatePage(vault, slug, { content: body, title: titleVal })` 로 전송

### 2-2. `PageView.tsx` — EditButton에 title prop 전달 ([PageView.tsx](file:///Users/jaekanglee/Desktop/Dev/Project/Raven/dashboard/src/routes/PageView.tsx))
- `<EditButton ... title={page.title} .../>` 추가

### 2-3. `api.ts` — updatePage payload 타입 확장 ([api.ts](file:///Users/jaekanglee/Desktop/Dev/Project/Raven/dashboard/src/lib/api.ts))
- `payload: { content: string; title?: string; type?: string; tags?: string[] }` 로 타입 업데이트

### 2-4. 테스트 픽스 ([All-modals-portal.test.tsx](file:///Users/jaekanglee/Desktop/Dev/Project/Raven/dashboard/tests/All-modals-portal.test.tsx))
- `<EditButton>` 호출부에 `title="Test Title"` 추가 (TS 타입 에러 수정)

---

## 3. 검증 결과

| 항목 | 결과 | 비고 |
|---|---|---|
| TypeScript 타입 체크 (`tsc --noEmit`) | **통과** | 에러 없음 |
| 백엔드 테스트 (`pytest tests/ -q`) | **490 passed, 1 skipped** | 회귀 없음 |

---

## 4. 다음 단계

* 제목 외 type / tags 편집도 Side Sheet에 추가하면 완전한 문서 메타데이터 편집 가능

## 5. 문서 상세 그래프 범위/하이라이트 정정 (2026-07-01)

* 문서 상세 페이지의 플로팅 미니맵과 `전체보기` 모달이 **같은 로컬 서브그래프**를 사용하도록 정정했습니다.
  * 대상은 현재 문서 + 직접 연결된 노드, 또는 문서의 `관련` 섹션에 명시된 연결 집합입니다.
  * 더 이상 문서 상세의 `전체보기`에서 보관소 전체 노드가 열리지 않습니다.
* 현재 보고 있는 문서는 미니맵과 확장 그래프 모두에서 **항상 강조 표시**되도록 `GraphCanvas`에 persistent highlight 경로를 추가했습니다.
* 전역 보관소 그래프는 계속 `/graph` 탭의 책임으로 유지됩니다. 즉, **문서 상세 = 로컬 관계**, **그래프 탭 = 보관소 전체** 규칙을 분리했습니다.
* 검증:
  * `npx tsc -b`
  * `npm test -- --run` → `113 passed, 1 skipped`
