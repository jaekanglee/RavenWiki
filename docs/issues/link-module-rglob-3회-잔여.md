---
title: link_module의 자체 rglob 3회 — lint 캐싱 범위 밖 잔여
type: issue
status: resolved
created: 2026-07-05
resolved: 2026-07-30
resolved_in: v0.7.179
tags: [performance, lint, core]
source: docs/evaluations/2026-07-04-raven-architecture-evaluation.md (B#8)
related_pr: v0.7.68 (changelog-v0.7.67.md 남은 백로그 #3 — lint run_all 스캔 캐싱)
aliases: [link-module-rglob-triplication]
---

# link_module의 자체 rglob 3회 — lint 캐싱 범위 밖 잔여

## 요약

v0.7.68에서 `raven/core/lint.py`의 `run_all()`이 14개 체크가 각각 독립적으로
vault를 rglob(~11회)하고 frontmatter를 재파싱(~6회)하던 중복 I/O를
`_ScanCache`(thread-local, `run_all()` 호출 경계 안에서만 유효)로 제거했다.

하지만 `_legacy_link_issues()`가 호출하는 `link_module.find_broken()`,
`find_missing()`, `find_broken_intent()`(`raven/core/link.py`)는 각자
독립적으로 `vault.content_root.rglob("*.md")` + 파일별 `read_text()`를
수행한다 — 이 3회는 `_ScanCache`의 적용 범위 밖에 남아있다.

## 위치

- `raven/core/link.py:49-127` — `find_broken`, `find_missing`,
  `find_broken_intent` 각각 자체 rglob + read_text 루프.
- `raven/core/lint.py`의 `_legacy_link_issues()`가 이 3개를 순차 호출
  (`run_all()` 1회 = link_module rglob 3회 + `_ScanCache` 적용 대상 rglob 1회
  = 총 4회. 캐싱 전에는 rglob 14회였으므로 이미 상당히 개선됐지만, 완전
  단일화는 아님).

## 안 고친 이유 (당시 판단)

- `link_module`은 `lint.py`와 별도 모듈이고, `find_broken`/`find_missing`/
  `find_broken_intent`는 `slug` 파라미터로 단일 페이지만 조회하는 경로도
  지원하는 공개 API라 시그니처 변경(캐시된 페이지 목록을 주입받는 구조로
  전환) 파급 범위가 lint.py 내부보다 넓음.
- 이미 lint.py 내부 11회 → 1회로 압축한 것이 성능 개선의 대부분을
  차지하고, 남은 3회는 정확성 버그가 아니라 성능 이슈라 리스크 대비
  낮은 가치로 유예.

## 제안

`link_module`의 3개 함수가 공유할 수 있는 "이미 스캔된 페이지 목록 +
텍스트"를 선택적으로 주입받는 파라미터(예: `pages: Optional[list[tuple[str, str]]] = None`)를
추가하고, `lint._legacy_link_issues()`가 `_ScanCache`에 채워둔 목록을
넘겨주는 방식이 시그니처 하위호환(기존 호출자는 `None` = 기존 동작)을
유지하면서 남은 3회 중복도 없앨 수 있는 가장 낮은 리스크의 경로로 보인다.

## 해결 (v0.7.179)

find_* 3종에 `pages` 주입 파라미터 추가. content glob 4회 → 1회.

검증: `tests/test_v0_7_179_rest_convention.py`, `tests/test_v0_7_179_link_scan_injection.py`, `dashboard/tests/Workspace.git-error.test.ts`.
