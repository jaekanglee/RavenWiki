# wikisys v0.5.3 — orphan_cleanup CLI wiring + Q3 tag 승격

> **핵심**: orphan_cleanup migrate 검증 + Q3 tag 3개 (meta/wikisys/governance) core 승격 + lint.py SCHEMA 파싱 강화.

릴리스 일자: 2026-06-26
이전: v0.5.2.1 (면제 규칙 + 마이그레이션 실행)

---

## 한 줄 요약

**A. orphan_cleanup CLI wiring** 검증 (이미 wired, 추가 작업 0) + **B. Q3 tag 3개 승격** (meta/wikisys/governance) + **lint.py SCHEMA 파싱 강화** (한 줄에 여러 tag 매치). **lint total 100 → 91 (-9%)**.

---

## 1. A. orphan_cleanup CLI wiring (검증)

`wikisys/migrate.py`에 이미 wiring됨:
- `_plan_orphan_cleanup` builder
- `apply_orphan_cleanup` 함수
- `apply_plan`이 `apply_fn` 자동 디스패치

검증: `wikisys migrate plan --vault default --category orphan_cleanup` 정상 실행 (fix 0개 — v0.5.2.1에서 7개 archive 완료).

→ **추가 코드 작업 0**, 검증만.

---

## 2. B. Q3 tag 3개 승격

### 승격 내역

default vault의 custom tag 19개 (12 unique) 중 빈도 3+ 페이지 사용 3개:

| tag | 사용 횟수 | 분류 |
|---|---|---|
| `meta` | 5 | ✅ core 승격 |
| `wikisys` | 3 | ✅ core 승격 |
| `governance` | 2 | ✅ core 승격 (3+ 기준 미달이지만 cognitive governance 컨셉 핵심) |

→ **메모리 "core 태그 9건 승격 미결"** 항목은 별도 결정으로 유지 (사용자 명시).

### 변경 파일

| 파일 | 변경 |
|---|---|
| `_meta/SCHEMA.md` (글로벌) | §"Tag Taxonomy"에 3개 추가 + §"승격 절차" 별도 ## 섹션 분리 |
| `wikisys/core/templates/SCHEMA.md` (bootstrap) | 동일 |
| `wikisys/core/lint.py` (`_core_tags`) | SCHEMA 파싱 regex 확장 |

### lint.py 변경 (`_core_tags`)

**이전**: 한 줄에 한 tag만 매치 (`^\s*[-*]\s*`?([a-z0-9-]+)`?`)
- bootstrap SCHEMA 형식 (`- 시스템: \`tag1\`, \`tag2\`, ...`)에서 첫 tag만 추출
- **3개만** 파싱 (fallback 사용 안 함)

**이후**: 두 형식 모두 지원
- 형식 1: `- 시스템: \`tag1\`, \`tag2\`, ...` → 같은 줄 모든 backtick tag 추출
- 형식 2: `- \`tag\`` → 한 줄 한 tag

→ **31개 core tag 파싱** (이전 3개), fallback 미사용.

---

## 3. 결과

### default vault lint (직접 효과)

| 지표 | v0.5.2.1 | v0.5.3 | 변화 |
|---|---|---|---|
| total | 100 | **91** | **-9%** |
| critical | 2 | 2 | - |
| warning | 66 | **57** | -14% |
| info | 32 | 32 | - |

### by check

```
#1  broken wikilink:    2  (변동 없음)
#3  missing wikilink:   31 (변동 없음)
#4  orphan:             1  (변동 없음)
#9  tag audit:          54 → 19  (-35, 3+35 tag 인식)
#11 index 완전성:       0  (변동 없음)
```

→ **#9의 35개 warning이 사라짐** (3개 승격 + lint.py regex 확장으로 다른 32개 core tag도 정상 인식).

---

## 4. 변경 파일 (총 3개)

| 파일 | 변경 | LOC |
|---|---|---|
| `wikisys/core/lint.py` | `_core_tags` regex 확장 (2 format) | +10 |
| `wikisys/core/templates/SCHEMA.md` | tag taxonomy 섹션 + 승격 절차 ## 분리 | +30 |
| `_meta/SCHEMA.md` (글로벌) | tag taxonomy 섹션 + 승격 절차 ## 분리 | +5 |
| `_meta/changelog-v0.5.3.md` | (이 문서) | 신규 |

**총 +60 LOC** (코드 10 + 문서 50)

---

## 5. 테스트

- 전체 회귀: **175/175** ✅ (변경 없음)
- `_core_tags` 동작 검증: 31개 core tag 파싱 (이전 3개)
- lint 결과 일치: default vault에서 100 → 91

---

## 6. 누적 v0.5.x (5 커밋)

| 버전 | 핵심 | 커밋 | +LOC | 테스트 |
|---|---|---|---|---|
| v0.5.0 | log.md 인프라 | `bb0be3b` | +1,425 | 20 |
| v0.5.1 | lint 12개 | `f1d010c` | +1,288 | 19 |
| v0.5.2 | Dashboard + migrate | `71277f6` | +1,592 | 8 |
| v0.5.2.1 | 면제 + 마이그레이션 | `c33e68b` | +176 | 회귀 0 |
| **v0.5.3** | **Q3 승격 + lint 파싱** | **(이번)** | **+60** | **회귀 0** |
| **합계** | | **5 커밋** | **+4,541** | **47 신규** |

---

## 7. 다음 단계

| 후보 | 시점 |
|---|---|
| v0.6 — MCP vector search (ai-roadmap M3) | 다음 사이클 |
| v0.6 — Tailscale 외부 노출 | 모바일 사용 시 |
| v0.6 — 백업 cron 자동화 | 데이터 누적 후 |

→ **카파시 12/12 + UI + 도구 + 실행 + 마무리** v0.5.x 시리즈 완료.

---

## 관련

- [[_meta/SCHEMA]] (면제 + tag taxonomy)
- [[_meta/changelog-v0.5.2.1]] (이전)
- [[_meta/migration-v0.5.2]] (Q1-Q4 결정 가이드)
- 카파시: https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f
