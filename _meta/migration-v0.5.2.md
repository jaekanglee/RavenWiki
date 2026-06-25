# v0.5.2 마이그레이션 가이드 — default vault

> v0.5.1+ lint 12개 자동화로 default vault에서 **140 issues** 발견됨.
> v0.5.2+는 **dry-run 기반 마이그레이션 도구** 제공. 데이터는 절대 자동 변경 ❌.

릴리스: 2026-06-26

---

## 0. dry-run 결과 (default vault)

```bash
$ raven migrate plan --vault default

📋 default migration plan (DRY-RUN):
   total fixes:    95
   safe (auto):    70 ✅     ← --apply --risk safe
   review (확인):  19 🟡     ← --apply --risk review (사용자 확인)
   manual (수동):  6 🔵      ← 자동화 불가

   lint context: {'critical': 72, 'warning': 57, 'info': 11, 'total': 140}

📊 by category:
   broken_to_missing     72  broken wikilink → missing placeholder
   page_size_split        4  200줄+ 페이지 분할 (수동)
   tag_promotion         19  custom tag → core 승격 (수동)
```

→ **`orphan_cleanup` 0개** (현재 orphan 7개는 grace 중 또는 warning이지만 fix 함수 연결 안 됨, v0.5.2.1 패치 가능)
→ **`frontmatter_fill` 0개** (모든 페이지에 created/updated 있음, clean)

---

## 1. 5개 카테고리 결정 가이드

### 🟡 #1 broken_to_missing (72개)

**문제**: `[[x]]` 인데 target 없음 → critical. 카파시 가이드대로 하자면:
- (a) `[[x]]?` (의도적 placeholder) — 미래에 페이지 만들 예정
- (b) `[[x]]!` (broken 의도) — 절대 안 만들 페이지
- (c) 페이지 만들기 — 진짜 필요

**72개 분류** (실측):
| sub-pattern | 개수 | 권장 | 비고 |
|---|---|---|---|
| `[[scripts/build_db]]`, `[[scripts/lint]]` (옛 위치) | 24+ | **(a) `[[x]]?` 변환** | v0.3 이전 문법, 현재는 `raven build` / `raven lint` |
| `[[_meta/system-design]]`, `[[_meta/mvp-prd]]` | 12+ | **(a) `[[x]]?` 변환** | 옛 vault 구조, _meta/ 하단 페이지 |
| `[[<project>/_overview]]` (template placeholder) | 6 | **(c) 페이지 만들기** (또는 ignore) | `<project>` 자체가 placeholder |
| 기타 (예: `[[harumoa/2026-06-26]]`) | 30 | **(a) 또는 (b)** | 사용자 판단 |

**권장 액션**:
```bash
# 1. dry-run으로 정확히 무엇이 바뀌는지 확인
raven migrate plan --vault default --category broken_to_missing

# 2. 70개 safe만 적용 (template placeholder는 자동 skip)
raven migrate plan --vault default --category broken_to_missing --apply --risk safe
# → log.md에 migrate entry 자동 기록
```

**예상 결과**: critical 72 → 6 (template placeholder만 남음, 6개는 수동 결정)

---

### 🟡 #2 page_size_split (4개, manual)

**문제**: SCHEMA.md, log.md, m1-completion-report, how-to-start-vault (사용자 분할 보류)

**현재 상태**: memory에 "사용자가 분할 보류" 명시. 자동화는 **사용자 결정 후**.

**옵션**:
- (a) 분할 (LLM이 의미 단위로) — 1-2시간 작업
- (b) `_meta/` 로 이동 (운영 문서라 lint 면제 후보) — SCHEMA에 rule 명시 필요
- (c) `#8 page_size` 면제 항목 추가 (대형 reference 페이지용)
- (d) 그대로 (info라 lint는 통과)

**권장**: **(b) `_meta/`로 이동 + SCHEMA.md에 "type: rule → 200줄 면제" 추가** (이미 stale 면제에 적용된 패턴과 동일)

**사용자 결정 필요** — 이 가이드가 합의되면:
```bash
# 1. 4개 파일을 _meta/로 이동 (수동 또는 git mv)
git mv content/SCHEMA.md _meta/SCHEMA-content.md   # 예시
# 2. SCHEMA.md (전역)에 면제 규칙 추가
# 3. lint #8 결과 확인: 0개
```

---

### 🟡 #3 tag_promotion (19개, review)

**문제**: core taxonomy에 없는 tag 19개 사용 중.

**19개 리스트** (실측 필요, dry-run으로 확인):
```bash
raven migrate plan --vault default --category tag_promotion --json | jq
```

**권장 액션**:
- (a) **코어 승격** (자주 쓰이는 tag) — SCHEMA.md에 추가
- (b) **custom 유지** (드문 tag) — 그대로
- (c) **제거** (오타 / 일회성)

**판단 기준**: 같은 tag가 3+ 페이지에서 사용 시 → (a) 코어 승격 후보

**예시 (memory 기반 추정)**:
- `karpathy` → 이미 core 가능 (memory: "core 태그 9건 승격 미결 — 사용자 결정 보류" — 이 9건과 매칭)
- `llm-wiki` → 이미 core
- `mcp` → 이미 core

→ **memory의 "core 태그 9건 승격 미결" 항목이 이 카테고리와 매칭**. 사용자가 SCHEMA.md에 한 번에 결정 추가하면 끝.

---

### 🟡 #4 orphan_cleanup (0개, 현재)

**현재**: orphan 7개 발견 (grace 만료된 것), 그러나 `migrate apply orphan_cleanup` 연결은 v0.5.2.1+.

**현재 상태**:
- 7개 orphan 모두 warning (lint #4)
- 자동 archive는 미구현 (안전 우선)
- 수동 archive: `raven page delete <slug>` 한 번씩

**권장**: 사용자가 직접 결정 — archive vs keep.

**자동화하려면** (v0.5.2.1):
- `apply_orphan_cleanup(vault, slug)` 함수 이미 작성됨 (migrate.py:253)
- `_plan_orphan_cleanup` builder도 있음
- 단지 CLI wiring만 빠짐

→ 이번 세션에서는 user manual action.

---

### 🔵 #5 frontmatter_fill (0개, clean)

**현재**: 모든 페이지에 created/updated 있음. 적용할 fix 0개.

**왜 0개**: v0.3+에서 page new가 자동 추가, 기존 페이지는 SCHEMA에 따라 수동으로 채워졌음.

**이 카테고리는 신규 vault / 외부 마이그레이션용** — 현재 default vault는 clean.

---

## 2. 적용 순서 (사용자 결정 필요)

### A안: 보수적 (안전만)
```bash
# Step 1: broken → missing 자동 (70개 safe)
raven migrate plan --vault default --category broken_to_missing --apply --risk safe
# → critical 72 → 6

# Step 2: orphan 7개 수동 결정
# 각 페이지 검토 후:
raven page delete content/orphan-1   # archive
# 또는 keep (둘 다 OK)

# Step 3: tag 19개 SCHEMA.md에 추가
# _meta/SCHEMA.md에 core 태그 승격

# Step 4: page_size 4개 _meta/ 이동
git mv content/SCHEMA.md _meta/...
# SCHEMA.md에 "type: rule → 200줄 면제" 추가

# Step 5: build (DB 재구축)
raven build
# → critical 0 / warning 0 / info ≤ stale
```

### B안: 자동화 (모든 safe + review)
```bash
# Step 1+2 한 번에
raven migrate plan --vault default --apply --risk safe
# → 70개 broken_to_missing + 0개 frontmatter_fill
# → 4 page_size + 19 tag은 review/manual이라 skip

# 이후 step 2-5는 A안과 동일
```

### C안: 그대로 (마이그레이션 안 함)
- lint info는 vault 동작에 영향 ❌
- critical만 fix하고 warning/info는 backlog

---

## 3. 결정 항목 체크리스트

사용자가 아래 4개 중 하나만 결정하면 OK:

- [ ] **Q1**: A안 / B안 / C안 중 선택
- [ ] **Q2**: page_size 4개 → 분할 / `_meta/` 이동 / 그대로
- [ ] **Q3**: tag 19개 → SCHEMA.md에 일괄 승격 (custom 일부) / 모두 custom 유지 / 무시
- [ ] **Q4**: orphan 7개 → 일괄 archive / 개별 결정 / 그대로

각 결정 후:
```bash
raven build          # DB 재구축
raven lint summary   # 결과 확인
```

---

## 4. 다음 단계 (마이그레이션 완료 후)

- [ ] Dashboard의 `🔧 Lint` 페이지에서 실시간 확인
- [ ] `raven lint run --vault default --log` 자동 log 기록 (cron)
- [ ] GitHub PR로 v0.5.2 머지

---

## 관련

- [[_meta/SCHEMA]] (정책 매니페스트)
- [[_meta/changelog-v0.5.2]] (릴리스 노트)
- [[_meta/changelog-v0.5.1]] (lint 12개)
- [[_meta/changelog-v0.5]] (log.md 인프라)
- 카파시: <https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f>
