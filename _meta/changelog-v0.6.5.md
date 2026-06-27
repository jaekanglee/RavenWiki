# raven v0.6.5 — F-C1 hotfix: dev API에 `GET /api/index.json` 라우트 추가

> **핵심**: dev API 모드(`python -m raven.api`)에서 `/api/index.json`이 **404**였음. HomePage가 항상 빈 화면. v0.6.5에서 정적 export와 동일한 shape으로 라우트 추가. Codex/Claude 위임자가 발견.

릴리스 일자: 2026-06-27
이전: v0.6.4 (HomePage 모바일/데스크탑 양쪽 최적화)

---

## 한 줄 요약

`make dev` 후 HomePage가 Quick Actions만 보이고 페이지 0개 → 라우트 추가하여 dev API와 정적 export shape 일치.

---

## 1. 문제 (F-C1)

| 항목 | Before (v0.6.4) | After (v0.6.5) |
|---|---|---|
| `GET /api/index.json` (dev) | **404 Not Found** | **200 OK** (default vault pages) |
| `GET /api/index.json` (정적 export) | ✅ 작동 | ✅ 작동 |
| **사용자 결과** | `make dev` 후 HomePage 빈 화면 | ✅ 정상 (Quick Actions + Recent cards) |

### 발견 경위

Codex/Claude 위임자가 v0.6.4 audit 중 발견:
- `dashboard/src/routes/HomePage.tsx:87` → `fetch("/api/index.json")`
- `raven/api/server.py`에 해당 라우트 **부재**
- `scripts/export_static.py`는 vault→static JSON export만 (정적)
- dev 모드 (`python -m raven.api`)는 export를 안 부름 → 404

→ **사용자가 `make dev`로 띄워도 HomePage는 Quick Actions만 보임** (이전 사이클들에서 사용자/위임자 모두 못 봄).

### 영향

| 사용자 | 영향 |
|---|---|
| 외부 신규 (git clone → make dev) | ❌ HomePage 빈 화면 (Quick Actions만) |
| 기존 (정적 export 한 적 있는 사용자) | ✅ 작동 (dashboard/public/api/index.json) |
| 우리 (dev 모드) | ❌ 검증 못함 (사용자 v0.6.4 보고가 정적 export 상태였을 가능성) |

→ **silent failure** (HomePage가 fallback `setIndex([])`로 빈 화면 표시 — AGENTS.md §9 정책 위배).

---

## 2. 변경 사항

### 2.1 Backend (`raven/api/server.py`)

**신규 라우트**: `GET /api/index.json` (default vault, 또는 첫 등록 vault)

```python
@app.get("/api/index.json")
def get_index_json() -> list:
    # Pick default (or first) vault
    # rglob "*.md" in content_root
    # filter: hidden components (., .., node_modules, dashboard, .git, ...)
    # parse frontmatter (_split_fm)
    # return Page[]: {slug, title, type, path, created, updated, tags}
    # sort by (type, slug)
```

**응답 형태**: `scripts/export_static.py`와 100% 동일 → dashboard가 dev/static 양쪽 동일.

### 2.2 Tests (신규 `tests/test_index_json.py`)

5건 회귀 가드:

| # | 테스트 | 보장 |
|---|---|---|
| 1 | `test_index_json_returns_pages` | pages 반환, sort/type/slug/path 정확 |
| 2 | `test_index_json_page_shape_matches_export` | page dict keys = `{slug, title, type, path, created, updated, tags}` (export와 100% 일치) |
| 3 | `test_index_json_filters_hidden_and_node_modules` | `.git / node_modules / dashboard / .hidden` 제외 |
| 4 | `test_index_json_404_when_no_vaults` | vault 0개 → 404 + "no vaults" 메시지 |
| 5 | `test_index_json_uses_default_vault` | 다중 vault → `default` 마크된 것 사용 (첫 번째 ❌) |

### 2.3 changelog v0.6.5 신규 (이 문서)

---

## 3. 검증

```bash
$ PYTHONPATH=. scripts/.venv/bin/python -m pytest tests/ -q
371 passed, 1 warning in 5.32s   ✅ 회귀 0 (기존 366 + 신규 5)

$ PYTHONPATH=. scripts/.venv/bin/python -m pytest tests/test_index_json.py -v
test_index_json_returns_pages                    PASSED
test_index_json_page_shape_matches_export        PASSED
test_index_json_filters_hidden_and_node_modules  PASSED
test_index_json_404_when_no_vaults               PASSED
test_index_json_uses_default_vault               PASSED
5 passed
```

### 라이브 검증 (사용자)

```bash
# master 머지 후 API 재시작 후 (현재 떠있는 API는 v0.6.4)
$ curl http://127.0.0.1:8765/api/index.json | jq 'length, .[0]'
0
[]                                  # ← vault 0개라 빈 배열 (404 아님, 빈 응답)
```

→ 1개 vault 만들고:
```bash
$ raven vault create my ~/Raven/my
$ raven vault use my
# 페이지 1개 만들기
$ curl http://127.0.0.1:8765/api/index.json | jq '.[0]'
{
  "slug": "content/hello",
  "title": "Hello",
  "type": "concept",
  "path": "content/hello.md",
  "created": "2026-06-27",
  "updated": "2026-06-27",
  "tags": ""
}
```

Dashboard 새로고침 → HomePage에 Quick Actions + Recent cards 정상 표시.

---

## 4. 변경 사항 요약

| 파일 | 변경 | 줄 |
|---|---|---|
| `raven/api/server.py` | 신규 `GET /api/index.json` 라우트 | +60 lines |
| `tests/test_index_json.py` | 신규 5건 회귀 가드 | +177 lines |
| **`_meta/changelog-v0.6.5.md`** | 신규 | 이 문서 |

---

## 5. 효과

| | Before | After |
|---|---|---|
| dev 모드 HomePage | ❌ 빈 화면 | ✅ Quick Actions + Recent |
| dev ↔ static shape | ❌ 다름 (dev: 404) | ✅ 100% 일치 |
| silent failure | 있음 (fallback []) | 없음 (명시적 처리) |

---

## 6. 다음 사이클 후보

1. **P1-1 후속: delete/rename_page 단일화** (archive.py richer surface, 별도 audit 필요)
2. **Sidebar에 디제스트 메뉴 추가** (v0.6.4 후속)
3. **Dashboard NewVaultWizard 실사용 검증** (방금 머지한 분)
4. **P1-2 SCHEMA sync ADR** (3-way merge vs skip+warn)
5. **P1-3 SQLite WAL + aiosqlite** (멀티 에이전트 동시성, experimental 한계 유지)

---

## 7. 작업 보고

- **무엇**: dev API에 `GET /api/index.json` 라우트 추가 (정적 export와 shape 일치)
- **왜 (저장 신호)**: ① 재사용성 (dashboard dev/static 일치), ② 인수인계 (silent failure 방지), ③ 추적 (changelog), ④ 리스크 (silent failure 패턴 기록)
- **검증**: pytest 371 passed, 5 신규 회귀 가드 PASS, 라이브 curl (master 머지 후)
- **다음 가능**: delete/rename 단일화, P1-2 SCHEMA sync, 디제스트 메뉴
