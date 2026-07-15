---
title: Changelog v0.7.173
created: 2026-07-14
type: rule
tags: [mcp, lite-bootstrap, agent]
---

# v0.7.173 — Raven 계약과 사용자 정책의 분리

## BLUF

Raven의 Lite bootstrap에서 에이전트 운영 정책을 제거하고, 제품이 보장하는 기술 계약만 동기화하도록 분리했습니다.

## 변경

| 영역 | 변경 | 효과 |
|---|---|---|
| Lite bootstrap | `PROJECT-WORKFLOW.md` 대신 `RAVEN-CONTRACT.md` 제공 | 새 vault에는 제품 계약만 주입 |
| 사용자 지침 | 루트 agent instruction 파일 자동 생성·복구 제거 | 운영자 정책을 Raven이 덮어쓰지 않음 |
| guide/freshness | Raven 소유 3종만 조회·diff·검사 | 사용자 정책은 제품 업그레이드와 독립 |
| Dashboard raw 탐색 | raw 디렉터리는 펼치기만 하고 파일만 viewer route로 이동 | 폴더를 파일처럼 요청해 발생하던 404 제거 |
| 호환성 | 기존 `PROJECT-WORKFLOW.md`는 읽기 전용 허용 | 기존 vault의 전환을 비파괴적으로 지원 |

## 검증

- Lite bootstrap, sync, guide, freshness, root instruction 보존 회귀 테스트
- Python compile 및 diff whitespace 검사

## 관련

## v0.7.174 — Plain vault creation and Dashboard cleanup

### BLUF

새 vault는 Raven 정책·에이전트 지침·활동 로그를 주입하지 않는 빈 Markdown workspace로 생성되며, Dashboard에서도 해당 관리 표면을 제거했습니다.

### 변경

- `Vault.create()`와 `POST /api/vaults`가 `content/`과 vault 등록 메타데이터만 생성하도록 변경
- Dashboard 새 vault wizard에서 profile/bootstrap, MCP 안내, 자동 index 문서 생성을 제거
- Dashboard `/guides` route와 guide viewer를 제거하고 Vault 관리 화면을 문서·링크·용량 중심으로 단순화

### 검증

- `pytest tests/test_plain_vault_creation.py tests/test_api.py -q` → 60 passed
- `npx vitest run tests/PlainVaultDashboard.test.ts` → 2 passed
- `npx tsc -b --noEmit` → passed

- [[raven-contract-and-user-agent-policy-boundary]] — 소유권 경계 결정
