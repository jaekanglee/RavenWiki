---
title: wiki.db schema drift silent 500 영구 해결 (build_db + drift detection)
created: 2026-07-09
type: rule
tags: [adr, schema-migration, silent-failure, build-db, hotfix]
audience: agent
confidence: high
status: current
related:
  - _meta/SCHEMA.md
  - raven/core/db.py
  - raven/core/garden.py
  - raven/api/server.py
  - _meta/decisions/adr-2026-07-08-lite-bootstrap-freshness.md
  - _meta/changelog-v0.7.119.md
aliases: [adr-wiki-db-schema-migration]
---

# ADR: wiki.db schema drift silent 500 영구 해결

> **BLUF**: v0.7.67 평가 P0에서 `wiki.db` schema가 `src/dst` → `source_slug/target_slug`로 마이그레이션됐지만, **기존 3 vault (`homelab` / `babymoa` / `hermes-infra`)에 자동 migration 경로가 없었음**. `db_is_stale()`은 mtime만 비교해 drift를 못 잡았고, dashboard 정원(Garden) 탭이 모든 호출에서 silent 500. 본 ADR은 **drift detection (`db_schema_drift()`) + 자동 rebuild** hook으로 영구 해결.

## 1. 맥락 (Context)

### 1.1 문제 — 정원 탭 silent 500

2026-07-08 dashboard 정원(Garden) 탭 진입 시 "데이터를 불러오는 중 오류가 발생했습니다" 토스트(2400ms) → 빈 화면. 5 vault audit:

| vault | `/garden` HTTP | 원인 |
|---|---|---|
| raven-dev | 200 ok | canonical schema |
| harumoa | 200 ok | canonical schema |
| **homelab** | **500** | `links` = `src/dst`, `tags` = `(name, count)`, `pages_fts` 없음 |
| **babymoa** | **500** | 동일 |
| **hermes-infra** | **500** | 동일 |

→ 3 vault에서 `garden.py:83-88`의 `SELECT ... target_slug FROM links` 가 `OperationalError: no such column: target_slug`로 폭발.

### 1.2 진짜 원인 — v0.7.67 schema migration 부재

`git log` 추적:
- **v0.7.67 평가 P0 (commit f274252)** — `db.py`의 canonical schema가 `src/dst` → `source_slug/target_slug`로 변경됨
- `_INLINE_SCHEMA_SQL`, `v_backlinks` view, `scripts/build_db.py` SCHEMA_SQL 모두 새 schema 사용
- **하지만 기존 vault의 wiki.db를 자동 migration하는 코드 없음** — `connect()`는 mtime 기반 `db_is_stale()`만 호출

진짜 silent failure가 된 이유:
1. 누군가 옛 시점에 3 vault에 `raven build`를 한 번 더 호출 → 옛 schema로 wiki.db가 **재생성됨**
2. 그 빌드 mtime이 markdown mtime보다 **더 늦음** (빌드가 최근이니까)
3. `db_is_stale()` (mtime 비교) → **False** (stale 아님)
4. `connect()` → 옛 schema 그대로 read → 500

→ **mtime freshness는 schema correctness를 보장하지 않음**.

### 1.3 진짜 진단

garden.py의 SQL은 `db.py` 정의를 정확히 따랐음 (`source_slug` / `target_slug`). 잘못은 garden.py가 아니라 **schema 변경 후 migration routine 부재**. garden.py는 정상 코드, db.py도 정상 정의, **운영 상태(schema)와 코드 기대치(schema) 사이 정합성 누락**.

### 1.4 사용자 north star

- silent failure P0 (AGENTS.md §9) — 500을 사용자가 보면 안 됨
- surgical + 정당한 모순 (사용자 보고) — schema 진화는 정상, 부족한 migration이 비정상
- Lite bootstrap freshness (ADR-2026-07-08)와 같은 정책 패턴: "stale 감지 + 자동 보정 + 사람 알림 (선택)"

## 2. 결정 (Decision)

### 2.1 `db_schema_drift(vault) -> bool` 신설

`raven/core/db.py`에 신규 함수. wiki.db가 canonical schema와 일치하는지 3개 PRAGMA 검사:

```python
def db_schema_drift(vault: Vault) -> bool:
    if not vault.db_path.exists():
        return False  # connect() handles "missing" via build_db directly
    try:
        conn = sqlite3.connect(f"file:{vault.db_path}?mode=ro", uri=True)
        try:
            # 1. links.source_slug + target_slug (canonical)
            cols = {row[1] for row in conn.execute("PRAGMA table_info(links)").fetchall()}
            if not {"source_slug", "target_slug"}.issubset(cols):
                return True
            # 2. tags.page_slug + tag (canonical M:N join)
            tag_cols = {row[1] for row in conn.execute("PRAGMA table_info(tags)").fetchall()}
            if not {"page_slug", "tag"}.issubset(tag_cols):
                return True
            # 3. pages_fts virtual table 존재
            fts_exists = conn.execute(
                "SELECT 1 FROM sqlite_master "
                "WHERE type='table' AND name='pages_fts' LIMIT 1"
            ).fetchone()
            if fts_exists is None:
                return True
            return False
        finally:
            conn.close()
    except Exception:
        # AGENTS.md §9 silent failure policy — inspection 실패 = drift로 간주
        # (corrupt db, locked, permissions 다 rebuild로 self-heal)
        return True
```

### 2.2 `connect()` 자동 rebuild hook

```python
# v0.7.119+: drift OR stale 둘 중 하나라도 True면 rebuild
if _garden.db_is_stale(vault) or db_schema_drift(vault):
    build_db(vault)
```

**rebuild가 유일한 답인 이유**: schema 차이가 단순 컬럼 rename이 아님:
- `pages`: 12 cols (옛) ↔ 10 cols (신) — `id/word_count/mtime` 제거, `contested/raw_content` 추가
- `tags`: `(name, count)` master table ↔ `(page_slug, tag)` M:N join — **구조 자체가 다름**
- `pages_fts`: missing ↔ FTS5 virtual table 존재

→ ALTER TABLE 불가능, **markdowns SoT에서 재생성**이 유일. 빌드 후 옛 db는 overwrite.

### 2.3 mtime vs schema freshness 분리

기존 `db_is_stale()`: **시간 신선도** (markdown이 db보다 최신 = rebuild)
신규 `db_schema_drift()`: **구조 신선도** (db schema ≠ canonical = rebuild)

두 가드는 OR 조건. 한쪽이라도 어긋나면 rebuild. Lite bootstrap freshness 가드(ADR-2026-07-08)와 같은 "stale 감지 + 자동 보정" 패턴.

### 2.4 silent failure 정책 준수

`db_schema_drift()`는 어떤 검사 실패에서도 False (drift 없음) 반환 ❌ — **True (drift 있음) 반환** ⭕. AGENTS.md §9 "silent failure > 잘못된 메시지 > 메시지 누락" 정책 그대로:
- corrupt db → drift → rebuild → 자가 치유
- locked db → drift → rebuild 시도 (lock 풀린 후 성공 가능)
- permissions 오류 → drift → rebuild 시도

### 2.5 비용

- 첫 호출 시 (3 vault) 1회 rebuild → 비용 ~1초 / vault. 그 후론 normal operation.
- 정상 schema vault (harumoa, raven-dev)는 추가 비용 0 — PRAGMA 4회 (μs 수준).
- markdown SoT가 rebuild의 단일 source of truth이므로 **데이터 손실 없음** (link 관계는 markdown wikilink `[[...]]`에서 재생성).

## 3. 결과 (Consequences)

### 긍정
- 3 vault silent 500 → 정원 탭 정상 작동
- 다음 schema 변경 시에도 `db_schema_drift()`가 3줄 추가만으로 가드 확장 가능
- Lite bootstrap freshness + 본 ADR 2개가 **"stale 감지 + 자동 보정"** 패턴의 정식 정책화
- AGENTS.md §9 silent failure 정책 일관성 회복

### 부정 / 비용
- 첫 호출 시 rebuild latency (~1초) — 사용자가 "garden 탭 누르고 1초 후 로딩" 느낌 (이전엔 즉시 500이었으니 trade-up)
- rebuild 시 `wiki.db.backup` 자동 갱신 (기존 동작) → 마지막 정상 db 1개 보존

### 후속 작업
- **다음 schema 변경 시 PR**: PR 본문에 schema 변경 명시 + `db_schema_drift()` 의 3 check 중 해당하는 항목 업데이트
- 3 vault rebuild 시 log.md에 `chore` audit append 가능 (선택, 본 ADR 범위 밖)
- 다른 silent 500 surface audit (search/graph/backlinks endpoint) — `homelab`/`babymoa`/`hermes-infra`에서 동일 schema 가정 사용 (L147/152/166/190/196 server.py, L185 garden.py, L284/298/310 build_db.py 등) — 모두 `connect()` 경유이므로 본 ADR로 자동 해결됨

## 4. 변경 파일

- `raven/core/db.py` — `db_schema_drift()` 신설 + `connect()` OR 가드 (1 함수 + 2줄)
- 본 ADR (신규)
- `_meta/changelog-v0.7.119.md` (신규)

## 5. references

- `raven/core/db.py` L99-115 (`connect()` 진입점, v0.7.67 mtime 가드)
- `raven/core/db.py` L184-219 (`_INLINE_SCHEMA_SQL` canonical 정의)
- `raven/core/garden.py` L73-110 (`get_orphan_pages` — drift 시 폭발 지점)
- `raven/api/server.py` L1940-1980 (`/api/vaults/{}/garden` endpoint)
- `scripts/build_db.py` L60-67 (canonical links schema)
- commit `f274252` (v0.7.67 평가 P0, schema 변경 시점)
- commit `8d5bb9d` (v0.7.117, dashboard lint rebuild hotfix — 본 ADR과 같은 silent-failure hotfix 계열)
- ADR-2026-07-08-lite-bootstrap-freshness (stale 감지 + 자동 보정 패턴 선례)
- AGENTS.md §9 (silent failure 정책), §15 (자가 평가)