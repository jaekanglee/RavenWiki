---
title: "POST /api/vaults/clone — vaults/create와 동일한 REST 네이밍 위반"
type: issue
status: open
created: 2026-07-05
tags: [rest, api, dashboard]
source: docs/evaluations/2026-07-04-raven-architecture-evaluation.md (B#17)
related_pr: v0.7.68 (changelog-v0.7.67.md 남은 백로그 #4 — REST 관례 정리)
---

# POST /api/vaults/clone — vaults/create와 동일한 REST 네이밍 위반

## 요약

v0.7.68에서 `POST /api/vaults/create` → `POST /api/vaults`로 리네임하며
"동작이 URL 경로 세그먼트로 노출되는" RESTful 위반을 고쳤다. 그런데
`raven/api/server.py`의 형제 엔드포인트 `POST /api/vaults/clone`은
**동일한 패턴의 위반**(`clone`이 동작이자 경로 세그먼트)이 그대로
남아있다. 이번 배치에서는 백로그 원문이 `vaults/create`만 명시해
범위 밖으로 두었다.

## 위치

- `raven/api/server.py` — `@app.post("/api/vaults/clone")` 데코레이터가
  붙은 clone 핸들러.
- 소비처: dashboard 프론트엔드에서 이 경로를 호출하는 지점(대시보드
  vault 관리 UI의 clone 액션) — 리네임 시 프론트도 동시 수정 필요.

## 안 고친 이유 (당시 판단)

- changelog v0.7.67의 "남은 백로그" 원문이 `POST /vaults/create` 네이밍만
  명시했고, `/vaults/clone`은 언급되지 않아 승인된 변경 경계 밖.
- REST 규칙상 정석은 소스 vault를 식별하는 `POST /api/vaults/{name}/clone`
  형태(clone 대상 body에 새 이름을 담는 방식)로 옮기는 것인데, 이는
  `/vaults/create`보다 요청 바디/경로 파라미터 재설계가 더 필요해
  리스크가 더 크다.

## 제안

`POST /api/vaults/{name}/clone`(경로 파라미터로 소스 vault 식별) 또는
최소한 `POST /api/vaults:clone`류 관례로 정리. 프론트 clone 액션 호출부
동시 수정 필수. `/vaults/create`를 고칠 때 썼던 것과 동일한 패턴
(테스트 sed 치환 + 프론트 fetch URL 갱신)을 재사용 가능.
