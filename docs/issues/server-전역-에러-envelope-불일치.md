---
title: server.py 전역 에러 응답 envelope 불일치 (3종 혼재)
type: issue
status: resolved
created: 2026-07-05
resolved: 2026-07-30
resolved_in: v0.7.179
tags: [rest, api, dashboard]
source: docs/evaluations/2026-07-04-raven-architecture-evaluation.md (B#17)
related_pr: v0.7.68 (changelog-v0.7.67.md 남은 백로그 #4 — REST 관례 정리)
aliases: [server-error-envelope-unification]
---

# server.py 전역 에러 응답 envelope 불일치 (3종 혼재)

## 요약

평가 문서(B#17)가 지적한 "에러 응답 3종 혼재" 중 `delete_vault`의
200 `{ok:false}` → 409 `HTTPException` 전환은 v0.7.68에서 처리했지만,
`raven/api/server.py` 전체를 보면 나머지 두 패턴이 여전히 혼재한다:

1. `HTTPException(detail=<str>)` — 대부분의 4xx/5xx.
2. `HTTPException(detail=<dict>)` — 예: `verify_vault_bootstrap`이
   `result.to_dict()` 전체를 detail에 담는 경우.
3. 200 OK + `{ok: false, ...}` 바디로 실패를 표현하는 나머지 엔드포인트
   (delete_vault 외에도 몇 곳 더 있을 수 있음 — 전수 조사 필요).

이번 배치는 changelog 백로그 원문에 나온 **delete_vault 1건**만 고쳤고,
"server.py 전역 에러 envelope 통일"이라는 더 넓은 범위는 범위 밖으로
남겨뒀다.

## 위치

- `raven/api/server.py` 전체 — grep `HTTPException(` vs `{"ok": False`
  패턴으로 전수 조사 필요.
- 소비처: `dashboard/src/` 내 각 컴포넌트의 fetch 에러 처리 코드 —
  현재도 파일마다 `data?.detail || data?.error`, `err.detail`, `d.ok`
  체크가 제각각인 상태(`NewVaultWizard.tsx`, `VaultManage.tsx` 등).

## 안 고친 이유 (당시 판단)

- 대시보드 소비 코드와 동시 변경이 필요한 엔드포인트가 몇 개인지
  이번 배치에서 전수 조사하지 않았고, delete_vault 1건 밖의 나머지가
  얼마나 되는지 불명확한 상태에서 "전역 통일"을 선언하면 범위가
  무제한으로 커질 위험.
- changelog 백로그 원문도 "REST 관례 정리(...vault delete 거부의
  200→409화)"까지만 구체적으로 명시했고, 그 이상은 "동시 변경 필요해
  리스크 대비 낮은 가치로 유예"라 명시.

## 제안

1. `raven/api/server.py`에서 `{"ok": False` 리턴 패턴 전수 grep으로
   목록화 (delete_vault 외 몇 건인지 먼저 파악).
2. 각 건이 실제로 "에러"인지(4xx로 전환 대상) vs "정상 응답의 일부로서의
   실패 플래그"(전환 불필요)인지 분류.
3. 대시보드 쪽에 공용 에러 파싱 헬퍼(예: `parseApiError(res, body)`)를
   먼저 만들어 각 컴포넌트의 제각각인 `data?.detail || data?.error` 류
   코드를 단일화한 뒤, 백엔드 전환을 단계적으로 진행하면 "동시 변경"
   리스크를 줄일 수 있다.

## 해결 (v0.7.179)

7개 사이트를 전환/보존으로 분류. git status·diff·log rotate 전환, dead `_err()` 제거.

검증: `tests/test_v0_7_179_rest_convention.py`, `tests/test_v0_7_179_link_scan_injection.py`, `dashboard/tests/Workspace.git-error.test.ts`.
