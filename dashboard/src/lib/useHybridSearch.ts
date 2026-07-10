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
