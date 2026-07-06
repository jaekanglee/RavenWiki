---
title: "ADR: SCHEMA 9종 고수 + content/_index/ 시스템 영역 격리 (817e2a2 index type 시도 자가 교정)"
date: 2026-07-04
status: accepted
audience: agent, human
supersedes: null
related:
  - AGENTS.md §0.5 (North Star)
  - AGENTS.md §10 (SCHEMA 9종 외 type 정의 금지)
  - _meta/decisions/adr-2026-06-30-llm-wiki-plus-alpha.md
  - raven/core/contracts.py:436 (valid_types = 9종)
  - raven/core/lint.py:90 (valid_types = 9종)
  - raven/core/index_builder.py (content/_index/{type}.md 자동 생성)
  - docs/architecture.md D10 (graph hub fan-out fix)
related_changelog: v0.7.48 (817e2a2 시도), v0.7.50 (ebcde83 자가 교정)
type: rule
---

# ADR — SCHEMA 9종 고수 + content/_index/ 시스템 영역 격리

> **한 줄**: 817e2a2에서 SCHEMA 9종에 `index`를 추가하려 했으나 §10 정책 위반 (type 9종 외 추가 금지). ebcde83에서 `system/SCHEMA.md` 자체가 Lite bootstrap 2-file로 흡수되며 자가 교정됨. 본 ADR은 **§10 정책 정합** + **`content/_index/` 시스템 영역 격리**로 의도 보존.

---

## 0. 맥락 (Context)

Raven의 SCHEMA는 **type 9종** 고정 (concept / person / comparison / project / tool / rule / query / journal / issue). AGENTS.md §10은 "SCHEMA.md 9종 외 type 정의 ❌"를 명시. 사용자 vault의 모든 페이지는 이 9종 중 하나로 type이 박혀야 lint 통과 + 정상 인덱싱.

**graph 성능 문제 (v0.7.48)**:
`content/index.md` (자동 카탈로그)가 모든 페이지를 직접 wikilink로 가리킴 → graph hub fan-out. 1 vault에 26 edge / 105 edge 발생 (실측). 817e2a2는 이를 **`content/_index/{type}.md` 자동 카탈로그 페이지**로 분리하는 fix를 도입:
- root `content/index.md` → 9개 type별 `content/_index/{type}.md`로만 링크
- 각 `content/_index/{type}.md`는 해당 type의 페이지들만 모음

**SCHEMA 정책 위반 시도 (817e2a2, 7/3)**:
구현 중 `_index/{type}.md` 자동 생성 페이지에 `type: index`를 부여하려 했음. commit 메시지: "SCHEMA.md template gains `index` as a valid type." → **§10 위반 (type 9종 외 추가)**.

**자가 교정 (ebcde83, 7/3, 1일 후)**:
Lite bootstrap 2-file refactor (Tier 2 = SCHEMA + PROJECT-WORKFLOW + log.md)에서 **`raven/core/templates/system/SCHEMA.md` 통째로 삭제** (Tier 2 위치로 흡수). 결과적으로:
- `system/SCHEMA.md`에 박혔던 `index` type 라인도 함께 사라짐
- `agent/SCHEMA.md` (Lite bootstrap 2-file SCHEMA)에는 `index` type 없음 (검증됨: 9종만)
- 코드 `valid_types` (contracts.py:436, lint.py:90)도 9종 그대로

→ **위반 시도가 자가 교정된 상태**. 그러나 **위반 시도의 의도(자동 카탈로그 시스템 영역)**는 보존되어야 함.

## 1. 결정 (Decision)

**§10 정책 그대로 유지** — type은 9종 고정. **`content/_index/` 폴더는 시스템 영역으로 격리** (frontmatter type 검증 면제, 마치 `_meta/`, `raw/`처럼).

| 영역 | type | lint #10 면제 |
|---|---|---|
| `<vault>/content/**/*.md` | 9종 필수 | ❌ (위반 시 lint warning) |
| `<vault>/content/_index/*.md` | **시스템 자동 생성 (type 없음 OK)** | ✅ (system area whitelist) |
| `<vault>/content/index.md` | **시스템 자동 생성** | ✅ |
| `<vault>/_meta/**/*.md` | 자유 | ✅ (운영 문서) |
| `<vault>/raw/**` | 자유 (사람 1차) | ✅ (raw/ 정책 §7) |

**index_builder.py**는 `content/_index/{type}.md` 생성 시 **frontmatter 없이** 생성하거나, **`type` 필드 자체를 박지 않음** (또는 `type: system` 같은 internal marker로 lint 면제). 단, 이 ADR 시점(`index_builder.py`)은 frontmatter 없는 형태로 추정 — 코드 확인 후 결정.

## 2. 정당화 (Rationale)

### 2.1. §10 정책 정합

- AGENTS.md §10 "SCHEMA 9종 외 type 정의 ❌"는 명확한 금칙. `index` 추가는 위반.
- 사용자 vault 페이지가 9종 외 type을 박는 일이 발생하면 **lint가 차단** (위반 자체가 검사됨).
- 자가 교정 (ebcde83)이 일어났으나 **시도 자체가 명문화된 정책**이 없었음 → 본 ADR로 **"system area는 type 면제"** 패턴을 정책화.

### 2.2. 자동 카탈로그 의도 보존

- 817e2a2의 graph hub fan-out fix (D10)은 **유효한 성능 개선** — 1 hub가 26+ edge 가져가는 건 검색/탐색에 무리.
- 자동 카탈로그는 사람이 작성하는 페이지가 아니라 **도구가 생성하는 시스템 영역** → type을 박을 의미가 없음.
- `content/_index/`를 system area로 격리하면 type 면제 + 자동 생성 가능 + 9종 정책 유지 3가지 동시 만족.

### 2.3. Trade-off 명시

- **(+)** §10 정책 정합 유지 (9종 고정)
- **(+)** 자동 카탈로그 의도 보존 (graph hub fan-out fix 유지)
- **(+)** Lite bootstrap 2-file SCHEMA (`agent/SCHEMA.md`)에는 type 9종만 정의 — vault 사용자 영향 0
- **(-)** `content/_index/` 페이지가 frontmatter에 `type`을 안 가지므로, vault 사용자가 실수로 편집하더라도 lint가 "이 페이지는 자동 생성 영역"임을 모름 → 문서화로 보완
- **(-)** 자동 생성 영역 vs 사람 작성 영역 경계 — 향후 다른 자동 생성 폴더 (`content/_draft/`, `content/_archive/`) 도 같은 시스템 영역 격리 필요할 수 있음 (YAGNI: 지금은 `_index/`만)

### 2.4. 거절한 대안 (Rejected Alternatives)

- **대안 A**: `index` type 정식 9종 → 10종 승격 (§10 절차: ADR + 사용자 승인). **거절**. 자동 카탈로그는 사람이 작성하지 않으므로 type 9종에 끼우는 게 개념적으로 어긋남. 자동 생성 영역 = type 면제 패턴이 더 정합.
- **대안 B**: `content/_index/` 자동 생성 중단 (원래대로 root `content/index.md` 단일). **거절**. 817e2a2의 graph hub fan-out fix가 무의미해짐. 26/105 edge fan-out 회귀.
- **대안 C**: `_index/`를 `_meta/` 안으로 이동. **거절**. `_meta/`는 vault 운영 문서 (사람 운영), 자동 카탈로그는 content side. 영역 의미 다름.

## 3. 구현 영향 (Implementation Impact)

### 3.1. SCHEMA 문서 (Lite bootstrap 2-file)

- **`agent/SCHEMA.md`** (현재 Lite bootstrap): type 9종 정의 그대로 유지. 변경 ❌
- ~~`system/SCHEMA.md`~~ (ebcde83에서 삭제됨): 더 이상 존재하지 않음. 복구 ❌

### 3.2. `raven/core/index_builder.py`

- `content/_index/{type}.md` 생성 시:
  - **옵션 (a)**: frontmatter 자체를 안 박음 (가장 간단). 자동 생성 영역 marker는 파일 위치(`_index/` 경로)로 식별.
  - **옵션 (b)**: `type: system` 같은 internal marker 박음. lint #10이 system area whitelist로 면제.
- 본 ADR 시점: `index_builder.py`는 옵션 (a) 형태 (`_index/{type}.md` 생성만 함, type 박지 않음) — **코드 추가 변경 불필요**.
- **검증**: `index_builder.py` L42 "Filter & Group pages"에서 `slug_lower.startswith("content/_index/")` 명시 → 이미 시스템 영역으로 인식 중.

### 3.3. Lint

- `raven/core/lint.py`의 `valid_types` 9종 유지 (변경 ❌).
- Lint #10 (frontmatter 완전성) — `_index/` 경로 페이지는 면제. `slug_module.validate`나 `index_builder.py`가 이 면제 규칙을 처리.

### 3.4. 검증

```python
# tests/test_index_builder.py (또는 test_v0_7_48_graph_hub_fix.py)
def test_index_pages_have_no_type():
    """content/_index/{type}.md 자동 생성 페이지는 type을 박지 않음."""
    builder = IndexBuilder(...)
    builder.build(vault)
    for path in (vault / "content" / "_index").glob("*.md"):
        fm = parse_frontmatter(path)
        assert "type" not in fm, f"auto-index {path} has type field (should be system area)"

def test_valid_types_remains_9():
    """SCHEMA 9종 고정 — 10종 추가 시도 자동 회귀 가드."""
    from raven.core.contracts import valid_types
    assert len(valid_types) == 9
    assert "index" not in valid_types
    assert "system" not in valid_types
```

### 3.5. 문서 명문화

- `agent/SCHEMA.md`에 **System Areas (type 면제)** 섹션 추가:
  ```
  ## System Areas (type 면제)

  다음 경로는 시스템 자동 생성 영역으로, type 9종 면제:
  - `<vault>/_meta/**` — vault 운영 문서 (Tier 2 bootstrap)
  - `<vault>/raw/**` — 사람 1차 운영 영역
  - `<vault>/content/_index/**` — 자동 카탈로그 (graph hub fan-out 방지)
  - `<vault>/content/index.md` — root 자동 카탈로그

  → 위 경로 페이지는 type 필드 없이도 lint #10 통과.
  ```

## 4. 단계 (Phasing)

| 단계 | 산출물 | 상태 |
|---|---|---|
| 0 | 본 ADR | ✅ 본 문서 (2026-07-04) |
| 1 | `agent/SCHEMA.md` System Areas 섹션 추가 (1-2줄) | ⏸ 사용자 승인 |
| 2 | 회귀 테스트 2개 (test_index_pages_have_no_type, test_valid_types_remains_9) | ⏸ 사용자 승인 |
| 3 | Changelog entry (v0.7.69+) + commit | ⏸ 사용자 승인 |

## 5. 결과 (Consequences)

### 5.1. 장점

- §10 정책 정합 유지 (9종 고정)
- 자동 카탈로그 의도 보존 (graph hub fan-out fix 유지)
- 817e2a2 시도 + ebcde83 자가 교정의 **히스토리 보존** (ADR = why 기록)
- 향후 다른 자동 생성 폴더 패턴 도입 시 본 ADR 패턴(system area whitelist) 재사용 가능

### 5.2. 단점 / 수용

- 817e2a2 + ebcde83 사이클 (7/3 하루 만에 self-correction) → ADR이 자가 교정 사실을 정식 기록함
- `content/_index/` 페이지가 frontmatter에 type 없음 → 사용자가 실수로 편집 시 lint가 "system area"임을 모름 → README/SCHEMA 문서화로 보완
- 자동 생성 영역 vs 사람 작성 영역 경계 — 향후 `_draft/`, `_archive/` 등 추가 시 별도 ADR 필요

### 5.3. 회귀 위험 (Regression Risks)

- 없음 (자가 교정 이미 완료, 본 ADR은 그 사실의 정식 기록 + 면제 규칙 명문화)

## 6. 참고 (References)

- **§10 정책**: AGENTS.md §10 (SCHEMA 9종 외 type 정의 금지)
- **위반 시도 commit**: 817e2a2 (2026-07-03, `feat(graph): add radial hierarchical layout + fix content/index hub fan-out`)
- **자가 교정 commit**: ebcde83 (2026-07-03, `refactor(vault): collapse Lite bootstrap to 2 agent-only files`)
- **D10 graph hub fan-out**: `docs/architecture.md`
- **현재 SCHEMA (Lite bootstrap)**: `raven/core/templates/agent/SCHEMA.md` (9종)
- **현재 valid_types**: `raven/core/contracts.py:436`, `raven/core/lint.py:90`
- **자동 카탈로그 빌더**: `raven/core/index_builder.py` (L42, L78, L107 부근)
- **raw/ 정책 ADR**: `_meta/decisions/adr-2026-07-02-raw-folder-human-first.md`
- **LLM Wiki +α ADR**: `_meta/decisions/adr-2026-06-30-llm-wiki-plus-alpha.md`

---

## 부록 A. Self-audit (Karpathy §6 + AGENTS.md §6,9)

- [x] **명시 (Karpathy §6 ①)**: 817e2a2 위반 시도 + ebcde83 자가 교정 둘 다 명시
- [x] **단순성 (YAGNI)**: 새 type 추가 ❌, 시스템 영역 격리 패턴 재사용
- [x] **Surgical (Karpathy §3)**: 단계별 phasing, 1단계 (문서 1-2줄) / 2단계 (회귀 테스트 2개) / 3단계 (changelog)
- [x] **검증 가능 (Goal-Driven)**: 회귀 테스트 2개로 정합성 강제
- [x] **4 저장 신호**: 재사용성 ✅ (시스템 영역 패턴) / 인수인계 ✅ (ADR 히스토리) / scope/provenance ✅ / 실패 리스크 ✅ (§10 위반 시도 보존)
