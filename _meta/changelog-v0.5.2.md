# wikisys v0.5.2 — Dashboard panel + 마이그레이션 도구

> **핵심**: lint 12개 + log.md 자동화가 **UI로 가시화**. + 5 카테고리 dry-run 마이그레이션.

릴리스 일자: 2026-06-26
이전: v0.5.1 (lint 12개 + 페이지 CRUD 자동 log)

---

## 한 줄 요약

**Dashboard에 `📜 Log` / `🔧 Lint` 2개 페이지** 추가 + **`wikisys migrate` 명령** (lint 결과 5 카테고리 dry-run/apply, 기본 dry-run).

→ 사용자가 **매번 CLI 안 띄워도** vault 건강 상태 확인. 140 issues 같은 노이즈도 UI에서 한눈에.

---

## 1. Dashboard 신규 페이지 (2개)

### 📜 `/log` — LogPage
- log.md timeline viewer
- 액션 필터 (ingest/update/create/lint/build/...)
- status 패널 (entries 수, rotation 필요)
- raw 모드 (grep-style 카파시 팁)

### 🔧 `/lint` — LintPage
- 12 check by-count bar chart
- severity counts (critical/warning/info)
- issue list (필터: check, severity)
- log 기록 옵션 (lint action → log.md)

### Layout nav
- 기존: `🕸 Graph` / `🔍 Search`
- 추가: `📜 Log` / `🔧 Lint`

---

## 2. wikisys migrate (신규 CLI)

```bash
wikisys migrate categories                  # 5 카테고리 설명
wikisys migrate plan --vault <name>         # dry-run
wikisys migrate plan --vault <name> --apply # 실제 적용 (confirm)
wikisys migrate plan --vault <name> --apply --risk safe
wikisys migrate plan --vault <name> --category broken_to_missing
wikisys migrate apply --vault <name> --yes  # 한 번에 (safe만 기본)
```

### 5개 카테고리 + 위험도

| 카테고리 | 설명 | 위험도 |
|---|---|---|
| `broken_to_missing` | `[[x]]` (target 없음) → `[[x]]?` 변환 | ✅ safe (template placeholder는 manual) |
| `orphan_cleanup` | grace 만료 orphan → `_archive/` 이동 | 🟡 review (사용자 확인) |
| `page_size_split` | 200줄+ 분할 | 🔵 manual (자동화 불가) |
| `tag_promotion` | custom tag → core 승격 후보 | 🔵 manual (SCHEMA.md 결정) |
| `frontmatter_fill` | created/updated missing → today 채움 | ✅ safe |

**기본 = dry-run**. `--apply` 명시 시에만 실행. log.md에 `migrate` entry 자동 기록.

---

## 3. default vault 실측

```bash
$ wikisys migrate plan --vault default
📋 default migration plan (DRY-RUN):
   total fixes:    95
   safe (auto):    70 ✅
   review (확인):  19 🟡
   manual (수동):  6 🔵

📊 by category:
   broken_to_missing     72  broken wikilink → missing placeholder
   page_size_split        4  200줄+ 페이지 분할 (수동)
   tag_promotion         19  custom tag → core 승격 (수동)

💡 적용:  wikisys migrate plan --vault default --apply
```

→ **70개 safe**는 한 방에 적용 가능 (critical 72 → 6).
→ **6개 manual** (`<project>/_overview` template placeholder) + **4개 page_size** + **19개 tag**는 사용자 결정.

---

## 4. 변경 파일 (총 8개)

| 파일 | 종류 | LOC |
|---|---|---|
| `dashboard/src/lib/api.ts` | 수정 | +110 (log + lint API) |
| `dashboard/src/routes/LogPage.tsx` | **신규** | 195 |
| `dashboard/src/routes/LintPage.tsx` | **신규** | 280 |
| `dashboard/src/App.tsx` | 수정 | +3 (route 2개) |
| `dashboard/src/components/Layout.tsx` | 수정 | +6 (nav link 2개) |
| `wikisys/migrate.py` | **신규** | 380 (5 category builders + 3 apply fns + plan/apply) |
| `wikisys/cli/__main__.py` | 수정 | +140 (migrate_app + 3 commands) |
| `tests/test_migrate.py` | **신규** | 180 (8 tests) |
| `_meta/migration-v0.5.2.md` | **신규** | 230 (결정 가이드) |
| `_meta/changelog-v0.5.2.md` | **신규** | (이 문서) |

**총 +1,524 LOC** (코드 1,114 + 테스트 180 + 문서 230)

---

## 5. 테스트

| 항목 | 결과 |
|---|---|
| 신규 `test_migrate.py` | 8/8 ✅ |
| TypeScript (`tsc -b --noEmit`) | 0 errors ✅ |
| 전체 회귀 | **175/175 ✅** (v0.5.1: 167 → v0.5.2: 175, +8) |

---

## 6. Dashboard 사용 예

브라우저에서 `http://localhost:5173/log` / `/lint` 접속.

```bash
# 1. API 서버 실행
python -m wikisys.api &

# 2. dashboard dev
cd dashboard && npm run dev

# 3. 브라우저:
#    /log    → vault log timeline
#    /lint   → 12 check by-count chart + issue list
```

→ 헤더에 `📜 Log` / `🔧 Lint` 링크 자동 추가.

---

## 7. 사용자 결정 필요 (마이그레이션 실행)

`_meta/migration-v0.5.2.md` 참조. 4개 Q:

- [ ] Q1: A안 (보수적) / B안 (자동화) / C안 (그대로)
- [ ] Q2: page_size 4개 → 분할 / `_meta/` 이동 / 그대로
- [ ] Q3: tag 19개 → SCHEMA.md 일괄 승격 / custom 유지
- [ ] Q4: orphan 7개 → archive / 개별 결정 / 그대로

각 결정 후:
```bash
wikisys build
wikisys lint summary
```

---

## 8. 다음 단계

| 후보 | 시점 |
|---|---|
| v0.5.3 — orphan_cleanup CLI wiring (현재 fix 함수만 있고 CLI 미연결) | 사용자 Q4 결정 시 |
| v0.5.3 — Dashboard의 `🚀 Build` 버튼 (현재는 CLI만) | Dashboard 확장 |
| v0.6 — MCP 강화 (vector search, related docs) | ai-roadmap M3 |
| v0.6 — Tailscale 외부 노출 | 모바일 사용 시 |

---

## 관련

- [[_meta/SCHEMA]] (정책 매니페스트)
- [[_meta/migration-v0.5.2]] (default vault 결정 가이드)
- [[_meta/changelog-v0.5.1]] (lint 12개)
- [[_meta/changelog-v0.5]] (log.md 인프라)
- 카파시: <https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f>
