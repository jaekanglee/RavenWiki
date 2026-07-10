---
title: Changelog v0.7.166
created: 2026-07-10
updated: 2026-07-10
type: rule
tags: [curator, mcp, api, dashboard, test]
---

# v0.7.166 — Phase 14: AI 기반 초안 작성기(AI-assisted Draft Generator) 파이프라인 및 1-Click 발행 UX 구축

## BLUF
사용자가 특정 주제, 아웃라인, 연관 문서를 선택하면 AI가 임시 공간(`drafts/`)에 초안 문서를 작성하여 린트 예외 혜택(Lint Bypass)을 받게 하고, 대시보드 인라인 편집을 통해 최종 승인 시 `content/`로 정식 승격 및 DB Rebuild를 유발하는 엔드투엔드 AI 초안 작성기 기능을 성공적으로 구현했습니다.

## 무엇을 했는가

| 변경 | 파일 | 효과 |
|---|---|---|
| AI 초안 핵심 모듈 신설 | `raven/core/draft.py` | 사용자 입력 및 관련 위키링크를 기반으로 Frontmatter와 본문을 지닌 마크다운을 자동 빌드하는 프롬프트(Gemini 호출) 및 휴리스틱 fallback, content/ 이동 및 DB Rebuild(commit) 파이프라인 구현 |
| Vault 디렉터리 및 helper 확장 | `raven/core/vault.py` | `Vault` 객체에 `drafts_root` property 추가 및 `ensure_dirs()` 내에서 `drafts/` 임시 공간 자동 생성 보장 |
| Core 패키지 노출 추가 | `raven/core/__init__.py` | 신규 `draft` 모듈을 `draft_module`로 패키지 수준에서 export |
| REST API 엔드포인트 연동 | `raven/api/server.py` | `POST /api/vaults/{name}/drafts/generate`, `POST /api/vaults/{name}/drafts/commit` 추가 및 Payload 모델 정의 |
| MCP 도구 등록 | `raven/mcp/cli.py` | `wiki_generate_draft` 및 `wiki_commit_draft` 도구를 FastMCP 서버에 정식 등록 |
| 대시보드 API 바인딩 추가 | `dashboard/src/lib/api.ts` | `generateDraft` 및 `commitDraft` 연동용 API 헬퍼 함수 추가 |
| 대시보드 라우팅 및 탭 네비게이션 연동 | `dashboard/src/App.tsx`, `dashboard/src/components/Layout.tsx` | 전역 탭 네비게이션 레일(GLOBAL_NAV)에 🤖 "초안 작성기" 메뉴 및 `/draft` 라우트 매핑 추가 |
| 대시보드 AI 초안 작성기 UI 구현 | `dashboard/src/routes/DraftPage.tsx` | 주제/아웃라인/연관 문서 선택 폼(좌) 및 초안 에디터/인라인 편집 영역(우) 2열 레이아웃 구현. 2400ms 토스트 및 1-click Commit 발행 UX 탑재 |
| 통합 유닛 테스트 구축 | `tests/test_draft.py` | Mock API 호출, fallback 생성, drafts to content 이동 및 DB/FTS 반영 확인을 아우르는 테스트 스위트 작성 (pytest 100% 통과) |

## 왜 했는가 (4 저장 신호)
- **재사용 가능성**: 새로운 문서를 기획할 때 수동 작성의 번거로움을 줄이고, 보관소 내 기존 지식을 연결하여 지식의 유기적 밀도를 높일 수 있는 지식 생성의 마중물 역할을 합니다.
- **인수인계**: `drafts/` 공간에 임시 격리해 불완전한 상태에서 린트 스파클링(Lint Warning)을 피하면서 점진적으로 문서를 보강하고 정식 승격할 수 있도록, 기계와 인간 협업의 중간 완충 지대를 제공합니다.
- **실패/리스크 기록**: API Key가 없는 오프라인 환경 등에서도 정상적으로 작동하고 테스트가 보장될 수 있도록, 마크다운 뼈대 및 위키링크를 자동 매칭하여 초안을 생성하는 정밀한 Heuristic Fallback 안전망을 갖추었습니다.

## 검증
- **Pytest**: `tests/test_draft.py` 포함 총 775개 유닛 테스트 케이스 100% 성공 완료.
- **TypeScript**: `make typecheck` 실행 시 React 및 API type signature 정합성 100% 통과 완료.
