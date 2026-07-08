---
title: Changelog v0.7.117
created: 2026-07-08
updated: 2026-07-08
type: rule
audience: agent
confidence: high
---

# v0.7.117 — log.md extra dict 가독성 + dashboard writeLog UX + run_all graceful degrade

## 무엇을 했는가

### Fix A — `log.append()` `extra` dict 가독성 (`raven/core/log.py:232-244`)

- **문제**: `extra={"by_check": json.dumps(result["by_check"], ensure_ascii=False)}` 로 dict를 통째 json.dumps한 뒤 entry로 박힘 → `## [date] lint | ...\n- by_check: {"#1": 168, ...}` 한 줄. grep이 어렵고 사람 눈으로 count 분포도 안 읽힘.
- **수정**: `log.append()` 의 `extra` 처리 루프가 value 타입 분기.
  - `dict` → `"#1=168, #4=1, ..."` 펼침
  - `str` (기존 caller 모두 이 형태) → 기존 그대로 `"{k}: {v}"`
- **회귀 가드**: `git grep 'extra=\\s*\\{'` 으로 모든 caller 사전 매핑 — 모두 `{"key": str(...) }` 형태라 회귀 0.

Before:
```
## [2026-07-08] lint | lint 12개 (168C/105W/599I)
- by_check: {"#1": 168, "#4": 1, "#8": 1, ...}
```
After:
```
## [2026-07-08] lint | lint 12개 (168C/105W/599I)
- by_check: #1=168, #4=1, #8=1, ...
```

### Fix C — Dashboard writeLog auto-reset 제거 (`dashboard/src/routes/LintPage.tsx:85-91`)

- **문제**: `setLastWriteResult(...)` 직후 `setWriteLog(false)` 자동 reset → 사용자가 매번 매번 체크해야 재호출마다 log 기록. 1-cycle에 1번 누락되는 off-by-one UX 결함.
- **수정**: 자동 reset 제거. `lastWriteResult` 메시지는 보여주고 checked 상태는 사용자 의도 존중.

### Fix D — `lint.run_all()` graceful degrade (`raven/api/server.py:1991-2015`)

- **문제**: `lint_module.run_all(v)` 자체가 어느 check에서 RuntimeError를 raise하면 응답은 500 → 전체 lint API fail. write_log 분기는 catch 안 됨.
- **수정**: `try / except`로 감싸고 `ok=False + empty counts + issues=[] + error="<Type>: <msg>"` 반환. **log fail ≠ lint fail 분리 보장**.

## 왜 그렇게 했는가 (§5 4 신호)

- **재사용 가능성**: `extra` 포맷 contract는 모든 log.append caller가 의존 (MCP/CLI/API 4+ 곳) — 한번 고치면 모든 표면이 정확
- **인수인계 필요성**: 다음 운영자가 log.md grep `^## \[.*\] lint` 시 `by_check` 가독성으로 분포 즉시 파악 가능
- **scope/provenance 추적**: AGENTS.md §15 "인간 중심 가독성" 위배 회귀 정정. backend 안정성은 §9 정합.
- **실패/리스크 기록**: silent run_all raise는 다음 운영자가 "lint 페이지 갑자기 500" 진단 비용 ↑ — graceful degrade + stderr log로 단서 남김

## 검증

- 3 파일 `py_compile` clean (raven/core/log.py, raven/api/server.py, raven/core/db.py)
- `dashboard tsc -b --noEmit` exit 0
- **Round-trip Test 1**: dict extra → `by_check: #1=168, #4=1, #8=1` ✅
- **Round-trip Test 2**: str extra 회귀 → `db: /path/to/wiki.db / returncode: 0` ✅
- **Round-trip Test 3**: 실제 `harumoa/log.md`에 두 entry 모두 정상 기록 ✅
- Fix D: `server.py` AST clean. 코드 경로상 lint 응답 500 → 200(ok=false) 전환은 다음 lint 페이지 직접 호출 시 확인 가능

## 회귀 영향

| 영향 영역 | 결과 |
|---|---|
| 기존 string extra caller (`db.py:62`, `cli/__main__.py:1533` 등 4곳) | 회귀 0 (str 분기 유지) |
| log.md parser (`log.py:130+ _parse_entry _DETAIL_RE`) | `- key: value` 동일 (key/value 형식만 다름) |
| dashboard writeLog reset | 의도 UX 변경 (off-by-one 사라짐) |
| API 500 가능성 | 200 + ok=false 로 graceful degrade |

## 다음 사이클 후보

- json import unused 가능성 (`server.py:14`) — 정리는 별도
- dashboard rebuild 버튼 옵션: 성공 후 자동 lint refetch (현재 `res.lint` 필드 있으면 자동 적용, 없으면 그대로)
