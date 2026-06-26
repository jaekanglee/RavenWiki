// DEPRECATED 2026-06-26 — SearchPage가 API로 이전. minisearch fallback용으로 보존.
// 새 코드에서는 직접 /api/vaults/{vault}/search 를 호출할 것 (SearchBar.tsx 패턴).
// @deprecated API search로 마이그레이션. 이 파일은 향후 삭제 예정.
import MiniSearch from "minisearch";

let _index: MiniSearch | null = null;

export async function initSearch(): Promise<MiniSearch> {
  if (_index) return _index;
  const r = await fetch("/api/search.idx.json");
  if (!r.ok) throw new Error(`search index fetch failed: ${r.status}`);
  _index = MiniSearch.loadJSON(await r.text(), {
    fields: ["title", "tags", "content"],
    storeFields: ["slug", "title", "path", "tags", "type"],
    searchOptions: { boost: { title: 3, tags: 2 }, fuzzy: 0.2 },
  });
  return _index;
}

export function search(q: string) {
  if (!_index) throw new Error("Search not initialized");
  return _index.search(q, { boost: { title: 3 }, fuzzy: 0.2 });
}
