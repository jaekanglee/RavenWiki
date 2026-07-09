# Changelog v0.7.153 — Issue Status & Comments Management & Layout Refactoring

> **BLUF**: `type: issue` 문서의 생명주기를 추적하기 위해 frontmatter `issue_status` 필드를 정의하고, 대시보드 상단 헤더 영역(관련 링크 칩 아래)에 딱 필요한 전환 드롭다운으로만 간소화하여 배치했습니다. 또한 피드백 댓글의 수정(편집) 및 삭제 API 엔드포인트를 구현하여 대시보드 상에서 개별 댓글 관리를 가능하게 했으며, 댓글 메타데이터(시간, 작성자)를 2줄 형태로 구성하고, 백링크 패널을 피드백 입력 영역 아래로 수직 배치하도록 개편했습니다.

이전 changelog: `_meta/changelog-v0.7.152.md`

---

## §0 — 묶음 메타

| 항목 | 값 |
|---|---|
| 묶음 | Issue Status & Comments Management |
| 범위 | v0.7.153 (단일 사이클) |
| 기간 | 2026-07-09 |
| 시작 트리거 | 사용자 명시: "이슈 상태 헤더 칩 밑으로 이동, 피드백 댓글 최신순 정렬 및 수정/삭제 기능 추가, 백링크 수직 배치, 메타 데이터 2줄로 쪼개기" |
| 종료 트리거 | tsc 통과 + pytest 736 passed + vite build 통과 |
| 정책 변경 | 1 — `type: issue` 에 `issue_status` 데이터 계약 추가 |
| ADR 동반 | 0 — SCHEMA 갱신으로 반영 |

## §1 — 무엇을 했나

### 백엔드 (FastAPI Server)

`raven/api/server.py`:
- `PageCreate` 와 `PageUpdate` Pydantic 모델에 `extra_meta` 필드를 추가하여 frontmatter 임의 메타데이터 수정/저장을 지원.
- `create_page` 및 `update_page` API 핸들러에서 payload로 전달된 `extra_meta`를 core `write_page` contract에 전달하도록 위임.
- `add_page_feedback` API 엔드포인트 수정:
  - 타임스탬프 포맷을 로컬 시간 기반 `YYYY-MM-DD HH:MM` 형식으로 변경 (T, Z 같은 ISO 포맷 배제).
  - 피드백 추가 시 대상 페이지의 `type`이 `issue`인 경우 자동으로 `issue_status` 필드를 `edit_requested`로 변경.
  - Python `typing.Any` 누락으로 인한 Pydantic User Error 핫픽스 (상단 import 추가).
- **[신규] 피드백 개별 댓글 편집 및 삭제 API 추가**:
  - `FeedbackUpdatePayload` Pydantic 모델 정의.
  - `DELETE /api/vaults/{name}/pages/{slug:path}/feedback/{index}`: 특정 인덱스의 피드백 댓글 라인을 파싱하여 파일 본문에서 완전 삭제.
  - `PUT /api/vaults/{name}/pages/{slug:path}/feedback/{index}`: 특정 인덱스의 피드백 댓글 텍스트 내용을 인라인으로 편집 및 수정하여 저장.

### 프론트엔드 (Dashboard React App)

`dashboard/src/types.ts`:
- `Page` 인터페이스에 선택적 필드로 `issueStatus?: string` 정의.

`dashboard/src/lib/api.ts`:
- `createPage` 및 `updatePage` API 클라이언트에 `extra_meta?: Record<string, any>`를 넘길 수 있도록 시그니처 확장.
- **[신규]** `deletePageFeedback(vault, slug, index)` 및 `updatePageFeedback(vault, slug, index, payload)` API 헬퍼 함수 구현.

`dashboard/src/components/BacklinksPanel.tsx`:
- `vertical?: boolean` 속성 지원 추가. 수직 배치 시 sticky를 해제하고, 상단 border 및 static 포지션, 마진을 적용하여 수직 흐름에 자연스럽게 녹아들도록 스타일링 개선.

`dashboard/src/routes/PageView.tsx`:
- `splitFeedbackSection` 헬퍼 함수 추가: Markdown 본문에서 피드백 댓글을 객체 배열로 분리 파싱.
- `parsedData` useMemo를 통한 연쇄 파싱(본문 / 관련 링크 / 피드백 댓글 분리).
- `InlineMarkdownEditor`의 `viewContent`에 피드백이 제거된 본문만 전달하여 렌더링.
- **상태 선택 UI 개선**: 기존 full width 패널을 제거하고, 상단 header 영역(관련 문서 칩 아래)에 인라인 미니 `select` 드롭다운으로 딱 전환 버튼만 배치.
- **피드백 댓글 관리 UI 탑재**:
  - 피드백 댓글들을 피드백 입력 폼 바로 밑에 최신순(내림차순) 리스트로 렌더링.
  - 각 피드백 댓글 우측에 **[편집] / [삭제]** 버튼 추가 및 인라인 편집 텍스트 영역 활성화.
  - 피드백의 메타데이터(시간, 액터)를 **2줄 레이아웃 (위: 시간, 아래: 괄호친 작성자)** 으로 표시.
- **백링크 배치 개편**: 백링크 `<BacklinksPanel>` 을 우측 컬럼에서 피드백 입력 및 댓글 영역 아래로 수직 배치 (`vertical={true}`).

`dashboard/src/components/NewIssueButton.tsx`:
- 신규 이슈 생성 시 기본 `issue_status` 값을 `"open"`으로 설정하여 frontmatter에 주입.

### 정책 & 스키마 문서

`_meta/SCHEMA.md` & `raven/core/templates/agent/SCHEMA.md`:
- YAML Frontmatter 규약 예시에 `issue_status: open | feedback_done | edit_requested | closed` 추가.
- `Issue Status 4종` 섹션을 신설하여 상태의 의미와 트리거 명기.
- `issue` 타입 문서의 상태 템플릿 설명에 `issue_status` 추가.

## §2 — 변경 안 한 것

- `status` 머신 (`draft | current | stale | contested | archived`)의 전이 규칙 자체는 그대로 유지.
- `type: decision` 등 `issue` 타입이 아닌 다른 유형에 대한 데이터 스키마는 보존.

## §3 — 검증

```text
make typecheck   → cd dashboard && npx tsc -b --noEmit (통과)
make test        → pytest 736 passed, 1 skipped, 1 warning (통과)
npm run build    → vite build (dist/assets/index.js 빌드 성공)
```

## §4 — 4 저장 신호

| 신호 | 충족 |
|---|---|
| 재사용성 | 이슈 상태 및 수정 피드백 자동화는 모든 vault의 `type: issue` 큐레이션 시 재사용 가능한 인프라가 됨. |
| 인수인계 | 에이전트가 큐레이팅할 때 `issue_status` 필드를 보고 적절히 수정요청(`edit_requested`)에 대응할 수 있게 됨. |
| scope/provenance | 로컬 시간 기반의 명료한 피드백 이력과 frontmatter issue_status 전이로 추적성 강화. |
| 실패/리스크 기록 | Pydantic validation User Error 방지를 위한 explicit Any import 및 extra_meta 통합 검증. |
