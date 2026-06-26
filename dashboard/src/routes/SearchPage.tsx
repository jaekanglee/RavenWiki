import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { initSearch, search } from "../lib/search";

export function SearchPage() {
  const [q, setQ] = useState("");
  const [results, setResults] = useState<any[]>([]);

  useEffect(() => {
    initSearch().catch(console.error);
  }, []);

  useEffect(() => {
    if (!q) return setResults([]);
    try {
      setResults(search(q));
    } catch {
      setResults([]);
    }
  }, [q]);

  return (
    <div style={{ maxWidth: 880 }}>
      <h1 style={{ marginBottom: 8 }}>Search</h1>
      <p className="text-muted" style={{ fontSize: 14, marginBottom: 24 }}>
        모든 페이지를 전문 검색합니다.
      </p>

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

      {q && (
        <>
          <div
            style={{
              fontSize: 13,
              color: "var(--color-muted)",
              marginBottom: 16,
            }}
          >
            {results.length} result{results.length === 1 ? "" : "s"}
          </div>

          {results.length === 0 ? (
            <p className="text-muted">결과 없음</p>
          ) : (
            <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
              {results.map((r) => (
                <li
                  key={r.slug}
                  style={{
                    borderBottom: "1px solid var(--color-hairline)",
                    paddingBottom: 16,
                    marginBottom: 16,
                  }}
                >
                  <Link to={`/page/${r.slug}`} className="link-ink">
                    <div style={{ fontSize: 16, fontWeight: 600, marginBottom: 4 }}>
                      {r.title}
                    </div>
                  </Link>
                  {r.snippet && (
                    <div
                      style={{
                        fontSize: 13,
                        color: "var(--color-muted)",
                        marginBottom: 4,
                        lineHeight: 1.4,
                      }}
                      dangerouslySetInnerHTML={{ __html: r.snippet }}
                    />
                  )}
                  <div
                    style={{
                      fontSize: 12,
                      color: "var(--color-muted)",
                      fontFamily: "ui-monospace, SFMono-Regular, monospace",
                    }}
                  >
                    {r.path}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </div>
  );
}