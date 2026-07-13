---
title: Changelog v0.7.171
created: 2026-07-13
updated: 2026-07-13
type: rule
tags: [dashboard, drafts, cleanup, mcp, api]
---

# v0.7.171 — 미사용 초안 템플릿 기능 제거

## BLUF
사용되지 않던 vault별 초안 템플릿 편집 기능을 Dashboard·API·MCP·초안 생성 경로에서 제거하고, 초안 생성은 고정된 기본 구조만 사용하도록 단순화했습니다.

## 변경

| 영역 | 변경 | 효과 |
|---|---|---|
| Dashboard | `템플릿` 전역 탭·라우트·편집 화면 삭제 | 핵심 탐색·편집 표면만 유지 |
| API | `/api/vaults/{name}/templates` 읽기·쓰기 엔드포인트 삭제 | `_templates/` 생성·저장 경로 제거 |
| Draft/MCP | `draft_type` 및 사용자 템플릿 주입 제거 | 초안은 기본 `concept` 구조로 일관되게 생성 |
| 테스트 | 템플릿 기능 테스트 삭제, 부재·기본 fallback 회귀 가드 추가 | 제거 상태와 초안 생성 유지 동시 검증 |

## 왜 했는가

- **재사용 가능성**: 실사용 없는 설정 표면보다 단순한 기본 초안 구조가 반복 사용에 적합합니다.
- **인수인계**: Dashboard·REST·MCP가 동일하게 템플릿 기능을 제공하지 않는 상태로 정합됩니다.
- **실패/리스크 기록**: 더 이상 `_templates/`가 생성·주입되어 예상과 다른 초안 구조를 만들지 않습니다.

## 검증

- `tests/test_draft.py` — 기본 fallback 및 템플릿 기능 부재 회귀 가드
- `tests/test_phase16.py` — 삭제된 템플릿 API 테스트 제거 후 기존 초안 목록·advice 검증
- Dashboard TypeScript·Vitest 및 관련 Python 회귀 스위트는 본 변경과 함께 실행
