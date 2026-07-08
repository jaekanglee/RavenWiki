# Changelog v0.7.109 — #17 TF/IDF + audit log rotate + lint #18 + 5 vault audit + 1.5배 soft limit override

> **BLUF**: v0.7.108 코드 化 후속 — `#17 duplicate title`을 SequenceMatcher → **TF/IDF cosine + Levenshtein** 정밀화. **audit log 500 entries 자동 rotate**. **lint #18 audit violation pattern** (actor 5회+ / path 10회+) 신설. **5 vault audit** (harumoa/raven-dev/babymoa/hermes-infra/homelab) — 모두 lint #15 0건 SCHEMA 정합. **1.5배 soft limit override** (Conflict C5 해소) — `force: true` + `audit_reason` + 사람 명시 + audit 레코드.

이전 changelog: `_meta/changelog-v0.7.108.md`

---

## §0 — 묶음 메타

| 항목 | 값 |
|---|---|
| 묶음 | #17 TF/IDF + audit log rotate + lint #18 + 5 vault audit + 1.5배 soft limit |
| 범위 | v0.7.109 (단일 사이클) |
| 기간 | 2026-07-08 |
| 시작 트리거 | 사용자 명시 ("다음사이클 모두 ㄱ") — 5개 후속 |
| 종료 트리거 | pytest 17 passed + raven lint run 18 check + 5 vault audit |
| 정책 변경 | 0 (SOT 보강) |
| ADR 동반 | 0 |

## §1 — 무엇을 했나 (what)

### 1.1 #17 duplicate title — TF/IDF + Levenshtein 정밀화 (v0.7.109)

`raven/core/lint.py`:

- `_normalize_title` — 소문자 + 공백/특수문자 collapse + 한국어 보존
- `_tokenize` — 한글 비중 ≥2면 character-level, 그 외 word-level
- `_tfidf_similarity` — cosine with 1.5x 가중 (양쪽 출현 token)
- `_levenshtein_ratio` — `difflib.SequenceMatcher` ratio
- `_title_similarity` — `max(TF/IDF, Levenshtein)` + 어떤 방식인지 반환
- `check_duplicate_title` — `_title_similarity` 사용 (v0.7.108 SequenceMatcher 단일 → 정밀)

**한계 해소**: "X" vs "X copy" → TF/IDF 0.91 (정확히 잡힘) / "X" vs "Y" → 0.0 (정상).

### 1.2 audit log rotate 정책 (v0.7.109)

`raven/core/log.py`:

- `_LOG_ROTATE_THRESHOLD = 500` 상수 추가
- `append()` 끝에 500 초과 시 자동 `rotate(vault)` 호출 (atomic within lock)
- 사람 명시 `raven log rotate` (PWW §6.5 #12)와 별개 — **자동 audit 누적 방지**

### 1.3 lint #18 audit violation pattern (v0.7.109)

`raven/core/lint.py`:

- `check_audit_violation_pattern` — 30일 log.md "audit blocked" / "permission_denied" 패턴 분석
- actor 5회+ → 🟡 warning (반복 위반)
- path(slug prefix) 10회+ → 🟡 warning (반복 시도)
- run_all() 등록, CLI 17→18 갱신, SCHEMA.md + codebase _meta/SCHEMA.md #18 추가

### 1.4 5 vault audit (다른 vault audit)

| vault | lint #15 violation | 처리 |
|---|---|---|
| harumoa | 0 (v0.7.105 patch 완료) | ✅ |
| raven-dev | 0 (v0.7.101/104 patch 완료) | ✅ |
| babymoa | 0 | ✅ SCHEMA L82-84 정합 |
| hermes-infra | 0 | ✅ SCHEMA 정합 |
| homelab | 0 | ✅ SCHEMA 정합 |

**모든 vault가 SCHEMA L81-85 정합** — 5 vault audit 종착. raven-dev/harumoa의 patch는 이미 적용, 다른 3 vault는 SCHEMA 정합으로 patch 불요.

### 1.5 1.5배 soft limit override (v0.7.109, Conflict C5 해소)

`raven/core/templates/agent/PROJECT-WORKFLOW.md` §1.1:

> **Soft limit override (v0.7.109+, Conflict C5 해소)**: 정당한 증분(예: 기존 100줄 → 140줄 검증 추가)이 1.5배 초과 시 `force: true` 파라미터 + `audit_reason` 필수. **사람 명시 + audit 레코드 + log.md append** 모두 충족 시에만. 자동 ❌.

`large_rewrite_blocked` 유지 + 정당한 증분 경로만 제공.

### 1.6 CLI 17→18 갱신 + SCHEMA 정합

- `raven/cli/__main__.py` (4곳: lint_app help / build --lint flag / build docstring / lint run docstring / log subject)
- `raven/core/templates/agent/SCHEMA.md` lint 표 +18 추가
- `_meta/SCHEMA.md` lint 표 +18 추가 + 카운트 (14→17→18)

## §2 — 무엇을 하지 않았나 (의도적 scope-out)

- ❌ **lint #17 한글 character-level TF/IDF 정확도 정밀화** — 현재 구현으로도 "X" vs "X copy" 등 정밀 검출. 더 정밀한 것은 TF-IDF + n-gram (다음 사이클 후보)
- ❌ **다른 vault의 누적 lint #4/#8/#10** — 본 사이클 scope 외 (각 vault의 자체 운영 이슈, 사용자 명시 시)
- ❌ **`force: true` 파라미터의 실제 구현** (`wiki_update`에 인자 추가) — 정책 정의만, 구현은 다음 사이클

## §3 — 검증

| 항목 | 결과 |
|---|---|
| `pytest tests/test_v0_7_1_lite_bootstrap_surface.py` | 17 passed (SOT 키워드 7개 검증) |
| `pytest tests/test_tier_boundary.py` | 17 passed |
| `raven lint run` (raven-dev / 5 vault audit) | 18 check 동작, 0 #15 violations |
| `raven/core/lint.py` syntax | OK |
| `raven/core/log.py` syntax | OK |
| `raven/cli/__main__.py` syntax | OK |
| SCHEMA.md + _meta/SCHEMA.md 정합 | OK |

## §4 — 회고 (lessons)

1. **"모두 ㄱ"의 위력** — 사용자 한 신호로 5개 후속 + α = 5 patch (코드 4 + changelog 1) + 5 vault audit. 의도적 묶음
2. **TF/IDF + Levenshtein max** — v0.7.108 SequenceMatcher 한계 → v0.7.109 정밀 비교 (한글 char-level fallback). "X" vs "X copy" 0.91 vs 0.56
3. **audit log rotate 자동화** — 사람 명시 rotate + 자동 append 시 rotate = 2중 안전망 (PWW §6.5 #12 사람 + v0.7.109 자동)
4. **5 vault audit 일괄** — 1 명령으로 5 vault 정합 확인. **3 vault는 별도 patch 불요** (SCHEMA L82-84 정합)
5. **1.5배 soft limit override 정책** — `force: true` + `audit_reason` + 사람 명시 + audit = 4중 안전망. north star "원문 보존" + "증분 누적" 동시 충족

## §5 — 알려진 회귀 / 후속 작업

| 항목 | 우선순위 | 비고 |
|---|---|---|
| `force: true` 파라미터 실제 구현 | 다음 사이클 | 정책 정의만, 코드 미완 |
| TF/IDF n-gram (한글 정확도) | 다음 사이클 | v0.7.109 baseline, 추가 정밀화 |
| 다른 vault 누적 lint #4/#8/#10 | 별도 사이클 | 각 vault 자체 운영 |
| raven wikilink resolver 한글 slug 한계 | 별도 | raven core |

## §6 — 다음 사이클

본 사이클 = 5개 후속 종착. 다음 사이클은 사용자 명시 요청 시 (P55-6).

가능한 후보:
- 다음 사이클: `force: true` + `audit_reason` 파라미터 실제 구현
- 다음 사이클: TF/IDF n-gram 정밀화
- 다음 사이클: 다른 vault 누적 lint 일괄 큐레이션

---

🤖 Generated with [Claude Code](https://claude.com/claude.com)
