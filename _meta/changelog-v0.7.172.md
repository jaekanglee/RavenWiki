---
title: Changelog v0.7.172
created: 2026-07-13
updated: 2026-07-13
type: rule
tags: [mcp, log, lite-bootstrap]
---

# v0.7.172 — 사람이 읽는 외부 에이전트 작업 이력

## BLUF
외부 에이전트의 MCP 문서 변경이 경로·건수 덤프 대신, 무엇을 왜 바꿨는지 읽히는 작업 이력으로 남도록 `summary`와 `reason` 기록 규약을 추가했습니다.

## 변경

| 영역 | 변경 | 효과 |
|---|---|---|
| MCP `wiki_update` | 선택 입력 `summary`, `reason` 추가 | 헤더에는 사람이 읽는 변경 요약, detail에는 변경 이유 기록 |
| Lite bootstrap | `PROJECT-WORKFLOW.md` §2.1 작업 이력 규약 추가 | 새 vault의 외부 에이전트가 기록 기준을 바로 확인 |
| log 템플릿 | 사람 중심 제목·감사 정보 분리 안내 | 새 vault의 `log.md` 시작 규약 일관화 |
| 검증 | 요약·이유 기록 및 bootstrap 동기화 회귀 테스트 | 기존 actor·idempotency 동작 유지 |

## 왜 했는가

- **인수인계**: 사람이 `log.md`만 읽고도 작업 의도와 결과를 파악할 수 있습니다.
- **실패/리스크 기록**: 경로·카운트 중심 로그가 반복되어 실제 변경 판단을 가리는 문제를 방지합니다.

## 검증

- `scripts/.venv/bin/python -m pytest tests/test_mcp_write_provenance.py tests/test_vault_create.py -q`
- `scripts/.venv/bin/python -m compileall -q raven/mcp`
- `git diff --check`
