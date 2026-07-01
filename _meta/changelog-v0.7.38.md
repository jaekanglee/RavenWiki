# raven v0.7.38 — multi-author vault lint 확장 (wikilink 형식 일관성 + log.md 추가 전용성 회귀 검출)

> **핵심**: 한 vault 를 여러 author(에이전트/사람)가 동시 운영하는 경우 두 가지 공통 회귀를 lint 가 detect-only 로 잡아냅니다. ① wikilink 형식 통일 부족 (short form `[[foo]]` vs long form `[[content/foo]]` 혼재) — INFO 1건 + 샘플 5개 + "(+N more)". ② `log.md` 의 append-only 가정 위반 (시간 역전 entry) — WARNING. **둘 다 silent auto-fix 안 함** — `vault.json.agents` (v0.7.37) 의 opt-in 정책 사고와 같은 철학: raven 은 detect-only generics 만 제공, 사용자 도메인 정책은 사용자 vault 가 결정.

릴리스 일자: 2026-07-01
이전: v0.7.37

---

## 1. 배경 — 요청 발생

`hermes-infra` vault 운영자(3개 Hermes 프로필 = 동일 vault 동시 운영) 가 `~/.hermes/decisions/RAVEN-FEATURE-REQUEST.md` 에서 4종 강제 메커니즘 요청. 1:1 검토 후:

* **요청 1 (wikilink auto-format)** 과 **요청 2 (log.md integrity)** 는 raven 제품 자체 결함 — 다른 사용자도 같은 문제. **lint detect-only 로 채택**.
* **요청 3 (author tracking)** 과 **요청 4 (cross-profile protocol)** 은 hermes-infra 도메인 정책(R5/R6/9.x) — raven core 가 표준화하면 다른 사용자에게 침습. `vault.json.agents` (v0.7.37) 의 `agents` allowlist 가 절반 해결. v0.7.39+ 에서 `author_folders` 확장으로 후속 검토.

이번 사이클 = 첫 두 가지 요청의 detect-only 응답.

---

## 2. 변경 사항

### 2-1. Rule #17 `wikilink-format-consistency` (INFO, lint)

* **`scripts/lint.py`** (`_lint_all` 끝부분, Rule #11 다음):
  * `pages.content` 본문에서 wikilink 후보를 `re.finditer(r"\[\[([^\]!|?]+)...")`.
  * target 이 다음 조건 모두 해당 시 "short form" 으로 카운트:
    * `/` 미포함 (= vault-relative prefix 없음)
    * `http://` / `https://` / `mailto:` 로 시작 안 함
  * 카운트가 1 이상 → 단일 INFO issue, vault-wide 단위로 surface (`path="(vault)"`).
  * 메시지에 샘플 최대 5개 wikilink + `(+(N-5) more)` suffix.
  * **`[[x]]!`, `[[x]]?` intent 표기는 무관** — `[[content/foo!]]` (intent marked long) 는 카운트 안 함.
  * **auto-rewrite 절대 안 함.** 도메인 의존 결정은 vault opt-in 으로.

### 2-2. Rule #18 `log-append-rollback` (WARNING, lint)

* **`scripts/lint.py`** (Rule #17 다음):
  * `<vault_root>/log.md` 의 `## [YYYY-MM-DD] action | subject` 헤더 줄들만 `re.findall` 로 date 추출.
  * 인접 entry 비교: `cur_date < prev_date` → 시간 역전 1건.
  * 1건 이상 → 단일 WARNING issue, path=`"log.md"`.
  * 메시지에 샘플 최대 3개 (line N: [cur] after [prev]) + `(+(N-3) more)` suffix (N > 3 일 때만).
  * **detail 줄 (`- key: val`) 은 무시** — 어차피 헤더 패턴만 매치.
  * **silent repair 절대 안 함** — repair 가 오히려 signal 을 숨김.
  * `vault_root=None` 인 CLI 호출에서는 log 검출 skip (silent). 다른 사용자가 `--db <wiki.db>` 만 넘기고 `--vault` 안 줘도 lint 다른 룰은 정상 동작.

### 2-3. 회귀 가드 (자동 검증)

* **`scripts/tests/test_lint_v0_7_38.py`** (신규, 16 케이스):
  * Rule #17: long-form only / short-form only / intent-marked long-form 통과 / sample cap 5개 / URL-prefix skip / 단수 short-form 케이스.
  * Rule #18: log 없음 = no issue / monotone log no issue / 시간 역전 1건 / under-cap no overflow / overflow above-cap / corrupt log 500 안 함 / 단일 entry log / detail 줄 무시 / 두 룰 독립 공존.
  * in-memory wiki.db schema (pages, links, tags, content + raw_content + links.context) 재현해서 `_lint_all` 직접 호출 — 다른 테스트들과 격리.

---

## 3. 검증 결과

| 항목 | 결과 | 비고 |
|---|---|---|
| `pytest scripts/tests/test_lint_v0_7_38.py -v` | **16 passed** | 신규 가드 (Rule #17 6건 + Rule #18 9건 + co-exist 1건) |
| `pytest scripts/tests/test_lint.py` | **24 passed** | 기존 lint suite 회귀 0 |
| `pytest tests/` (raven core) | **525 passed, 2 skipped** | 회귀 0 |
| `python -c "import ast; ast.parse(...)"` (lint.py) | **OK** | syntax clean |
| 사용자 vault 데이터 / raven 핵심 코드 | **0건 변동** | lint 룰 2건 추가 외 |

---

## 4. 다음 단계

* **다음 사이클 후보 (사용자 결정 대기)**:
  * v0.7.39+ `vault.json.author_folders` opt-in 확장 (요청 3·4의 hermes-infra 도메인 격리) — `<actor>: <folder-glob>` map, actor ≠ folder 인 write 시 경고/거부.
  * 또는 다른 우선순위 (예: Dashboard federated wikilink wire-in).
* 요청자에게 위 회신은 `~/.hermes/decisions/RAVEN-FEATURE-REQUEST.md` 작성자에게 회신 초안으로 이미 전달됨 (별도 메시지). 이후 응답에 따라 후속 결정.
