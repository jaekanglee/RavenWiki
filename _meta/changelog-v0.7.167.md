---
title: Changelog v0.7.167
created: 2026-07-10
updated: 2026-07-10
type: rule
tags: [draft, template, conflict, api, dashboard, mcp, test]
---

# v0.7.167 — Phase 15: 타입별 초안 템플릿 연동 + Multi-author 충돌 감지 및 UX 개선

## BLUF
`_templates/{type}.md` 파일이 vault에 존재하면 AI 프롬프트에 자동 주입되어 타입별 일관된 구조로 초안을 생성하고, 같은 slug 문서가 `content/`에 이미 존재할 때 Advisory Lock 기반 충돌 감지(`conflict=True`, HTTP 409)와 "덮어쓰기 vs 비교 병합" 선택 UX를 구현했습니다.

## 무엇을 했는가

| 변경 | 파일 | 효과 |
|---|---|---|
| 타입별 템플릿 참조 | `raven/core/draft.py` — `generate_draft()` | `draft_type` 파라미터 신설. `vault/_templates/{type}.md`가 존재하면 내용을 읽어 AI 프롬프트에 "구조 참조 템플릿"으로 주입. Fallback 경로에서도 템플릿 본문 뼈대를 반영. |
| Advisory Lock 적용 | `raven/core/draft.py` — `generate_draft()` + `commit_draft()` | 초안 쓰기/커밋 모두 `lock_for_file()` 로 보호. 타임아웃 시 `ok=False` 에러 반환. |
| 충돌 감지 | `raven/core/draft.py` — `commit_draft()` | `overwrite` 파라미터 신설(기본 `False`). 동일 slug가 `content/`에 존재하면 `conflict=True` + `existing_content` + `draft_content` 반환. 기존 파일과 draft 파일 모두 보존. |
| API 페이로드 확장 | `raven/api/server.py` | `DraftGeneratePayload.draft_type` 필드 추가. `DraftCommitPayload.overwrite` 필드 추가. 충돌 시 HTTP 409 + JSON 본문 반환 (`JSONResponse(409, content=res)`). |
| MCP 도구 시그니처 갱신 | `raven/mcp/cli.py` | `wiki_generate_draft` — `draft_type` 파라미터 추가 및 템플릿 연동 설명 보완. `wiki_commit_draft` — `overwrite` 파라미터 추가 및 충돌 동작 설명 보완. |
| Dashboard API 바인딩 확장 | `dashboard/src/lib/api.ts` | `generateDraft` — `draft_type` 페이로드 필드 추가. `commitDraft` — `overwrite` 페이로드 필드 추가 및 HTTP 409 핸들링(→ `DraftConflictResult`). `DraftConflictResult` 인터페이스 신설. |
| Dashboard UX 고도화 | `dashboard/src/routes/DraftPage.tsx` | `SelectField` 기반 문서 타입 선택기(9종) 추가 — 선택된 타입에 대응하는 템플릿 경로 힌트 표시. 충돌 감지 모달(`<Modal>`) 신설 — Draft vs Existing 버전 비교 탭 + "덮어쓰기 발행" / "취소 — 초안 유지" 액션. |
| Phase 15 테스트 추가 | `tests/test_draft.py` | 7개 신규 테스트 (템플릿 없는 fallback, 템플릿 있는 fallback 뼈대 반영, 충돌 감지, overwrite 해소, HTTP 409 API 검증, MCP draft_type/overwrite 소스 검증) 추가. 총 12 케이스 100% 통과. |

## 왜 했는가 (4 저장 신호)
- **재사용 가능성**: `_templates/{type}.md`는 vault 단위로 사용자가 자유롭게 정의하고, 모든 AI 초안 생성에 자동 적용됩니다.
- **인수인계**: 충돌 감지는 멀티 에이전트/멀티 저자 환경에서 묵시적 덮어쓰기로 인한 데이터 손실을 방지하는 중요한 안전망입니다.
- **실패/리스크 기록**: Advisory Lock 타임아웃, 충돌 시 draft 파일 보존, Fallback 경로의 템플릿 활용 — 세 가지 경우 모두 데이터 손실 없이 안전하게 처리합니다.

## 검증
- **Pytest**: `tests/test_draft.py` 12개 케이스 100% 통과.

## 후속 작업 후보
- `_templates/` 하위 파일을 Dashboard에서 편집/관리할 수 있는 Template Editor UI
- Draft 목록 페이지 (`/drafts`) — 현재 격리 중인 초안 목록 + 상태(미발행/충돌) 표시
- MCP `wiki_list_drafts` 도구 추가
