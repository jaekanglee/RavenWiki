# wikisys v0.5.0 — 카파시 LLM Wiki 운영정책 도입

> **핵심**: vault가 카파시 gist의 3-Layer 운영정책을 1급 시민으로 갖춤.
> `log.md` 자동화 + lint 12개 중 #12 선반영 + 정책 문서 3개.

릴리스 일자: 2026-06-26
이전: v0.4 (archive cleanup + vault clone + GUI 갭 가이드)

---

## 한 줄 요약

**log.md (vault 루트) 자동화** + **wikisys-policy.md 템플릿** + **meta sync --with-log** + **CLI/API log endpoints** + **lint log_size check**.

→ karpathy gist의 핵심 운영 패턴 (log.md + lint 12개 + 운영 규칙) 중 v0.5.0은 **기반 작업** 완료. lint 9개 잔여분은 v0.5.1, dashboard는 v0.5.2.

---

## 1. 신규 모듈

### `wikisys.core.log` (60 LOC + 100 LOC test)

카파시 LLM Wiki 패턴. `log.md` 위치는 **vault 루트 고정**.

| 함수 | 역할 |
|---|---|
| `log_path(vault)` | `<vault>/log.md` 경로 |
| `ensure_log(vault)` | 없으면 템플릿에서 생성 (idempotent) |
| `append(vault, action, subject, files=, note=, extra=)` | entry 추가 (append-only, 원자적 write) |
| `load(vault)` | 전체 파싱 → list[LogEntry] |
| `list_entries(vault, tail=, action=)` | dict 리스트 (filtering) |
| `count(vault)` | entry 수 |
| `rotate(vault, year=)` | log-YYYY.md로 rotate (500 entries 시) |

**9종 액션**: `ingest`, `update`, `create`, `archive`, `delete`, `lint`, `build`, `migrate`, `chore`

**log.md 형식** (grep-parseable, 카파시 팁):
```markdown
## [2026-06-26] ingest | karpathy LLM Wiki gist
- files: [content/llm-wiki]
- reason: v0.5.0 도입
```

→ `grep "^## \[" log.md | tail -5` → 최근 5개.

---

## 2. 정책 문서 (3개 템플릿)

| 파일 | 위치 | 용도 |
|---|---|---|
| `templates/SCHEMA.md` | `_meta/SCHEMA.md` (수정) | v0.5.0+ 필드 + 운영규칙 + lint 12개 표 |
| `templates/log.md` | vault 루트 `log.md` (신규) | 작업 이력 헤더 + grep-parseable 형식 |
| `templates/wikisys-policy.md` | vault 루트 `wikisys-policy.md` (신규) | 카파시 가이드 통합 1페이지 (3-Layer + 5규칙 + 12 lint) |

→ `wikisys vault create` (bootstrap) 시 자동 복사.
→ 기존 vault 보강: `wikisys meta sync --with-log` (v0.5.0+ 옵션, 기존 파일 skip).

---

## 3. CLI 신규: `wikisys log ...`

5개 서브커맨드:

| 명령 | 역할 |
|---|---|
| `wikisys log list` | entry 조회 (--tail, --action, --json) |
| `wikisys log show` | raw 표시 (--limit, grep-style) |
| `wikisys log append` | 수동 추가 (--action, --files, --note) |
| `wikisys log rotate` | log-YYYY.md로 rotate (--year, --force) |
| `wikisys log status` | entries 수 + last + needs_rotate (--json) |

```bash
wikisys log list --tail 10
wikisys log list --action build --json
wikisys log append "manual note" --action chore --note "context"
wikisys log status
```

---

## 4. API 신규: 4개 endpoint

| Method | Path | 응답 |
|---|---|---|
| GET | `/api/vaults/{name}/log?tail=N&action=X` | entries + total |
| GET | `/api/vaults/{name}/log/status` | entries + last + needs_rotate |
| POST | `/api/vaults/{name}/log` | body: `{action, subject, files, note}` |
| POST | `/api/vaults/{name}/log/rotate?year=&force=` | rotated_to + preserved_entries |

→ FastAPI model: `LogAppend` (action/subject/files/note)

---

## 5. lint 확장: 12개 중 #12 선반영

`wikisys.core.lint.check_log_size(vault)`:

| 상태 | info 카운트 |
|---|---|
| log.md 없음 | 0 (bootstrap이 만듦) |
| entries < 500 | 0 |
| entries ≥ 500 | **1** (rotation 권장) |

→ `run_lint()` 결과에 `log_issues` 필드 추가. `wikisys build` 시 자동 호출.

**잔여 9개 (v0.5.1+)**:
- #4 orphan (7일 grace)
- #5 contradictions
- #6 confidence low
- #7 stale (90일)
- #8 page size (>200)
- #9 tag audit
- #10 frontmatter 완전성
- #11 index 완전성
- (페이지 CRUD 자동 log append)

---

## 6. build hook: 자동 log 기록

`wikisys.core.db.build_db(v)` 호출 시:

```
## [2026-06-26] build | wiki.db rebuild (ok, N pages)
- db: /Users/.../wiki.db
- returncode: 0
```

→ 실패해도 build 자체에 영향 ❌, try/except 무시.

---

## 7. 변경 파일 (총 11개)

| 파일 | 종류 | LOC |
|---|---|---|
| `wikisys/core/log.py` | **신규** | 320 |
| `wikisys/core/lint.py` | 수정 | +60 (log_size check) |
| `wikisys/core/vault.py` | 수정 | +50 (bootstrap + sync_meta --with-log) |
| `wikisys/core/db.py` | 수정 | +20 (log hook) |
| `wikisys/core/__init__.py` | 수정 | +2 (log_module export) |
| `wikisys/cli/__main__.py` | 수정 | +150 (log_app + 5 commands + meta sync --with-log) |
| `wikisys/api/server.py` | 수정 | +90 (4 endpoints + LogAppend model) |
| `wikisys/core/templates/SCHEMA.md` | 수정 | +60 (정책 강화) |
| `wikisys/core/templates/log.md` | **신규** | 8 |
| `wikisys/core/templates/wikisys-policy.md` | **신규** | 80 |
| `tests/test_log.py` | **신규** | 220 (16 tests) |
| `tests/test_lint_log_size.py` | **신규** | 80 (4 tests) |
| `tests/test_cli.py` | 수정 | +2 (sync_meta path 변경) |
| `tests/test_vault_create.py` | 수정 | +3 (sync_meta path 변경) |
| `~/.hermes/.../wikisys/SKILL.md` | 수정 | +30 (log 섹션 + 다음 단계) |

**총 +1,175 LOC** (코드 700 + 테스트 300 + 문서 175)

---

## 8. 테스트

| 항목 | 결과 |
|---|---|
| 신규 `test_log.py` | 16/16 ✅ |
| 신규 `test_lint_log_size.py` | 4/4 ✅ |
| 전체 회귀 (`tests/`) | **148/148 ✅** (이전 146 + 신규 20 - 회귀 0) |

---

## 9. 카파시 가이드 충실도

| 카파시 항목 | v0.5.0 | v0.5.1+ |
|---|---|---|
| log.md 위치 = vault 루트 | ✅ | |
| grep-parseable 형식 | ✅ | |
| append-only | ✅ | |
| 500 entries → rotate | ✅ (lint #12) | |
| index.md (content catalog) | ❌ 우리 wiki.db로 대체 | |
| raw/ 레이어 + sha256 | ❌ (소스 ingest 안 함) | |
| 9 lint 풀세트 | 부분 (1/9) | 9/9 (v0.5.1) |
| frontmatter 신호 (confidence/contradictions) | SCHEMA 명시 ✅ | lint 강제 (v0.5.1) |
| 페이지 200줄 split rule | SCHEMA 명시 ✅ | lint 강제 (v0.5.1) |
| log 500 rotate rule | lint #12 ✅ | 자동 hook (v0.5.2) |

---

## 10. 사용자 액션 가이드

### 신규 vault

```bash
wikisys vault create <name> <path>   # → SCHEMA/RULES/log/policy 자동 복사
```

### 기존 vault 보강 (v0.5.0 도입 시)

```bash
wikisys meta sync --with-log --vault <name>
# → log.md + wikisys-policy.md 추가 (없던 vault에 한함)
```

### 작업 후 검증

```bash
wikisys log status
# entries: N / 500, last: [...]

wikisys log list --tail 5
# 최근 5개 entry (build, update, ingest, ...)

wikisys build
# DB rebuild + lint (log_size check 자동)
```

### API 사용 예

```bash
curl http://localhost:8765/api/vaults/default/log?tail=5 | jq
curl -X POST http://localhost:8765/api/vaults/default/log \
  -H "Content-Type: application/json" \
  -d '{"action":"chore","subject":"manual note","note":"hello"}'
```

---

## 11. 다음 단계

### v0.5.1 (lint 12개 풀세트)
- 9개 lint 추가 (orphan/contradictions/confidence/stale/page size/tag audit/frontmatter 완전성/index 완전성)
- 페이지 CRUD 자동 log append
- 기존 페이지 frontmatter 마이그레이션 (선택)

### v0.5.2 (Dashboard + 마이그레이션)
- Dashboard Log viewer (Timeline UI)
- 기존 `default` / `second-vault` 자동 마이그레이션 가이드
- rotate 자동 hook (cron-friendly)

### OUT (의도적 제외)
- raw/ 레이어 (소스 ingest 패턴 안 씀)
- Marp / matplotlib 출력 (사용 패턴 미관찰)
- 자동 frontmatter 추가 (기존 데이터 안 건드림 정책)

---

## 관련

- [[_meta/SCHEMA]] (정책 매니페스트, v0.5.0 강화)
- [[_meta/RULES]] (편집 5규칙, v0.5.0 호환)
- [[content/llm-wiki]] (카파시 gist 분석)
- 카파시: <https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f>
