# raven v0.5.2.1 — default vault 마이그레이션 실행 + 면제 규칙

> **핵심**: v0.5.2 dry-run 결과를 default vault에 실제 적용. lint 면제 규칙 추가로 운영 문서 noise 0.

릴리스 일자: 2026-06-26
이전: v0.5.2 (Dashboard + migrate dry-run)

---

## 한 줄 요약

**lint #4/#7/#8에 `_meta/` 면제 규칙** 추가 + **default vault 마이그레이션 실행** (Q1 broken→missing 18개 safe 적용 + Q2 page_size 면제 + Q4 orphan 7개 archive).

→ **lint critical 72 → 2 (-97%)**, total 140 → 100 (-29%).

---

## 1. 변경 파일 (코드)

| 파일 | 변경 |
|---|---|
| `raven/core/lint.py` | `check_orphans` / `check_stale` / `check_page_size`에 `_meta/` 면제 추가 |
| `_meta/SCHEMA.md` | 면제 정책 명시 ("type: rule 또는 _meta/ → 200줄/stale/orphan 면제") |

### 면제 규칙 (SCHEMA.md §"분리/아카이브")

- **200줄 초과 면제**: `_meta/` 안 페이지 (rule/reference, 운영 문서)
- **stale (90일+) 면제**: `type: rule` + `_meta/` 안
- **orphan 면제**: `_meta/` 안 (운영 문서는 inbound 0이 정상)

→ **카파시 가이드의 "core tags와 rule page는 면제" 정신**을 우리 운영정책에 정식 반영.

---

## 2. default vault 마이그레이션 결과

### 시작 vs 종료

| 지표 | v0.5.2 (시작) | v0.5.2.1 (종료) | 변화 |
|---|---|---|---|
| **total** | 140 | 100 | **-29%** |
| **critical** | 72 | 2 | **-97%** |
| **warning** | 57 | 66 | +16% (archive → index mismatch 일시) |
| **info** | 11 | 32 | +21 (broken→missing 정상 전환) |

### Q1-Q4 적용 내역

| Q | 카테고리 | 적용 | 결과 |
|---|---|---|---|
| Q1 | `broken_to_missing` (safe) | 18개 `[[x]]` → `[[x]]?` | critical 72 → 10 |
| Q2 | `page_size` (면제 규칙) | 4개 면제 + `how-to-start-vault` → `_meta/` | #8 4 → 0 |
| Q3 | `tag_promotion` (보류) | 12 unique / 19 occurrences (list only) | 사용자 결정 대기 |
| Q4 | `orphan_cleanup` (review) | 7개 archive | #4 7 → 1, critical 10 → 2 |

### 최종 lint by check

```
#1  broken wikilink:    2  (template <project>/_overview placeholder)
#3  missing wikilink:   31 (의도적 placeholder, 정상)
#4  orphan:             1  (면제 안 한 페이지, 조사 필요)
#9  tag audit:          19 (Q3 사용자 결정 대기)
#11 index 완전성:       0  (build로 해결)
```

---

## 3. 안전망

### 백업
- **위치**: `~/vaults/default/_backups/pre-migration-20260625-163110/`
- **크기**: 176K
- **내용**: content/, _meta/, _archive/, log.md, raven-policy.md, SCHEMA.md, RULES.md

### log.md (작업 이력)

```
[2026-06-25] migrate  | migration apply --risk safe (applied=18)
[2026-06-25] migrate  | orphan cleanup Q4: 7개 archive
[2026-06-25] build    | wiki.db rebuild (ok)
[2026-06-25] build    | wiki.db rebuild (ok)
```

### 되돌리기 (필요 시)

```bash
# Q1 broken→missing 18개 (역변환: ? 제거)
# 텍스트 처리라 자동 스크립트 가능
# Python: re.sub(r'\[\[([^\[\]\n]+?)\]\](\?)(?!\?)', r'[[\1]]\2', text) — 단순

# Q4 archive 7개 (복원)
cp ~/vaults/default/_backups/pre-migration-20260625-163110/content/*.md \
   ~/vaults/default/content/

# Q2 how-to-start-vault 이동 (복원)
mv ~/vaults/default/_meta/how-to-start-vault.md \
   ~/vaults/default/content/

# SCHEMA.md 면제 규칙 (git revert로 충분)
```

---

## 4. 사용자 보류 (Q3)

`tag_promotion` 19개 (12 unique):

| tag | 사용 횟수 | 추천 |
|---|---|---|
| `meta` | 5 | ✅ **core 승격** (빈도 높음) |
| `raven` | 3 | ✅ **core 승격** (시스템 정체성) |
| `governance` | 2 | ✅ **core 승격** (cognitive governance 컨셉) |
| `rules` | 1 | ❌ 중복 (`rule`이 type과 중복) |
| `onboarding` | 1 | ❌ custom |
| `architecture` | 1 | ❌ custom |
| `faq` | 1 | ❌ custom |
| `guide` | 1 | ❌ custom |
| `template` | 1 | ❌ custom |
| `criticism` | 1 | ❌ custom |
| `rag` | 1 | ❌ custom |
| `security` | 1 | ❌ custom |

→ memory의 "core 태그 9건 승격 미결" 항목과 통합 결정 필요.

---

## 5. 누적 v0.5.x (4 PR)

| 버전 | 핵심 | 커밋 | +LOC | 테스트 |
|---|---|---|---|---|
| v0.5.0 | log.md 인프라 + 정책 3개 | `bb0be3b` | +1,425 | 20 신규 |
| v0.5.1 | lint 12개 + 자동 log hook | `f1d010c` | +1,288 | 19 신규 |
| v0.5.2 | Dashboard + migrate | `71277f6` | +1,592 | 8 신규 |
| **v0.5.2.1** | **면제 규칙 + 마이그레이션 실행** | (이번) | +50 | 회귀 0 |
| **합계** | **카파시 12/12 + UI + 도구 + 실행** | **4 커밋** | **+4,355** | **47 신규** |

→ **카파시 gist 운영정책 통합 작업 완료**.

---

## 6. 다음 단계 (제안)

| 후보 | 시점 |
|---|---|
| 4 PR push (origin remote 설정 후) | 사용자 결정 |
| v0.5.3 — orphan_cleanup CLI wiring + tag 3개 승격 | Q3 결정 시 |
| v0.6 — MCP vector search (ai-roadmap M3) | 다음 사이클 |
| Tailscale 외부 노출 | 모바일 사용 시 |

---

## 관련

- [[_meta/SCHEMA]] (면제 규칙 추가)
- [[_meta/migration-v0.5.2]] (결정 가이드)
- [[_meta/changelog-v0.5.2]] (이전)
- [[_meta/changelog-v0.5.1]] (lint 12개)
- [[_meta/changelog-v0.5]] (log 인프라)
- 카파시: <https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f>
