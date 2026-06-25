# wikisys v0.5.1 — lint 12개 풀세트 + 페이지 CRUD 자동 log

> **핵심**: 카파시 gist의 12개 lint 항목 **100% 자동화**. 페이지 CRUD/Build 시 log.md 자동 갱신.

릴리스 일자: 2026-06-26
이전: v0.5.0 (log.md 인프라 + 정책 문서 3개)

---

## 한 줄 요약

**`wikisys/core/lint.py`에 9개 check 함수 추가** (orphan/contradictions/confidence/stale/page size/tag audit/frontmatter/index/log_size 정리) + **페이지 CRUD/build 자동 log hook** + **CLI `wikisys lint` 명령 3개** + **API 2개 endpoint**.

→ 카파시 가이드 12/12 자동화. 운영자가 `wikisys lint` 한 번이면 vault 건강 상태 100% 파악.

---

## 1. lint 12개 풀세트

| # | 항목 | 심각도 | 함수 | 비고 |
|---|---|---|---|---|
| #1 | broken wikilink | 🔴 critical | `link.find_broken` | (v0.5.0) |
| #2 | broken-intent false positive | 🔴 critical | `link.find_broken_intent` (신규) | `[[x]]!` 인데 target 존재 |
| #3 | missing wikilink | 🔵 info | `link.find_missing` | (v0.5.0) 의도적 placeholder |
| #4 | **orphan** | 🟡 warning / 🔵 info (grace 중) | `check_orphans` (신규) | **7일 grace**, `.vault.json`에 `lint_orphan_grace_days` override |
| #5 | **contradictions** | 🟡 warning | `check_contradictions` (신규) | frontmatter.contradictions 미존재 |
| #6 | **confidence low** | 🔵 info | `check_confidence_low` (신규) | frontmatter.confidence: low |
| #7 | **stale** | 🔵 info | `check_stale` (신규) | 90일+ 미갱신 (rule 면제) |
| #8 | **page size** | 🔵 info | `check_page_size` (신규) | > 200줄 (분할 권장) |
| #9 | **tag audit** | 🟡 warning | `check_tag_audit` (신규) | core taxonomy 외 태그 |
| #10 | **frontmatter 완전성** | 🔵 info / 🟡 warning | `check_frontmatter_completeness` (신규) | title/type/created/updated |
| #11 | **index 완전성** | 🟡 warning | `check_index_completeness` (신규) | FS vs DB 비교 (build 후) |
| #12 | log size | 🔵 info | `check_log_size` | (v0.5.0) ≥ 500 → rotate |

**grace 기간 설정**:
```json
// .vault.json
{
  "name": "default",
  ...
  "lint_orphan_grace_days": 7  // 기본값
}
```

→ 0으로 설정하면 즉시 warning.

---

## 2. CLI: `wikisys lint ...` (3개 명령)

```bash
wikisys lint run [--vault] [--check #N] [--severity X] [--verbose] [--json] [--log]
wikisys lint summary [--vault] [--json]
wikisys lint check #N [--vault] [--json]
```

예시:
```bash
$ wikisys lint run --vault default
❌ default — 72C / 57W / 11I (total 140)

📊 by check:
   #1: 72
   #11: 38
   #4: 7
   #8: 4
   #9: 19

$ wikisys lint summary --vault default
📊 default lint summary:
   total:     140
   critical:  72 🔴
   warning:   57  🟡
   info:      11     🔵

   by check:
     #1   72  ████████████████████
     #11   38  ████████████████████
     #9    19  ███████████████████
     ...

$ wikisys lint check #4 --vault default
🔍 #4 (orphans): 7 issues
  [warning] content/old-orphan  orphan (no inbound, age 30d ≥ grace 7d)
  ...

$ wikisys lint run --check #4 --log
# → log.md에 lint entry 자동 append
```

→ `wikisys build` 안에 lint 통합 (기본 ON, `--no-lint`로 끄기).

---

## 3. API: 2개 endpoint

| Method | Path | 응답 |
|---|---|---|
| GET | `/api/vaults/{name}/lint?check=#N&severity=X&write_log=bool` | counts + by_check + issues |
| GET | `/api/vaults/{name}/lint/summary` | counts + by_check |

예시:
```bash
curl http://localhost:8765/api/vaults/default/lint | jq
curl http://localhost:8765/api/vaults/default/lint?check=%234 | jq
curl http://localhost:8765/api/vaults/default/lint/summary | jq
```

---

## 4. 자동 log hook (페이지 CRUD + build)

| 액션 | 트리거 | log action |
|---|---|---|
| `wikisys page new` | CLI | `create` |
| `wikisys page delete` (archive) | CLI | `archive` |
| `wikisys build` | CLI | `build` (v0.5.0) |
| `POST /api/vaults/{name}/pages` | API | `create` |
| `PUT /api/vaults/{name}/pages/{slug}` | API | `update` |
| `DELETE /api/vaults/{name}/pages/{slug}` | API | `archive` |
| `POST /api/vaults/{name}/build` | API | `build` (v0.5.0) |
| `wikisys lint run --log` | CLI | `lint` |
| `GET /api/vaults/{name}/lint?write_log=true` | API | `lint` |

→ 모든 hook은 `try/except`로 보호 — log append 실패가 본 작업에 영향 ❌.

---

## 5. 변경 파일 (총 6개)

| 파일 | 종류 | LOC |
|---|---|---|
| `wikisys/core/lint.py` | 수정 (확장) | +400 (12 check 함수 + run_all) |
| `wikisys/core/link.py` | 수정 | +28 (find_broken_intent) |
| `wikisys/core/db.py` | 수정 | +15 (build에 lint 통합) |
| `wikisys/cli/__main__.py` | 수정 | +135 (lint_app + 3 commands) |
| `wikisys/api/server.py` | 수정 | +55 (2 endpoints) |
| `tests/test_lint_v2.py` | **신규** | 320 (19 tests, 9 check) |
| `tests/test_lint_log_size.py` | 수정 | 시그니처 변경 (info dict → issue list) |
| `_meta/changelog-v0.5.1.md` | **신규** | (이 문서) |

**총 +1,000 LOC** (코드 600 + 테스트 320 + 문서 80)

---

## 6. 테스트

| 항목 | 결과 |
|---|---|
| 신규 `test_lint_v2.py` | 19/19 ✅ |
| 수정 `test_lint_log_size.py` | 4/4 ✅ (시그니처 변경) |
| 전체 회귀 | **167/167 ✅** (v0.5.0: 148 → v0.5.1: 167, +19 신규) |

---

## 7. 카파시 가이드 12/12 충족

| 카파시 항목 | 충족도 | 비고 |
|---|---|---|
| #1 broken wikilink | ✅ | link_module |
| #2 broken-intent false positive | ✅ v0.5.1+ | link.find_broken_intent |
| #3 missing wikilink | ✅ | link_module |
| #4 orphan (7일 grace) | ✅ v0.5.1+ | configurable |
| #5 contradictions | ✅ v0.5.1+ | frontmatter field |
| #6 confidence low | ✅ v0.5.1+ | frontmatter field |
| #7 stale (90일) | ✅ v0.5.1+ | |
| #8 page size | ✅ v0.5.1+ | |
| #9 tag audit | ✅ v0.5.1+ | core + custom |
| #10 frontmatter 완전성 | ✅ v0.5.1+ | |
| #11 index 완전성 | ✅ v0.5.1+ | build 후 |
| #12 log size | ✅ v0.5.0 | |

→ **12/12 자동화 100%**.

---

## 8. default vault 실측 결과

```
$ wikisys lint summary --vault default
📊 default lint summary:
   total:     140
   critical:  72 🔴
   warning:   57  🟡
   info:      11     🔵

   by check:
     #1   72  ████████████████████  broken wikilink (template placeholder)
     #2    0                       깨끗
     #3    0                       깨끗
     #4    7  ███████              orphan 7개 (grace 만료)
     #5    0                       깨끗
     #6    0                       깨끗
     #7    0                       깨끗
     #8    4  ████                 page size 200줄 초과 (4개, 사용자 분할 보류)
     #9   19  ███████████████████  custom tag 19개 (코어 승격 후보)
     #10   0                       깨끗
     #11  38  ████████████████████  DB vs FS mismatch (build 안 됨)
     #12   0                       깨끗
```

**해석**:
- 72 broken = template placeholder (`[[<project>/_overview]]` 등) + 진짜 broken — `[[x]]?`로 변경 권장
- 7 orphan = 사용 안 되는 페이지, archive 후보
- 4 page size = SCHEMA.md, log.md, m1-completion-report, how-to-start-vault (사용자 분할 보류)
- 19 tag = custom tag → SCHEMA.md에 core 승격 가능
- 38 index = wiki.db 빌드 안 됨 → `wikisys build` 필요

→ 이 5개 카테고리만 정리하면 default vault lint 통과.

---

## 9. 다음 단계 (v0.5.2)

| 작업 | 비고 |
|---|---|
| Dashboard log viewer (Log.tsx) | UI 작업 |
| Dashboard lint panel | UI 작업 |
| default vault 자동 마이그레이션 (template → `[[x]]?`, 200줄 분할) | 사용자 결정 필요 |
| core tag 승격 가이드 | custom tag 19개 → SCHEMA.md 추가 |
| cron-friendly rotate hook | 500 entries 자동 |

---

## 관련

- [[_meta/SCHEMA]] (정책 매니페스트, v0.5.1 강화)
- [[_meta/changelog-v0.5]] (v0.5.0 — log 인프라)
- [[content/llm-wiki]] (카파시 gist 분석)
- 카파시: <https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f>
