# raven v0.7.53 — 대시보드 MD 편집/삭제 버튼 복구 및 그래프 fallback 보정

> **핵심**: PageView 컴포넌트의 `related.body` 조건 분기로 인해 인라인 편집기(InlineMarkdownEditor)가 아닌 fallback 뷰어(MarkdownView)가 항상 렌더링되면서 편집/삭제가 봉인되었던 문제를 해결하고, wiki.db가 없는 환경이나 fallback 동작 시 rglob으로 링크 그래프 수집 중 짧은 slug가 보정되지 않아 모든 문서가 고아 처리되던 결함을 수정했습니다.

릴리스 일자: 2026-07-02
이전: v0.7.52

---

## 1. 변경 사항

### 1-1. MD 인라인 에디터(InlineMarkdownEditor) 통합 및 삭제 기능 복구
* [dashboard/src/components/InlineMarkdownEditor.tsx](file:///Users/jaekanglee/Desktop/Dev/Project/Raven/dashboard/src/components/InlineMarkdownEditor.tsx)
  * `viewContent` 프로퍼티를 추가 지원하여 뷰 모드일 때 "관련" 섹션 및 중복 제목 등이 제거된 가공 본문(`related.body`)을 렌더링하도록 개선하되, 편집 모드에서는 파일 전체 내용을 보존해 안전하게 편집할 수 있도록 분리했습니다.
* [dashboard/src/routes/PageView.tsx](file:///Users/jaekanglee/Desktop/Dev/Project/Raven/dashboard/src/routes/PageView.tsx)
  * `related.body` 존재 여부와 무관하게 항상 `InlineMarkdownEditor`를 렌더링하도록 통합하여 대시보드에서 편집(Cmd+E) 및 삭제 버튼이 상시 노출되도록 복구했습니다.
  * 기존에 단순 화면 복귀만 하던 더미 `onDelete` 콜백을 보완하여, 실제 `deletePage` API를 호출해 백엔드에서 삭제 및 아카이빙 처리가 진행되도록 정상화했습니다.

### 1-2. 그래프 rglob fallback 내 짧은 slug 보정 로직 추가 및 예외 로깅
* [raven/api/server.py](file:///Users/jaekanglee/Desktop/Dev/Project/Raven/raven/api/server.py)
  * `vault_graph` API 실행 중 `wiki.db` 로드가 실패해 fallback rglob 분기를 타게 되는 경우, wikilink가 짧은 형태(`[[features]]` 등)일 때 이를 실제 노드 리스트의 긴 slug(`content/concept/features` 등)와 비교/보정하는 로직을 추가했습니다. 이로써 `wiki.db`가 없거나 빌드 전인 vault에서도 정상적으로 연결선(edge)이 수립되어 고아문서 오판을 방지합니다.
  * `wiki.db` 로드 실패 예외를 로깅(sys.stderr)해 silent failure를 방지하고 디버깅 가능성을 향상했습니다.

---

## 2. 검증 결과

### 2-1. 빌드 및 테스트 검증
* Python 백엔드 테스트 세트 검증 완료: `542 passed, 2 skipped` (`pytest tests/ -q` 통과)
* 프론트엔드 정적 타입 체크 및 빌드 검증 완료: `tsc -b && vite build` 에러 없이 빌드 통과

---

## 3. 다음에 가능한 것 (후속 작업)
* **API 예외 응답 세분화**: fallback 동작의 원인이 된 database exception 시 silent fallback 대신 에러 모니터링 경고를 dashboard UI 혹은 로그 대시보드에 surface하는 방안 검토.
