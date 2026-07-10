---
title: Lint 체크 레지스트리 단일화 (대시보드-백엔드 동기화)
created: 2026-07-11
type: rule
audience: agent
confidence: high
---

# Lint 체크 레지스트리 단일화 (대시보드-백엔드 동기화)

## BLUF

`raven/core/lint.py`는 현재 23개 체크(#1-#23)를 실행하지만, CLI(`raven lint summary`,
`raven lint check`)와 대시보드(`LintPage.tsx`)는 각자 체크 이름/개수를 하드코딩해
14개(대시보드) 또는 13개(CLI summary)까지만 표시하는 drift 버그가 있다. `lint.py`에
`CHECK_REGISTRY` 단일 딕셔너리를 두고 API/CLI/대시보드가 전부 이를 참조하도록 만들어
근본 원인을 제거한다.

## 배경 — 현재 문제

- `dashboard/src/routes/LintPage.tsx`: `CHECK_NAMES` 상수가 `#1`~`#14`만 정의,
  체크별 분포 차트와 필터 드롭다운도 `Array.from({length:14},...)`로 하드코딩.
  `#15`~`#23` 이슈는 하단 이슈 리스트에는 뜨지만 차트/필터/이름 표시에서 누락됨.
- `raven/cli/__main__.py` `lint summary`: `range(1,14)` 루프로 13개까지만 바 차트 표시.
- `raven/cli/__main__.py` `lint check`: `_CHECK_ID_TO_NAME` 매핑이 `#1`과 `#3`을
  둘 다 `"orphans"`로 잘못 매핑(복사 실수)하고 있고, `#2`, `#14`~`#23`이 아예 빠져있음.
- 세 곳 모두 새 체크가 `lint.py`에 추가될 때마다 수동으로 맞춰야 했고, 실제로
  맞춰지지 않은 채 방치된 상태 (v0.5.1 "12개" → 현재 23개까지 여러 차례 증가하며
  각 표면이 서로 다른 시점에 멈춰있음).

## 설계

### 1. 백엔드 — `raven/core/lint.py`

새 모듈 레벨 상수 `CHECK_REGISTRY: dict[str, dict]` 추가. 각 항목은
`{"name": "<한글 표시명>", "fn": "<check_* 함수명 또는 None>"}`.

```python
CHECK_REGISTRY: dict[str, dict] = {
    "#1":  {"name": "깨진 위키링크", "fn": None},
    "#2":  {"name": "깨진 의도 링크 오탐", "fn": None},
    "#3":  {"name": "누락된 위키링크", "fn": None},
    "#4":  {"name": "고아 문서", "fn": "check_orphans"},
    "#5":  {"name": "모순 감지", "fn": "check_contradictions"},
    "#6":  {"name": "신뢰도 낮음", "fn": "check_confidence_low"},
    "#7":  {"name": "오래된 문서", "fn": "check_stale"},
    "#8":  {"name": "문서 길이 초과", "fn": "check_page_size"},
    "#9":  {"name": "핵심 분류 밖 태그", "fn": "check_tag_audit"},
    "#10": {"name": "frontmatter 완전성", "fn": "check_frontmatter_completeness"},
    "#11": {"name": "index 완전성", "fn": "check_index_completeness"},
    "#12": {"name": "로그 크기 과다", "fn": "check_log_size"},
    "#13": {"name": "인지 거버넌스", "fn": "check_cognitive_governance"},
    "#14": {"name": "계층 무결성", "fn": "check_tier_integrity"},
    "#15": {"name": "slug-title 매칭", "fn": "check_slug_title_1to1"},
    "#16": {"name": "vault 성장률 이상", "fn": "check_vault_growth_rate"},
    "#17": {"name": "중복 제목 후보", "fn": "check_duplicate_title"},
    "#18": {"name": "감사 위반 패턴", "fn": "check_audit_violation_pattern"},
    "#19": {"name": "가이드 최신성", "fn": "check_guide_freshness"},
    "#20": {"name": "플레이스홀더 텍스트", "fn": "check_placeholder_text"},
    "#21": {"name": "맥락 없는 위키링크", "fn": "check_contextless_wikilinks"},
    "#22": {"name": "저널 요약 완전성", "fn": "check_journal_summary_completeness"},
    "#23": {"name": "의미 관계 무결성", "fn": "check_semantic_relations"},
}
```

`#1`~`#3`은 `_legacy_link_issues()`(link_module 결과 변환)로 생성되어 개별
`check_*` 함수가 없으므로 `fn: None`.

`run_all()`의 반환 dict에 한 줄 추가:

```python
"checks": {cid: meta["name"] for cid, meta in CHECK_REGISTRY.items()},
```

### 2. API — `raven/api/server.py`

- `GET /api/vaults/{name}/lint` 응답에 `"checks": result.get("checks", {})` 추가.
- `GET /api/vaults/{name}/lint/summary` 응답에 동일하게 `"checks"` 추가.
- 두 엔드포인트 모두 added-only 변경 — 기존 필드 제거/이름 변경 없음, 하위 호환 유지.
- 오래된 `"#1-#12"` 등 Query 설명 문구는 일반적인 문구로 정리(수치 하드코딩 제거).

### 3. CLI — `raven/cli/__main__.py`

- `lint summary`: `for cid in [f"#{i}" for i in range(1, 14)]` →
  `for cid in sorted(lint_module.CHECK_REGISTRY, key=lambda c: int(c[1:]))` 로 교체.
  모든 체크가 항상 표시되며(0건이어도), 이름은 표시하지 않고 기존처럼 id+bar만
  출력(기존 포맷 유지, 범위만 수정).
- `lint check <id>`: `_CHECK_ID_TO_NAME` 딕셔너리(버그 있는 수동 매핑) 제거하고
  `lint_module.CHECK_REGISTRY.get(check_id, {}).get("fn")`으로 조회.
  - `fn`이 `None`이면 (즉 `#1`-`#3`): "이 check는 link_module 기반이라 개별 실행을
    지원하지 않습니다 — `raven link check` 사용" 안내 후 `exit(1)`.
  - `check_id`가 레지스트리에 없으면 기존과 동일하게 unknown 에러.
- `lint run`/`lint check`/`lint summary`의 도움말 문구 중 하드코딩된 개수
  ("#1-#12", "18개" 등)는 실행 시점 `len(lint_module.CHECK_REGISTRY)`를 반영하도록
  동적 문자열로 교체(정적 docstring은 근사치로 남겨도 무방, `--help` 텍스트가
  아닌 echo 출력부만 동적화).

### 4. 대시보드 — `dashboard/src/lib/api.ts`, `dashboard/src/routes/LintPage.tsx`

- `LintSummary`/`LintResult` 타입에 `checks?: Record<string, string>` 필드 추가.
- `LintPage.tsx`의 하드코딩된 `CHECK_NAMES` 상수 제거, 대신
  `const names = summary?.checks ?? {}`로 대체.
- 체크별 이슈 분포 차트와 체크 필터 `<select>` 두 곳의 `Array.from({length:14}, ...)`
  루프를 `Object.keys(names).sort((a,b) => Number(a.slice(1)) - Number(b.slice(1)))`
  기반 순회로 교체.
- 헤더 subtitle "14개 lint check 결과 요약입니다." → 동적 개수
  (`${Object.keys(names).length}개 lint check 결과 요약입니다.`)로 교체.
- **범위 밖**: auto-fix/quick-fix UI는 추가하지 않는다. 기존
  `dashboard/tests/LintPage.no-quickfix.contract.test.ts` 계약을 그대로 유지.

### 5. 테스트

- `tests/`에 회귀 테스트 신규 추가: `CHECK_REGISTRY`의 키 집합이 `run_all()`이
  실제로 생성하는 고유 `id` 집합의 상위집합(superset)인지 확인 — 새 체크 함수가
  추가됐는데 레지스트리 등록을 빠뜨리면 이 테스트가 실패해 즉시 드러나게 함.
- 기존 `tests/test_lint_v2.py` 등 lint 관련 테스트는 응답 shape의 added-only
  변경이므로 수정 없이 통과해야 함.
- `lint check` CLI의 `fn=None`(#1-#3) 안내 메시지 동작을 검증하는 테스트 1개 추가.

## 데이터 흐름 요약

```
raven/core/lint.py: CHECK_REGISTRY (단일 소스)
        │
        ├─ run_all()["checks"] 로 embed
        │
        ├─→ CLI (같은 프로세스, 직접 참조)
        │
        └─→ API 응답 (get_lint, get_lint_summary)
                │
                └─→ Dashboard (fetch 후 렌더링에 활용, 하드코딩 제거)
```

향후 24번째 체크가 추가되면 `CHECK_REGISTRY`에 한 줄만 추가하면 CLI/API/대시보드
전부가 자동으로 반영한다.

## 영향 범위

파일 5개 수정 (`raven/core/lint.py`, `raven/api/server.py`, `raven/cli/__main__.py`,
`dashboard/src/lib/api.ts`, `dashboard/src/routes/LintPage.tsx`) + 신규 테스트 파일/케이스
추가. 신규 진입점 없음, API 응답 필드는 추가만 하므로 ADR 불필요 (AGENTS.md §8 대상
아님). auto-fix UI, per-check enable/disable 토글, threshold 설정 UI 등은 이번 스코프에
포함하지 않는다(향후 별도 스펙).
