---
title: Changelog v0.7.119
created: 2026-07-09
updated: 2026-07-09
type: rule
audience: agent
confidence: high
---

# v0.7.119 — wiki.db schema drift silent 500 영구 해결

## 무엇을 했는가

Dashboard 정원(Garden) 탭 silent 500 → `homelab` / `babymoa` / `hermes-infra` 3 vault의 wiki.db가 v0.7.67 이전 schema 유지. `db_is_stale()`(mtime 기반)이 drift 못 잡아 rebuild 트리거 안 됨. `db_schema_drift()` 신설 + `connect()` OR 가드.

### Fix A — `raven/core/db.py:99-167` `db_schema_drift()` 신설

**문제**: `db_is_stale()`은 markdown mtime vs db mtime만 비교. 누군가 옛 시점에 3 vault에 `raven build` 한 번 더 호출 → 옛 schema wiki.db가 mtime 더 늦음 → `db_is_stale()` False → silent 500.

**신규 함수 `db_schema_drift(vault) -> bool`**: 3개 PRAGMA 검사
1. `links` table에 `source_slug` + `target_slug` 컬럼 존재 (canonical v0.7.67+)
2. `tags` table에 `page_slug` + `tag` 컬럼 존재 (canonical M:N join)
3. `pages_fts` virtual table 존재 (FTS5 인덱스)

어느 하나라도 어긋나면 True. 검사 실패 (corrupt db / locked / permissions) 시에도 True — AGENTS.md §9 silent failure 정책 (drift로 간주 → caller가 rebuild).

### Fix B — `raven/core/db.py:99-115` `connect()` OR 가드

```python
# Before (v0.7.67~118):
if _garden.db_is_stale(vault):
    build_db(vault)

# After (v0.7.119+):
if _garden.db_is_stale(vault) or db_schema_drift(vault):
    build_db(vault)
```

### Why rebuild가 유일한 답

schema 차이가 단순 컬럼 rename이 아님:
- `pages`: 12 cols (옛) ↔ 10 cols (신) — `id/word_count/mtime` 제거, `contested/raw_content` 추가
- `tags`: `(name, count)` master ↔ `(page_slug, tag)` M:N join — **구조 자체가 다름**
- `pages_fts`: missing ↔ FTS5 virtual table 존재

→ ALTER TABLE 불가능, markdowns SoT에서 재생성만 가능.

## 왜 그렇게 했는가 (§5 4 신호)

- **재사용 가능성**: `connect()`는 5 vault × 5 진입점 (CLI/API/MCP/Dashboard/Workspace) 진입점. drift 가드 1곳 추가가 모든 표면을 자가 치유.
- **인수인계 필요성**: 다음 schema 변경 시 PR 본문에 schema 변경 명시 + `db_schema_drift()` check 항목 업데이트만 하면 자동 적용.
- **scope/provenance 추적**: v0.7.67 P0 schema 변경의 후속 작업. ADR로 정책 박음.
- **실패/리스크 기록**: silent 500은 AGENTS.md §9 P0. 다른 endpoint (search/graph/backlinks)도 동일 schema 가정인데 본 ADR로 자동 해결.

## 검증

| vault | before | after | rebuild latency |
|---|---|---|---|
| homelab | HTTP 500 | **HTTP 200** | ~0.5s |
| babymoa | HTTP 500 | **HTTP 200** | ~0.5s |
| hermes-infra | HTTP 500 | **HTTP 200** | ~0.5s |
| harumoa | HTTP 200 | HTTP 200 | 추가 비용 0 (μs PRAGMA 4회) |
| raven-dev | HTTP 200 | HTTP 200 | 추가 비용 0 |

- `py_compile raven/core/db.py` exit 0
- `db_schema_drift()` 단위 호출: 3 vault True, 2 vault False ✓
- `connect()` 호출 → rebuild 트리거 → `db_schema_drift()` False 전환 ✓
- API `/garden` 5 vault HTTP 200 ✓
- 정상 schema vault는 추가 latency 없음 (PRAGMA 4회, μs 단위)

## 후속 작업

- 3 vault rebuild 시 log.md에 `chore` audit append 가능 (선택, 본 changelog 범위 밖)
- 다른 silent 500 surface audit — 모두 `connect()` 경유라 본 ADR로 자동 해결됨
- 다음 schema 변경 시 PR 본문에 `db_schema_drift()` check 업데이트 명시