import { useState, useEffect } from "react";
import { useOutletContext } from "react-router-dom";
import { EmptyState } from "../components/ui/EmptyState";
import { PageHeader } from "../components/ui/PageHeader";
import { SearchResultItem } from "../components/SearchResultItem";

export function SearchPage() {
  const { vault } = useOutletContext<{ vault: string }>();
  const [q, setQ] = useState("");
  const [results, setResults] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);

  // Debounced fetch with AbortController (SearchBar와 동일 패턴).
  // 입력 중 과도한 요청/깜빡임을 줄이기 위해 220ms 대기 후 조회한다.
  useEffect(() => {
    if (!q.trim()) {
      setResults([]);
      setLoading(false);
      setHasSearched(false);
      return;
    }
    const ctrl = new AbortController();
    const timer = window.setTimeout(() => {
      setLoading(true);
      setHasSearched(true);
      fetch(`/api/vaults/${encodeURIComponent(vault)}/search?q=${encodeURIComponent(q)}&top_k=20`, {
        signal: ctrl.signal,
      })
        .then((r) => (r.ok ? r.json() : { results: [] }))
        .then((d) => setResults(d.results || []))
        .catch(() => setResults([]))
        .finally(() => setLoading(false));
    }, 220);
    return () => {
      ctrl.abort();
      window.clearTimeout(timer);
    };
  }, [q, vault]);

  return (
    <div style={{ maxWidth: 880 }}>
      <PageHeader
        title="검색"
        contextLabel={`${vault} 보관소`}
        subtitle="모든 페이지를 전문 검색합니다."
        bottomSpacing={24}
      />

      <div style={{ marginBottom: 32 }}>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            height: 64,
            background: "var(--color-canvas)",
            border: "1px solid var(--color-hairline-strong)",
            borderRadius: "var(--radius-full)",
            padding: "0 24px",
            boxShadow: "0 1px 2px rgba(0,0,0,0.04)",
          }}
        >
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="검색어를 입력하세요"
            autoFocus
            style={{
              flex: 1,
              border: "none",
              outline: "none",
              background: "transparent",
              fontSize: 16,
              color: "var(--color-ink)",
              fontFamily: "inherit",
            }}
          />
        </div>
      </div>

      {!q && (
        <EmptyState
          icon="🔎"
          title="검색어를 입력하세요"
          description="제목, 본문, 스니펫 기준으로 현재 보관소 전체를 바로 탐색합니다."
        />
      )}

      {q && (
        <>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              fontSize: 13,
              color: "var(--color-muted)",
              marginBottom: 16,
            }}
          >
            <span>
              {loading
                ? "검색 중…"
                : `${results.length}개 결과`}
            </span>
            {hasSearched && !loading && (
              <span>{`"${q}"`}</span>
            )}
          </div>

          {!loading && results.length === 0 ? (
            <EmptyState
              icon="🗂"
              title="검색 결과 없음"
              description="다른 키워드나 더 짧은 검색어로 다시 시도해 보세요."
            />
          ) : (
            <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
              {results.map((r) => (
                <SearchResultItem
                  key={r.slug}
                  vault={vault}
                  result={r}
                />
              ))}
            </ul>
          )}
        </>
      )}
    </div>
  );
}
