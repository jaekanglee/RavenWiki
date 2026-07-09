---
title: Changelog v0.7.147
created: 2026-07-09
updated: 2026-07-09
type: rule
audience: agent
confidence: high
---

# v0.7.147 — wiki_lint read-only 수렴 패치

## BLUF
`wiki_lint`/lint 운영 경로가 `content/issues/issue-lint-*` 자동 생성과 archive 재스캔으로 수렴하지 않는 문제를 차단했다. lint는 read-only로 되돌리고, `_archive/`는 active lint/index 대상에서 제외했다.

## 무엇을 했는가

| 변경 | 위치 | 효과 |
|---|---|---|
| `_archive/` lint 제외 | `raven/core/lint.py` | `content/**/_archive/**` 페이지가 #1/#10/#15/#17/#20/#21/#22 등으로 재검출되는 루프 차단 |
| `run_all()` read-only화 | `raven/core/lint.py` | lint 실행 중 draft issue 자동 승격/파일 write 제거. `draft_promoted` 응답 키는 호환용 `0` 유지 |
| index builder archive 제외 | `raven/core/index_builder.py` | archived `issue-lint-*`가 `content/_index/issue.md`에 다시 링크되는 문제 차단 |
| cron cleanser issue 생성 opt-in | `scripts/cron-cleanser.py`, `.sh` | 기본 실행은 lint 수집만. legacy 자동 issue 페이지 생성은 `--create-issues` 명시 필요 |
| 회귀 테스트 추가 | `tests/test_lint_read_only_archive.py`, `tests/test_cron_cleanser_contract.py`, `tests/test_index_builder.py` | read-only, archive 제외, explicit issue generation 계약 고정 |

## 왜 했는가
- Hermes 관리자 리포트: `hermes-infra` vault에서 lint 자동 issue page가 118개까지 누적되고 `_index/issue.md`가 31KB로 비대화.
- 원인: lint 결과를 소비하는 `cron-cleanser.py`가 issue page를 생성하고, archive/index가 다시 active graph/lint에 들어와 다음 lint를 악화시킴.
- linter는 remediator가 아니라 read-only 검사여야 한다.

## 검증
- `pytest tests/test_lint_read_only_archive.py tests/test_index_builder.py tests/test_cron_cleanser_contract.py -q` → 9 passed
- `pytest tests/test_lint_read_only_archive.py tests/test_index_builder.py tests/test_cron_cleanser_contract.py tests/test_lint_guide_freshness.py tests/test_lint_log_size.py -q` → 17 passed
- `python -m compileall raven/core/lint.py raven/core/index_builder.py scripts/cron-cleanser.py` → success
