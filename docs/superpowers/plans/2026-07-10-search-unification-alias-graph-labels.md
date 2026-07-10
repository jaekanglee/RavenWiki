# 검색 통합 + Alias 구조적 지원 + 그래프 라벨 개선 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 사이드바 전체 문서 검색과 PropertiesPanel 연결 문서 검색을 동일한 로직(hybrid-search)으로 통합하고, alias를 검색 인덱스와 편집 UI에 정식 반영하고, 그래프 뷰의 긴 노드 라벨을 잘라서 표시 + 호버 시 전체 제목을 보여준다.

**Architecture:** 프론트엔드는 공용 훅 `useHybridSearch`로 두 검색 UI의 fetch/debounce 로직을 단일화한다. 백엔드는 FTS5 인덱스(`pages_fts`)에 `aliases` 컬럼을 추가해 alias 텍스트가 BM25 매칭 대상이 되도록 하고, PropertiesPanel에는 `tags`와 동일한 칩 UI로 `aliases` 편집을 추가한다(기존 `extra_meta` 프론트매터 병합 경로를 그대로 재사용, 백엔드 스키마 변경 불필요). 그래프는 캔버스 라벨 렌더 루프에 `ctx.measureText` 기반 말줄임 자르기와, 호버/포커스 노드에 대한 배경 박스 전체 제목 표시를 추가한다.

**Tech Stack:** React + TypeScript (Vite, dashboard/), FastAPI + SQLite/FTS5 (raven/, Python), force-graph 캔버스 렌더링, pytest, vitest.

## Global Constraints

- 스펙 문서: `docs/superpowers/specs/2026-07-10-search-unification-alias-graph-labels-design.md` — 모든 태스크는 이 문서의 A/B/C 섹션에 대응한다.
- 기존 단순 검색 엔드포인트 `/api/vaults/{name}/search` (`raven/api/server.py:2549`)는 삭제하지 않는다 — `tests/test_search_excludes_autoindex.py`가 이 엔드포인트를 직접 테스트하고 있어 존치 대상으로 확정됨 (스펙 B의 "다른 호출자 확인 후 결정" 조건 해소).
- LLM 발행 지침(`SCHEMA.md` 등) 강화는 범위 밖 — 건드리지 않는다.
- 프론트엔드 커밋 전 `cd dashboard && npx tsc -b --noEmit` (또는 `npm run build`) 통과 확인. 백엔드 커밋 전 관련 pytest 통과 확인.

---

### Task 1: FTS5 인덱스에 aliases 컬럼 추가 (백엔드)

**Files:**
- Modify: `scripts/build_db.py:100-135` (SCHEMA_SQL의 `pages_fts` 가상 테이블 + 3개 트리거)
- Modify: `raven/core/db.py:316` (`_INLINE_SCHEMA_SQL`의 `pages_fts` 정의), `raven/core/db.py:387-391` (`_inline_build`의 수동 INSERT)
- Test: `tests/test_hybrid_search.py` (기존 파일에 테스트 추가)

**Interfaces:**
- Consumes: 없음 (스키마/DDL 변경, 기존 `aliases_to_json`/`normalize_aliases` 그대로 사용).
- Produces: `pages_fts` 가상 테이블에 5번째 컬럼 `aliases`가 생겨 `pages_fts MATCH ?` 쿼리(비한정 컬럼 매치)가 alias 텍스트도 검색 대상으로 포함한다. 이후 태스크는 이 컬럼 변경에 의존하지 않는다 (쿼리 SQL 자체는 무수정).

- [ ] **Step 1: 실패하는 테스트 작성 (alias로 검색되는지)**

`tests/test_hybrid_search.py` 파일 끝(`test_mcp_hybrid_search_registered` 함수 뒤)에 추가:

```python
def test_hybrid_search_matches_alias(isolated_vault: Vault) -> None:
    """title/본문에는 없는 검색어라도 aliases frontmatter에 있으면 검색되어야 한다 (FTS5 aliases 컬럼)."""
    content_dir = isolated_vault.root / "content"
    (content_dir / "doc-c.md").write_text(
        "---\ntitle: 인증 가이드\ntype: concept\ntags: [auth]\naliases: [ZanzibarAuthZ]\n---\n"
        "권한 부여 흐름을 설명한다.\n",
        encoding="utf-8",
    )
    db_module.build_db(isolated_vault, run_lint=False)

    results = hybrid_search(isolated_vault, "ZanzibarAuthZ", limit=5)
    assert len(results) >= 1
    assert results[0]["slug"] == "content/doc-c"


def test_inline_build_fts_includes_alias(tmp_path) -> None:
    """설치 패키지 fallback 빌더(_inline_build)도 pages_fts에 aliases를 포함해야
    한다 — 두 빌더 간 스키마 drift는 과거 실제 버그였다 (db.py 상단 문서 참고)."""
    import sqlite3
    from raven.core.vault import Vault
    from raven.core.db import _inline_build

    vault = Vault.create("inline-test", tmp_path / "vault", bootstrap=False)
    content_dir = vault.root / "content"
    content_dir.mkdir(parents=True, exist_ok=True)
    (content_dir / "doc-d.md").write_text(
        "---\ntitle: 결제 가이드\ntype: concept\ntags: [pay]\naliases: [PayGateway]\n---\n"
        "결제 처리 흐름.\n",
        encoding="utf-8",
    )

    db_path = tmp_path / "wiki.db"
    _inline_build(vault, db_path)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT slug FROM pages_fts WHERE pages_fts MATCH ?", ("PayGateway",)
    ).fetchall()
    conn.close()
    assert [r["slug"] for r in rows] == ["content/doc-d"]
```

- [ ] **Step 2: 테스트 실행 → 실패 확인**

Run: `cd /Users/jaekanglee/Dev/Project/Raven && python3 -m pytest tests/test_hybrid_search.py::test_hybrid_search_matches_alias tests/test_hybrid_search.py::test_inline_build_fts_includes_alias -v`
Expected: 둘 다 FAIL — `results`/`rows`가 비어 있음 (aliases가 아직 FTS 인덱스에 없음).

- [ ] **Step 3: `scripts/build_db.py`의 `pages_fts` 스키마 + 트리거에 aliases 추가**

`scripts/build_db.py:100-135`의 다음 블록을 교체:

```python
CREATE VIRTUAL TABLE pages_fts USING fts5(
  slug, title, tags_concat, content
);

CREATE TRIGGER pages_ai AFTER INSERT ON pages BEGIN
  INSERT INTO pages_fts(rowid, slug, title, tags_concat, content)
  VALUES (
    new.rowid, new.slug, new.title,
    COALESCE((SELECT GROUP_CONCAT(tag, ' ') FROM tags WHERE page_slug = new.slug), ''),
    new.content
  );
END;

CREATE TRIGGER pages_ad AFTER DELETE ON pages BEGIN
  DELETE FROM pages_fts WHERE rowid = old.rowid;
END;

CREATE TRIGGER pages_au AFTER UPDATE ON pages BEGIN
  DELETE FROM pages_fts WHERE rowid = old.rowid;
  INSERT INTO pages_fts(rowid, slug, title, tags_concat, content)
  VALUES (
    new.rowid, new.slug, new.title,
    COALESCE((SELECT GROUP_CONCAT(tag, ' ') FROM tags WHERE page_slug = new.slug), ''),
    new.content
  );
END;

CREATE TRIGGER tags_ai AFTER INSERT ON tags BEGIN
  -- refresh FTS row for this page so new tag joins the index
  DELETE FROM pages_fts WHERE rowid = (SELECT rowid FROM pages WHERE slug = new.page_slug);
  INSERT INTO pages_fts(rowid, slug, title, tags_concat, content)
  SELECT p.rowid, p.slug, p.title,
         COALESCE((SELECT GROUP_CONCAT(tag, ' ') FROM tags WHERE page_slug = p.slug), ''),
         p.content
  FROM pages p WHERE p.slug = new.page_slug;
END;
```

with:

```python
CREATE VIRTUAL TABLE pages_fts USING fts5(
  slug, title, tags_concat, content, aliases
);

CREATE TRIGGER pages_ai AFTER INSERT ON pages BEGIN
  INSERT INTO pages_fts(rowid, slug, title, tags_concat, content, aliases)
  VALUES (
    new.rowid, new.slug, new.title,
    COALESCE((SELECT GROUP_CONCAT(tag, ' ') FROM tags WHERE page_slug = new.slug), ''),
    new.content, new.aliases
  );
END;

CREATE TRIGGER pages_ad AFTER DELETE ON pages BEGIN
  DELETE FROM pages_fts WHERE rowid = old.rowid;
END;

CREATE TRIGGER pages_au AFTER UPDATE ON pages BEGIN
  DELETE FROM pages_fts WHERE rowid = old.rowid;
  INSERT INTO pages_fts(rowid, slug, title, tags_concat, content, aliases)
  VALUES (
    new.rowid, new.slug, new.title,
    COALESCE((SELECT GROUP_CONCAT(tag, ' ') FROM tags WHERE page_slug = new.slug), ''),
    new.content, new.aliases
  );
END;

CREATE TRIGGER tags_ai AFTER INSERT ON tags BEGIN
  -- refresh FTS row for this page so new tag joins the index
  DELETE FROM pages_fts WHERE rowid = (SELECT rowid FROM pages WHERE slug = new.page_slug);
  INSERT INTO pages_fts(rowid, slug, title, tags_concat, content, aliases)
  SELECT p.rowid, p.slug, p.title,
         COALESCE((SELECT GROUP_CONCAT(tag, ' ') FROM tags WHERE page_slug = p.slug), ''),
         p.content, p.aliases
  FROM pages p WHERE p.slug = new.page_slug;
END;
```

(`pages` 테이블은 이미 `aliases TEXT NOT NULL DEFAULT '[]'` 컬럼과 INSERT 시 `:aliases` 바인딩을 갖고 있으므로 — `scripts/build_db.py:56,289-296` — 파이썬 INSERT 코드는 수정할 필요 없다. 트리거가 `new.aliases`/`p.aliases`로 자동으로 값을 가져간다.)

- [ ] **Step 4: `raven/core/db.py`의 inline fallback 빌더에 aliases 추가**

`raven/core/db.py:316`을 교체:

```python
CREATE VIRTUAL TABLE pages_fts USING fts5(slug, title, tags_concat, content);
```

→

```python
CREATE VIRTUAL TABLE pages_fts USING fts5(slug, title, tags_concat, content, aliases);
```

그리고 `raven/core/db.py:387-391`을 교체:

```python
        con.execute(
            "INSERT INTO pages_fts (rowid, slug, title, tags_concat, content) "
            "VALUES (last_insert_rowid(), ?, ?, ?, ?)",
            (slug, title, " ".join(str(t) for t in tags) if isinstance(tags, (list, tuple)) else "", body),
        )
```

→

```python
        con.execute(
            "INSERT INTO pages_fts (rowid, slug, title, tags_concat, content, aliases) "
            "VALUES (last_insert_rowid(), ?, ?, ?, ?, ?)",
            (slug, title, " ".join(str(t) for t in tags) if isinstance(tags, (list, tuple)) else "", body, aliases),
        )
```

(`aliases` 변수는 바로 위 `raven/core/db.py:371`에서 이미 `aliases = aliases_to_json(meta.get("aliases"))`로 계산돼 있다.)

- [ ] **Step 5: 테스트 재실행 → 통과 확인**

Run: `cd /Users/jaekanglee/Dev/Project/Raven && python3 -m pytest tests/test_hybrid_search.py -v`
Expected: 전체 PASS (기존 테스트 포함, 회귀 없음).

- [ ] **Step 6: 관련 회귀 테스트 실행**

Run: `cd /Users/jaekanglee/Dev/Project/Raven && python3 -m pytest tests/test_search_excludes_autoindex.py tests/test_db_build_relations.py tests/test_db_build_result.py -v`
Expected: 전체 PASS (스키마 변경이 다른 빌드/검색 경로를 깨지 않았는지 확인).

- [ ] **Step 7: 커밋**

```bash
git add scripts/build_db.py raven/core/db.py tests/test_hybrid_search.py
git commit -m "search: FTS5 인덱스에 aliases 컬럼 추가 — alias로도 문서 검색 가능"
```

---

### Task 2: 공용 검색 훅 `useHybridSearch` + `fetchHybridSearch` abort 지원

**Files:**
- Modify: `dashboard/src/lib/api.ts:781-792` (`fetchHybridSearch`에 옵션 파라미터 추가)
- Create: `dashboard/src/lib/useHybridSearch.ts`
- Test: `dashboard/src/lib/useHybridSearch.test.ts`

**Interfaces:**
- Consumes: `HybridSearchResult` 타입 (`dashboard/src/lib/api.ts:771-779`), `useDebounced` (`dashboard/src/lib/useDebounced.ts`).
- Produces: `useHybridSearch(vault: string, query: string, opts?: { limit?: number; excludeSlug?: string }): HybridSearchResult[]` — Task 3, 4가 이 훅을 소비한다.

- [ ] **Step 1: `fetchHybridSearch`에 `signal` 옵션 추가**

`dashboard/src/lib/api.ts:781-792`을 교체:

```typescript
export async function fetchHybridSearch(
  vault: string,
  query: string,
  limit: number = 20
): Promise<HybridSearchResult[]> {
  const r = await fetch(
    `/api/vaults/${encodeURIComponent(vault)}/hybrid-search?query=${encodeURIComponent(query)}&limit=${limit}`
  );
  if (!r.ok) return [];
  const d = await r.json();
  return d.results || [];
}
```

→

```typescript
export async function fetchHybridSearch(
  vault: string,
  query: string,
  limit: number = 20,
  opts: { signal?: AbortSignal } = {}
): Promise<HybridSearchResult[]> {
  const r = await fetch(
    `/api/vaults/${encodeURIComponent(vault)}/hybrid-search?query=${encodeURIComponent(query)}&limit=${limit}`,
    { signal: opts.signal }
  );
  if (!r.ok) return [];
  const d = await r.json();
  return d.results || [];
}
```

- [ ] **Step 2: 실패하는 훅 테스트 작성**

Create `dashboard/src/lib/useHybridSearch.test.ts`:

```typescript
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { useHybridSearch } from "./useHybridSearch";

describe("useHybridSearch", () => {
  beforeEach(() => {
    vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout"] });
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it("returns empty results for a blank query without fetching", () => {
    const fetchSpy = vi.spyOn(global, "fetch");
    const { result } = renderHook(() => useHybridSearch("vault1", ""));
    expect(result.current).toEqual([]);
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("debounces then fetches hybrid-search results", async () => {
    const fetchSpy = vi.spyOn(global, "fetch").mockResolvedValue({
      ok: true,
      json: async () => ({
        results: [{ slug: "content/a", title: "A", type: "concept", score: 1, bm25_score: 1, distance: 0, method: "hybrid" }],
      }),
    } as Response);

    const { result, rerender } = renderHook(
      ({ q }) => useHybridSearch("vault1", q, { limit: 8 }),
      { initialProps: { q: "" } }
    );
    rerender({ q: "hello" });

    await vi.advanceTimersByTimeAsync(220);
    await waitFor(() => expect(result.current.length).toBe(1));

    expect(fetchSpy).toHaveBeenCalledWith(
      expect.stringContaining("/api/vaults/vault1/hybrid-search?query=hello&limit=8"),
      expect.anything()
    );
    expect(result.current[0].slug).toBe("content/a");
  });

  it("filters out excludeSlug from results", async () => {
    vi.spyOn(global, "fetch").mockResolvedValue({
      ok: true,
      json: async () => ({
        results: [
          { slug: "content/self", title: "Self", type: "concept", score: 1, bm25_score: 1, distance: 0, method: "hybrid" },
          { slug: "content/other", title: "Other", type: "concept", score: 1, bm25_score: 1, distance: 0, method: "hybrid" },
        ],
      }),
    } as Response);

    const { result, rerender } = renderHook(
      ({ q }) => useHybridSearch("vault1", q, { excludeSlug: "content/self" }),
      { initialProps: { q: "" } }
    );
    rerender({ q: "term" });

    await vi.advanceTimersByTimeAsync(220);
    await waitFor(() => expect(result.current.length).toBe(1));
    expect(result.current[0].slug).toBe("content/other");
  });
});
```

- [ ] **Step 3: 테스트 실행 → 실패 확인 (모듈 없음)**

Run: `cd dashboard && npx vitest run src/lib/useHybridSearch.test.ts`
Expected: FAIL — `Cannot find module './useHybridSearch'` (또는 `@testing-library/react` 미설치 시 별도 에러 — Step 3-1 참고).

- [ ] **Step 3-1: 테스트 의존성 확인/설치**

`@testing-library/react`가 없다면 설치:

Run: `cd dashboard && test -d node_modules/@testing-library/react && echo present || npm install -D @testing-library/react`
Expected: `present` 이거나 설치 완료.

- [ ] **Step 4: `useHybridSearch` 훅 구현**

Create `dashboard/src/lib/useHybridSearch.ts`:

```typescript
// useHybridSearch — SearchBar(사이드바)와 PropertiesPanel(연결 문서 검색)이 공유하는
// 검색 훅. 두 UI가 완전히 동일한 결과를 얻도록 fetch/디바운스/AbortController
// 로직을 한 곳으로 모은다 (§A 검색 로직 통합, 2026-07-10 스펙).
import { useEffect, useState } from "react";
import { fetchHybridSearch, type HybridSearchResult } from "./api";
import { useDebounced } from "./useDebounced";

export function useHybridSearch(
  vault: string,
  query: string,
  opts: { limit?: number; excludeSlug?: string } = {}
): HybridSearchResult[] {
  const { limit = 8, excludeSlug } = opts;
  const [results, setResults] = useState<HybridSearchResult[]>([]);
  const debouncedQuery = useDebounced(query, 220);

  useEffect(() => {
    if (!debouncedQuery.trim()) {
      setResults([]);
      return;
    }
    const ctrl = new AbortController();
    fetchHybridSearch(vault, debouncedQuery, limit, { signal: ctrl.signal })
      .then((hits) => {
        setResults(excludeSlug ? hits.filter((h) => h.slug !== excludeSlug) : hits);
      })
      .catch(() => {});
    return () => ctrl.abort();
  }, [vault, debouncedQuery, limit, excludeSlug]);

  return results;
}
```

- [ ] **Step 5: 테스트 재실행 → 통과 확인**

Run: `cd dashboard && npx vitest run src/lib/useHybridSearch.test.ts`
Expected: 3개 테스트 모두 PASS.

- [ ] **Step 6: 타입체크**

Run: `cd dashboard && npx tsc -b --noEmit`
Expected: 에러 없음.

- [ ] **Step 7: 커밋**

```bash
git add dashboard/src/lib/api.ts dashboard/src/lib/useHybridSearch.ts dashboard/src/lib/useHybridSearch.test.ts dashboard/package.json dashboard/package-lock.json
git commit -m "dashboard: useHybridSearch 공용 검색 훅 추가 (SearchBar/PropertiesPanel 통합용)"
```

---

### Task 3: SearchBar.tsx를 `useHybridSearch`로 전환

**Files:**
- Modify: `dashboard/src/components/SearchBar.tsx`

**Interfaces:**
- Consumes: `useHybridSearch(vault, query, opts)` (Task 2).
- Produces: 사이드바 검색이 PropertiesPanel과 동일한 `/hybrid-search` 결과를 사용 — Task 4와 나란히 "동일 로직" 요구사항을 만족한다.

- [ ] **Step 1: import 교체**

`dashboard/src/components/SearchBar.tsx:1-4`를 교체:

```typescript
import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { SearchResultItem } from "./SearchResultItem";
import { useDebounced } from "../lib/useDebounced";
```

→

```typescript
import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { SearchResultItem } from "./SearchResultItem";
import { useHybridSearch } from "../lib/useHybridSearch";
```

- [ ] **Step 2: 로컬 fetch/debounce 로직을 훅 호출로 교체**

`dashboard/src/components/SearchBar.tsx:28-29`의:

```typescript
  const [q, setQ] = useState("");
  const [results, setResults] = useState<any[]>([]);
```

→

```typescript
  const [q, setQ] = useState("");
```

그리고 `dashboard/src/components/SearchBar.tsx:80-95`의:

```typescript
  // Debounced fetch with AbortController.
  const debouncedQ = useDebounced(q, 220);
  useEffect(() => {
    if (!debouncedQ.trim()) {
      setResults([]);
      return;
    }
    const ctrl = new AbortController();
    fetch(`/api/vaults/${vault}/search?q=${encodeURIComponent(debouncedQ)}&top_k=8`, {
      signal: ctrl.signal,
    })
      .then((r) => (r.ok ? r.json() : { results: [] }))
      .then((d) => setResults(d.results || []))
      .catch(() => setResults([]));
    return () => ctrl.abort();
  }, [debouncedQ, vault]);
```

→

```typescript
  // v0.7.201+: PropertiesPanel 연결 문서 검색과 동일한 hybrid-search 결과를
  // 공유 (§A 검색 로직 통합, 2026-07-10 스펙) — 중복 fetch/debounce 제거.
  const results = useHybridSearch(vault, q, { limit: 8 });
```

- [ ] **Step 3: 나머지 코드는 무수정 확인**

`results` 상태가 이제 훅 반환값이므로 `setResults`를 호출하던 다른 곳이 없는지 확인.

Run: `cd dashboard && grep -n "setResults" src/components/SearchBar.tsx`
Expected: 결과 없음 (아무 출력도 없어야 함).

- [ ] **Step 4: 타입체크**

Run: `cd dashboard && npx tsc -b --noEmit`
Expected: 에러 없음 (`results`가 `HybridSearchResult[]`이고 `SearchResultItem`은 `result: any`를 받으므로 타입 충돌 없음).

- [ ] **Step 5: 수동 동작 확인**

Run: `cd dashboard && npm run dev` (백그라운드 실행 후) 브라우저에서 사이드바 검색창에 쿼리 입력 → PropertiesPanel의 "연결할 문서 검색"에 같은 쿼리를 입력했을 때 동일한 문서 목록이 나오는지 비교.
Expected: 두 검색 결과 목록이 동일한 슬러그/순서로 나온다 (스니펫은 사이드바에서 더는 표시되지 않음 — hybrid-search 응답에는 `snippet` 필드가 없어 `SearchResultItem`의 `result.snippet && ...`가 자연히 스킵됨. 이는 스펙에서 승인한 "완전히 동일한 결과" 요구사항의 직접적 귀결).

- [ ] **Step 6: 커밋**

```bash
git add dashboard/src/components/SearchBar.tsx
git commit -m "dashboard: 사이드바 검색을 hybrid-search로 전환 (PropertiesPanel과 로직 통합)"
```

---

### Task 4: PropertiesPanel.tsx 연결 문서 검색을 `useHybridSearch`로 정리

**Files:**
- Modify: `dashboard/src/components/PropertiesPanel.tsx`

**Interfaces:**
- Consumes: `useHybridSearch(vault, query, opts)` (Task 2).
- Produces: 없음 (내부 리팩터링) — Task 5가 이 파일을 계속 수정한다.

- [ ] **Step 1: import 교체**

`dashboard/src/components/PropertiesPanel.tsx:5-9`를 교체:

```typescript
import { useState, useEffect, useRef, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { updatePage, addRelation } from "../lib/api";
import { useDebounced } from "../lib/useDebounced";
import type { Page } from "../types";
```

→

```typescript
import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { updatePage, addRelation } from "../lib/api";
import { useHybridSearch } from "../lib/useHybridSearch";
import type { Page } from "../types";
```

(`useRef`는 이 파일에서 relation 검색 debounce 외 용도로 쓰이지 않으므로 함께 제거 — Step 3에서 사용처 없음을 확인한다.)

- [ ] **Step 2: relation 검색 state/effect를 훅 호출로 교체**

`dashboard/src/components/PropertiesPanel.tsx:68-73`의:

```typescript
  // ── relation 연결 ──────────────────────────────────────────────────────────
  const [relQuery, setRelQuery] = useState("");
  const [relResults, setRelResults] = useState<{ slug: string; title: string; type: string }[]>([]);
  const [relType, setRelType] = useState<string>("references");
  const [relSaving, setRelSaving] = useState(false);
  const [relToast, setRelToast] = useState<string | null>(null);
  const debouncedRelQuery = useDebounced(relQuery, 220);
```

→

```typescript
  // ── relation 연결 ──────────────────────────────────────────────────────────
  const [relQuery, setRelQuery] = useState("");
  const [relType, setRelType] = useState<string>("references");
  const [relSaving, setRelSaving] = useState(false);
  const [relToast, setRelToast] = useState<string | null>(null);
  // v0.7.201+: 사이드바 SearchBar와 동일한 훅 — 결과 100% 동일 보장.
  const relResults = useHybridSearch(vault, relQuery, { limit: 8, excludeSlug: page.slug });
```

그리고 `dashboard/src/components/PropertiesPanel.tsx:120-135`의:

```typescript
  // ── 문서 검색 — SearchPage와 동일한 hybrid-search (220ms debounce, AbortController)
  useEffect(() => {
    if (!debouncedRelQuery.trim()) { setRelResults([]); return; }
    const ctrl = new AbortController();
    fetch(
      `/api/vaults/${encodeURIComponent(vault)}/hybrid-search?query=${encodeURIComponent(debouncedRelQuery)}&limit=8`,
      { signal: ctrl.signal }
    )
      .then(r => r.ok ? r.json() : { results: [] })
      .then(d => {
        const hits = (d.results || []) as { slug: string; title: string; type: string }[];
        setRelResults(hits.filter(h => h.slug !== page.slug));
      })
      .catch(() => {});
    return () => ctrl.abort();
  }, [debouncedRelQuery, vault, page.slug]);
```

→ (전체 삭제, 훅이 대체함)

- [ ] **Step 3: `handleAddRelation`에서 검색 결과 초기화 방식 확인**

`dashboard/src/components/PropertiesPanel.tsx:149-150`에 `setRelResults([]);` 호출이 있는데 이제 `relResults`는 훅 반환값이라 직접 set할 수 없다. 해당 줄을 제거하고 `setRelQuery("")`만 남긴다 (쿼리를 비우면 훅이 자동으로 빈 배열을 반환함, `useHybridSearch.ts`의 `if (!debouncedQuery.trim()) { setResults([]); ...}` 로직).

`dashboard/src/components/PropertiesPanel.tsx:138-158`의:

```typescript
  async function handleAddRelation(target: { slug: string; title: string }) {
    setRelSaving(true);
    try {
      await addRelation(vault, {
        source_slug: page.slug,
        target_slug: target.slug,
        relation_type: relType,
        actor: "user",
      });
      setRelToast(`✅ ${target.title} 연결됨`);
      setTimeout(() => setRelToast(null), 2400);
      setRelQuery("");
      setRelResults([]);
      onSaved();
    } catch (e: any) {
      setRelToast(`오류: ${e.message}`);
      setTimeout(() => setRelToast(null), 2400);
    } finally {
      setRelSaving(false);
    }
  }
```

→

```typescript
  async function handleAddRelation(target: { slug: string; title: string }) {
    setRelSaving(true);
    try {
      await addRelation(vault, {
        source_slug: page.slug,
        target_slug: target.slug,
        relation_type: relType,
        actor: "user",
      });
      setRelToast(`✅ ${target.title} 연결됨`);
      setTimeout(() => setRelToast(null), 2400);
      setRelQuery("");
      onSaved();
    } catch (e: any) {
      setRelToast(`오류: ${e.message}`);
      setTimeout(() => setRelToast(null), 2400);
    } finally {
      setRelSaving(false);
    }
  }
```

- [ ] **Step 4: 타입체크**

Run: `cd dashboard && npx tsc -b --noEmit`
Expected: 에러 없음. (남아있는 `useRef`/`useDebounced` import나 미사용 변수가 있으면 여기서 드러난다.)

- [ ] **Step 5: 수동 동작 확인**

문서 페이지를 열어 PropertiesPanel의 "문서 연결" 검색창에 쿼리를 입력했을 때 기존과 동일하게 결과가 뜨고, 클릭 시 관계가 추가되는지 확인 (회귀 없음).

- [ ] **Step 6: 커밋**

```bash
git add dashboard/src/components/PropertiesPanel.tsx
git commit -m "dashboard: PropertiesPanel 연결 문서 검색을 공용 useHybridSearch 훅으로 정리"
```

---

### Task 5: PropertiesPanel에 alias 편집 UI 추가

**Files:**
- Modify: `dashboard/src/components/PropertiesPanel.tsx`

**Interfaces:**
- Consumes: `Page.aliases?: string[]` (`dashboard/src/types.ts:16`), `updatePage(vault, slug, { ..., extra_meta })` (`dashboard/src/lib/api.ts:151-163` — `extra_meta`는 `raven.core.contracts.write_page`를 통해 프론트매터에 병합되므로 백엔드 변경 불필요).
- Produces: 없음 (leaf UI 변경).

- [ ] **Step 1: `TagPill`을 범용 `Pill`로 일반화**

`dashboard/src/components/PropertiesPanel.tsx:31-49`의:

```typescript
// ── 단일 태그 pill ──────────────────────────────────────────────────────────
function TagPill({ tag, onRemove }: { tag: string; onRemove: () => void }) {
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", gap: 4,
      padding: "2px 8px", borderRadius: 12, fontSize: 12, fontWeight: 500,
      background: "rgba(99,102,241,0.12)", color: "var(--color-primary)",
      border: "1px solid rgba(99,102,241,0.25)",
    }}>
      #{tag}
      <button
        type="button"
        aria-label={`태그 ${tag} 제거`}
        onClick={onRemove}
        style={{ background: "none", border: "none", cursor: "pointer", padding: 0, lineHeight: 1, color: "var(--color-muted)", fontSize: 13 }}
      >×</button>
    </span>
  );
}
```

→

```typescript
// ── 단일 pill (tags/aliases 공용) ────────────────────────────────────────────
function Pill({ text, prefix = "", removeLabel, onRemove }: {
  text: string; prefix?: string; removeLabel: string; onRemove: () => void;
}) {
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", gap: 4,
      padding: "2px 8px", borderRadius: 12, fontSize: 12, fontWeight: 500,
      background: "rgba(99,102,241,0.12)", color: "var(--color-primary)",
      border: "1px solid rgba(99,102,241,0.25)",
    }}>
      {prefix}{text}
      <button
        type="button"
        aria-label={removeLabel}
        onClick={onRemove}
        style={{ background: "none", border: "none", cursor: "pointer", padding: 0, lineHeight: 1, color: "var(--color-muted)", fontSize: 13 }}
      >×</button>
    </span>
  );
}
```

- [ ] **Step 2: tags 렌더 부분에서 `Pill` 사용하도록 갱신**

`dashboard/src/components/PropertiesPanel.tsx:214-216`(현재 `<TagPill key={t} tag={t} onRemove={() => handleRemoveTag(t)} />` 렌더 부분)을:

```typescript
              {tags.map(t => (
                <TagPill key={t} tag={t} onRemove={() => handleRemoveTag(t)} />
              ))}
```

→

```typescript
              {tags.map(t => (
                <Pill key={t} text={t} prefix="#" removeLabel={`태그 ${t} 제거`} onRemove={() => handleRemoveTag(t)} />
              ))}
```

- [ ] **Step 3: aliases state 추가 + page 동기화**

`dashboard/src/components/PropertiesPanel.tsx:60-66`(tags state 선언부) 바로 뒤에 추가:

```typescript
  // ── aliases ───────────────────────────────────────────────────────────────
  const [aliases, setAliases] = useState<string[]>(() => page.aliases || []);
  const [aliasInput, setAliasInput] = useState("");
  const [aliasSaving, setAliasSaving] = useState(false);
```

`dashboard/src/components/PropertiesPanel.tsx:76-79`의:

```typescript
  // page가 바뀌면 state 동기화
  useEffect(() => {
    setType(page.type || "concept");
    setTags((page.tags || "").split(",").map(t => t.trim().replace(/^#/, "")).filter(Boolean));
  }, [page.slug]);
```

→

```typescript
  // page가 바뀌면 state 동기화
  useEffect(() => {
    setType(page.type || "concept");
    setTags((page.tags || "").split(",").map(t => t.trim().replace(/^#/, "")).filter(Boolean));
    setAliases(page.aliases || []);
  }, [page.slug]);
```

- [ ] **Step 4: `save()` 헬퍼가 aliases도 저장하도록 확장**

`dashboard/src/components/PropertiesPanel.tsx:82-92`의:

```typescript
  // ── 저장 헬퍼 ─────────────────────────────────────────────────────────────
  const save = useCallback(async (patch: { type?: string; tags?: string[] }) => {
    const tagArray = patch.tags ?? tags;
    const pageType = patch.type ?? type;
    await updatePage(vault, page.slug, {
      content: page.content,
      title: page.title,
      type: pageType,
      tags: tagArray,
    });
    onSaved();
  }, [vault, page, type, tags, onSaved]);
```

→

```typescript
  // ── 저장 헬퍼 ─────────────────────────────────────────────────────────────
  const save = useCallback(async (patch: { type?: string; tags?: string[]; aliases?: string[] }) => {
    const tagArray = patch.tags ?? tags;
    const pageType = patch.type ?? type;
    const aliasArray = patch.aliases ?? aliases;
    await updatePage(vault, page.slug, {
      content: page.content,
      title: page.title,
      type: pageType,
      tags: tagArray,
      extra_meta: { aliases: aliasArray },
    });
    onSaved();
  }, [vault, page, type, tags, aliases, onSaved]);
```

- [ ] **Step 5: alias 추가/삭제 핸들러 추가**

`handleRemoveTag` 함수(`dashboard/src/components/PropertiesPanel.tsx:113-118`) 바로 뒤에 추가:

```typescript
  // ── alias 추가 ────────────────────────────────────────────────────────────
  async function handleAddAlias() {
    const a = aliasInput.trim();
    if (!a || aliases.includes(a)) { setAliasInput(""); return; }
    const next = [...aliases, a];
    setAliases(next);
    setAliasInput("");
    setAliasSaving(true);
    try { await save({ aliases: next }); } catch {} finally { setAliasSaving(false); }
  }

  // ── alias 삭제 ────────────────────────────────────────────────────────────
  async function handleRemoveAlias(alias: string) {
    const next = aliases.filter(a => a !== alias);
    setAliases(next);
    setAliasSaving(true);
    try { await save({ aliases: next }); } catch {} finally { setAliasSaving(false); }
  }
```

- [ ] **Step 6: aliases Row UI 추가**

`dashboard/src/components/PropertiesPanel.tsx:242`(tags `Row` 닫는 `</Row>`) 바로 뒤, "Updated" Row(`244-251`) 앞에 추가:

```typescript
          {/* Aliases */}
          <Row label="aliases" saving={aliasSaving}>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 4, alignItems: "center" }}>
              {aliases.map(a => (
                <Pill key={a} text={a} removeLabel={`별칭 ${a} 제거`} onRemove={() => handleRemoveAlias(a)} />
              ))}
              <div style={{ display: "flex", gap: 4 }}>
                <input
                  type="text"
                  value={aliasInput}
                  onChange={e => setAliasInput(e.target.value)}
                  onKeyDown={e => { if (e.key === "Enter") { e.preventDefault(); handleAddAlias(); } }}
                  placeholder="별칭 추가..."
                  style={{
                    fontSize: 12, padding: "3px 8px", borderRadius: 6,
                    border: "1px solid var(--color-hairline)",
                    background: "var(--bg-surface)", color: "var(--color-ink)",
                    width: 90, outline: "none",
                  }}
                />
                <button
                  type="button"
                  onClick={handleAddAlias}
                  style={{
                    fontSize: 12, padding: "3px 8px", borderRadius: 6,
                    background: "var(--color-primary)", color: "#fff",
                    border: "none", cursor: "pointer", fontWeight: 600,
                  }}
                >+</button>
              </div>
            </div>
          </Row>

```

- [ ] **Step 7: 타입체크**

Run: `cd dashboard && npx tsc -b --noEmit`
Expected: 에러 없음.

- [ ] **Step 8: 수동 동작 확인**

문서 페이지를 열어 Properties 패널의 "aliases" 행에서 별칭을 추가/삭제 → 저장 성공 토스트/상태 확인 → 페이지 새로고침 후에도 별칭이 유지되는지 (`GET /pages/{slug}`가 `aliases`를 반환함, `raven/api/server.py:924/1190`) 확인. 추가한 별칭으로 사이드바 검색 시 문서가 나오는지도 확인 (Task 1의 FTS 변경과의 통합 확인 — DB 재빌드가 필요할 수 있으니 필요 시 vault의 build 버튼/`raven build` 실행).

- [ ] **Step 9: 커밋**

```bash
git add dashboard/src/components/PropertiesPanel.tsx
git commit -m "dashboard: PropertiesPanel에 alias 칩 편집 UI 추가"
```

---

### Task 6: 그래프 노드 라벨 말줄임 + 호버 전체 제목 표시

**Files:**
- Modify: `dashboard/src/components/GraphCanvas.tsx`
- Test: `dashboard/src/components/graphLabel.test.ts`

**Interfaces:**
- Consumes: `shouldShowLabel`, `NODE_LABEL_BASE_SIZE`, `GRAPH_LABEL_FONT` (기존, `GraphCanvas.tsx:327-372`), `hoveredNodeRef`/`isFocused` (기존 hover 인프라, `GraphCanvas.tsx:409-418,1186-1191`).
- Produces: `truncateLabel(ctx, label, maxWidth): string` — 순수 함수로 export해 vitest에서 mock `CanvasRenderingContext2D`로 단위 테스트 가능.

- [ ] **Step 1: 실패하는 순수 함수 테스트 작성**

Create `dashboard/src/components/graphLabel.test.ts`:

```typescript
import { describe, it, expect } from "vitest";
import { truncateLabel } from "./GraphCanvas";

// 고정폭 mock: 문자 1개 = 6px (측정 로직만 검증하면 되므로 폰트 렌더는 불필요).
function makeMockCtx(charWidth = 6): CanvasRenderingContext2D {
  return {
    measureText: (text: string) => ({ width: text.length * charWidth }),
  } as unknown as CanvasRenderingContext2D;
}

describe("truncateLabel", () => {
  it("returns the label unchanged when it fits within maxWidth", () => {
    const ctx = makeMockCtx();
    expect(truncateLabel(ctx, "짧은제목", 100)).toBe("짧은제목");
  });

  it("truncates with an ellipsis when the label exceeds maxWidth", () => {
    const ctx = makeMockCtx();
    // "매우매우매우긴제목입니다" = 12 chars * 6px = 72px > maxWidth(30px, 5칸)
    const result = truncateLabel(ctx, "매우매우매우긴제목입니다", 30);
    expect(result.endsWith("…")).toBe(true);
    expect(result.length).toBeLessThan("매우매우매우긴제목입니다".length);
  });

  it("never exceeds maxWidth after truncation", () => {
    const ctx = makeMockCtx();
    const result = truncateLabel(ctx, "abcdefghijklmnopqrstuvwxyz", 50);
    expect(ctx.measureText(result).width).toBeLessThanOrEqual(50);
  });
});
```

- [ ] **Step 2: 테스트 실행 → 실패 확인**

Run: `cd dashboard && npx vitest run src/components/graphLabel.test.ts`
Expected: FAIL — `truncateLabel` is not exported from `./GraphCanvas`.

- [ ] **Step 3: `truncateLabel` 순수 함수 구현 + export**

`dashboard/src/components/GraphCanvas.tsx:372`(`const NODE_LABEL_BASE_SIZE = 11.4;`) 바로 뒤에 추가:

```typescript
const NODE_LABEL_MAX_WIDTH_PX = 90; // 화면 픽셀 기준 — fontSize와 동일하게 scale로 나눠 apparent 크기 고정.

// 캔버스 라벨이 너무 길면 자르고 말줄임표(…)를 붙인다. ctx.font가 이미 설정된
// 상태에서 호출해야 measureText가 올바른 폭을 반환한다.
export function truncateLabel(ctx: CanvasRenderingContext2D, label: string, maxWidth: number): string {
  if (ctx.measureText(label).width <= maxWidth) return label;
  const ellipsis = "…";
  let lo = 0;
  let hi = label.length;
  while (lo < hi) {
    const mid = Math.ceil((lo + hi) / 2);
    const candidate = label.slice(0, mid) + ellipsis;
    if (ctx.measureText(candidate).width <= maxWidth) {
      lo = mid;
    } else {
      hi = mid - 1;
    }
  }
  return label.slice(0, lo) + ellipsis;
}
```

- [ ] **Step 4: 테스트 재실행 → 통과 확인**

Run: `cd dashboard && npx vitest run src/components/graphLabel.test.ts`
Expected: 3개 테스트 모두 PASS.

- [ ] **Step 5: 라벨 렌더 루프에 말줄임 + 호버 전체 제목 배경 박스 적용**

`dashboard/src/components/GraphCanvas.tsx:1261-1282`의:

```typescript
      if (showLabel) {
        const label = node.title || node.slug || node.id;
        const fontSize = NODE_LABEL_BASE_SIZE / scale;
        ctx.save();
        ctx.font = `${isFocused ? "500" : "400"} ${fontSize}px ${GRAPH_LABEL_FONT}`;
        ctx.textAlign = "center";
        ctx.textBaseline = "top";

        // v0.7.146 (B): zoom-out에서 라벨이 노드 안에 박혀서 깨짐 → 노드 옆으로 오프셋.
        // zoom-in (scale > 1.5) 이하면 라벨을 노드 오른쪽으로 띄움.
        const labelOffsetX = scale < 1.5 ? (renderedSize + 8) / scale : 0;
        const labelX = node.x + labelOffsetX;
        const labelY = node.y + renderedSize + 3.8 / scale;

        // No text outline: small canvas labels became fat/blurry with halo strokes.
        // Rely on theme-resolved high-contrast label color instead.
        ctx.fillStyle = isFocused
          ? resolvedEdgeHighlightRef.current
          : resolvedLabelColorRef.current;
        ctx.fillText(label, labelX, labelY);
        ctx.restore();
      }
```

→

```typescript
      if (showLabel) {
        const label = node.title || node.slug || node.id;
        const fontSize = NODE_LABEL_BASE_SIZE / scale;
        ctx.save();
        ctx.font = `${isFocused ? "500" : "400"} ${fontSize}px ${GRAPH_LABEL_FONT}`;
        ctx.textAlign = "center";
        ctx.textBaseline = "top";

        // v0.7.146 (B): zoom-out에서 라벨이 노드 안에 박혀서 깨짐 → 노드 옆으로 오프셋.
        // zoom-in (scale > 1.5) 이하면 라벨을 노드 오른쪽으로 띄움.
        const labelOffsetX = scale < 1.5 ? (renderedSize + 8) / scale : 0;
        const labelX = node.x + labelOffsetX;
        const labelY = node.y + renderedSize + 3.8 / scale;

        // v0.7.201+: 긴 제목이 안 잘려서 다른 노드/UI와 겹치던 문제 — 잘라서
        // 표시하고, 호버/포커스 중인 노드만 배경 박스와 함께 전체 제목을 보여준다.
        const maxLabelWidth = NODE_LABEL_MAX_WIDTH_PX / scale;
        const displayLabel = isFocused ? label : truncateLabel(ctx, label, maxLabelWidth);

        if (isFocused) {
          const textWidth = ctx.measureText(displayLabel).width;
          const padX = 4 / scale;
          const padY = 2 / scale;
          ctx.fillStyle = "rgba(15, 15, 20, 0.82)";
          ctx.fillRect(
            labelX - textWidth / 2 - padX,
            labelY - padY,
            textWidth + padX * 2,
            fontSize + padY * 2
          );
        }

        // No text outline: small canvas labels became fat/blurry with halo strokes.
        // Rely on theme-resolved high-contrast label color instead.
        ctx.fillStyle = isFocused
          ? resolvedEdgeHighlightRef.current
          : resolvedLabelColorRef.current;
        ctx.fillText(displayLabel, labelX, labelY);
        ctx.restore();
      }
```

- [ ] **Step 6: 타입체크**

Run: `cd dashboard && npx tsc -b --noEmit`
Expected: 에러 없음.

- [ ] **Step 7: 수동 동작 확인**

Run: `cd dashboard && npm run dev`
브라우저에서 그래프 뷰를 열어: (a) 제목이 긴 노드가 이제 `...`로 잘려서 다른 노드와 안 겹치는지, (b) 그 노드에 마우스를 올렸을 때 배경 박스와 함께 전체 제목이 보이는지, (c) 짧은 제목 노드는 기존과 동일하게 보이는지(회귀 없음) 확인.

- [ ] **Step 8: 커밋**

```bash
git add dashboard/src/components/GraphCanvas.tsx dashboard/src/components/graphLabel.test.ts
git commit -m "dashboard: 그래프 노드 라벨 말줄임 처리 + 호버 시 전체 제목 표시"
```

---

## 최종 확인

- [ ] 전체 백엔드 테스트: `cd /Users/jaekanglee/Dev/Project/Raven && python3 -m pytest tests/ -q`
- [ ] 전체 프론트엔드 테스트: `cd dashboard && npx vitest run`
- [ ] 전체 타입체크: `cd dashboard && npx tsc -b --noEmit`
- [ ] 스펙 문서(`docs/superpowers/specs/2026-07-10-search-unification-alias-graph-labels-design.md`)의 "테스트 관점" 4개 항목을 브라우저에서 수동으로 재확인.
