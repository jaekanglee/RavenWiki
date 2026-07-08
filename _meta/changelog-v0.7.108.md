# Changelog v0.7.108 — lint #15/#16/#17 + audit log 코드 구현 (SOT 정의 → 런타임)

> **BLUF**: v0.7.107 SOT 정의 → **v0.7.108 코드 런타임 化**. `raven/core/lint.py`에 #15 (slug-title 1:1), #16 (vault growth rate), #17 (duplicate title) check 함수 구현 + `run_all()` 등록 + CLI `--help` 정합. `raven/mcp/tools/write.py`의 `wiki_update` permission_denied 시 audit log append (G5). pytest 17 passed, `raven lint run` 17 check 동작 확인.

이전 changelog: `_meta/changelog-v0.7.107.md`

---

## §0 — 묶음 메타

| 항목 | 값 |
|---|---|
| 묶음 | lint #15/#16/#17 + audit log 코드 구현 |
| 범위 | v0.7.108 (단일 사이클) |
| 기간 | 2026-07-08 |
| 시작 트리거 | v0.7.107 SOT 정의 후속 — 정의 → 런타임 化 |
| 종료 트리거 | pytest 17 passed + raven lint 17 check 동작 |
| 정책 변경 | 0 (SOT 정합) |
| ADR 동반 | 0 |

## §1 — 무엇을 했나 (what)

### 1.1 `raven/core/lint.py` — #15/#16/#17 check 함수 + run_all 등록

**v0.7.100 (ADR-2026-07-08) → v0.7.107 (SOT 정의) → v0.7.108 (런타임)**:

- **`check_slug_title_1to1`** (#15) — frontmatter `title` 슬러그화 결과 ≠ 파일명 → 🟡 warning. main name + 부속어 예외, ADR/journal 컨벤션 면제. SCHEMA.md L81-85 정합
- **`check_vault_growth_rate`** (#16) — 7일 rolling window의 page count 증가율 > 3σ (과거 30일 baseline) → 🔵 info. baseline 30일 데이터 부족 시 skip. SCHEMA.md L248 정합
- **`check_duplicate_title`** (#17) — title 유사도 > 0.8 (SequenceMatcher.ratio) 페이지 2개+ → 🟡 warning. SCHEMA.md L249 정합

**상수 추가**:
```python
VAULT_GROWTH_WINDOW_DAYS = 7
VAULT_GROWTH_BASELINE_DAYS = 30
VAULT_GROWTH_SIGMA_THRESHOLD = 3.0
DUPLICATE_TITLE_THRESHOLD = 0.8
```

**`run_all()` 등록** (L948-967): 14 → 17 check. docstring 14 → 17 동기화.

### 1.2 `raven/mcp/tools/write.py` — audit log (G5)

`wiki_update` `_is_immutable_agent_path` 가드 (raw/, _meta/, log.md 변조 차단) 시 **`log.md`에 audit 레코드 append** (permission_denied와 별개, PWW §8.4):

```python
audit_line = (
    f"\n## [{ts[:10]}] chore | audit blocked write: {rel} "
    f"(actor={actor}, slug={slug}, result=permission_denied)\n"
)
```

**action: "chore"** (9종 action enum) — audit 의미는 subject + `result=permission_denied` 필드로 표기. `vault_path` 직접 file append (Vault 객체 복원 회피) + try/except로 audit 실패가 본 동작 차단 안 함.

### 1.3 `raven/cli/__main__.py` — lint 14 → 17 (4곳)

- L38: `lint_app` help string
- L1166: `build` `--lint/--no-lint` help
- L1168: `build` docstring
- L1377: `lint run` docstring
- L1415: log subject 메시지

## §2 — 무엇을 하지 않았나 (의도적 scope-out)

- ❌ **vault growth rate z-score 통계 정밀도** — mean/σ 단순 계산. outlier 시그널링만 (정밀 통계는 별도)
- ❌ **duplicate title TF/IDF / Levenshtein** — SequenceMatcher.ratio (Python stdlib) 사용. 더 정밀한 알고리즘은 별도
- ❌ **audit log rotate 정책** — log.md 무한 누적 가능. 500 entries 도달 시 rotate (다음 사이클)
- ❌ **audit log 전용 lint** — audit 레코드 자체 lint (예: "30일 내 permission_denied 10회+ = 위험 패턴")
- ❌ **1.5배 soft limit override** (Conflict C5) — 1-party 권고, 2-party 미합의

## §3 — 검증

| 항목 | 결과 |
|---|---|
| `pytest tests/test_v0_7_1_lite_bootstrap_surface.py` | 17 passed |
| `pytest tests/test_tier_boundary.py` | 17 passed |
| `raven lint run` (raven-dev vault) | 17 check 동작, 125 critical (#1 누적, 본 사이클 무관) |
| `raven/core/lint.py` syntax | OK |
| `raven/mcp/tools/write.py` syntax | OK |
| `raven/cli/__main__.py` syntax | OK |
| 새 broken wikilink | 0 |

## §4 — 회고 (lessons)

1. **SOT 정의 → 런타임 化 단계 분리** — v0.7.107 = 약속, v0.7.108 = 실행. 정직 분리 (이전 평가 권고와 정합)
2. **lint #15 (slug-title 1:1) main name + 부속어 예외** — 단순 `cur != title_slug`만 검사하면 **현재 6건 (raven-dev main name 패턴)** 도 violation으로 잡힘. v0.7.104 SCHEMA main name 예외 정합을 코드에 반영 (`cur_words[:len(title_words)] != title_words`로 첫 N 단어 매치)
3. **audit log raw file append** — `vault.append()` 9종 action enum + Vault 객체 복원 복잡성 회피. `chore` action + raw `log_path.open("a")`로 단순 안전 구현
4. **pytest 자동 회귀 가드** — `tests/test_v0_7_1_lite_bootstrap_surface.py`의 SOT 키워드 검증 (v0.7.107 추가) → v0.7.108 코드 변경 시 자동 정합 검증

## §5 — 알려진 회귀 / 후속 작업

| 항목 | 우선순위 | 비고 |
|---|---|---|
| audit log rotate 정책 (500 entries) | 다음 사이클 | `log.md` 무한 누적 회피 |
| audit log 전용 lint (반복 violation 패턴) | 다음 사이클 | 위험 에이전트/actor 조기 감지 |
| 1.5배 soft limit override (Conflict C5) | 별도 | 1-party 권고, 2-party 미합의 |
| 다른 vault audit | 다음 사이클 | |
| raven wikilink resolver 한글 slug 한계 | 별도 | raven core |

## §6 — 다음 사이클

본 사이클 = lint #15/#16/#17 + audit log 런타임 化 종착. 다음 사이클은 사용자 명시 요청 시 (P55-6).

가능한 후보:
- 다음 사이클: audit log rotate + audit log 전용 lint
- 다음 사이클: 다른 vault audit
- 다음 사이클: 1.5배 soft limit override

---

🤖 Generated with [Claude Code](https://claude.com/claude-code)
