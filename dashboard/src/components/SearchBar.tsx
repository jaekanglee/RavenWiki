import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

/**
 * SearchBar — pill-shaped (search-bar-pill token).
 * 9999px radius, 64px height, hairline + shadow border.
 * Single Rausch "search orb" button on the right.
 */
export function SearchBar({
  vault,
  onSelect,
}: {
  vault: string;
  onSelect?: (slug: string) => void;
}) {
  const [q, setQ] = useState("");
  const [results, setResults] = useState<any[]>([]);
  const [focused, setFocused] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    if (!q.trim()) {
      setResults([]);
      return;
    }
    const ctrl = new AbortController();
    fetch(`/api/vaults/${vault}/search?q=${encodeURIComponent(q)}&top_k=8`, {
      signal: ctrl.signal,
    })
      .then((r) => (r.ok ? r.json() : { results: [] }))
      .then((d) => setResults(d.results || []))
      .catch(() => setResults([]));
    return () => ctrl.abort();
  }, [q, vault]);

  return (
    <div className="relative w-full">
      <div
        className="search-bar-pill"
        style={{
          display: "flex",
          alignItems: "center",
          height: 64,
          background: "var(--color-canvas)",
          border: focused
            ? "2px solid var(--color-ink)"
            : "1px solid var(--color-hairline-strong)",
          borderRadius: "var(--radius-full)",
          boxShadow: focused
            ? "var(--shadow-card)"
            : "0 1px 2px rgba(0,0,0,0.04)",
          padding: "0 6px 0 24px",
          transition: "border-color 0.12s ease, box-shadow 0.12s ease",
        }}
      >
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          placeholder={`${vault}에서 검색…`}
          style={{
            flex: 1,
            minWidth: 0,
            border: "none",
            outline: "none",
            background: "transparent",
            fontSize: 15,
            color: "var(--color-ink)",
            fontFamily: "inherit",
          }}
        />
        <button
          aria-label="검색"
          style={{
            width: 48,
            height: 48,
            borderRadius: "var(--radius-full)",
            background: "var(--color-primary)",
            color: "var(--color-on-primary)",
            border: "none",
            cursor: "pointer",
            display: "inline-flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: 18,
            flexShrink: 0,
          }}
        >
          🔎
        </button>
      </div>

      {results.length > 0 && (
        <ul
          style={{
            position: "absolute",
            width: "100%",
            marginTop: 8,
            background: "var(--color-canvas)",
            border: "1px solid var(--color-hairline)",
            borderRadius: "var(--radius-md)",
            boxShadow: "var(--shadow-card)",
            zIndex: 10,
            maxHeight: 384,
            overflowY: "auto",
            padding: 8,
            listStyle: "none",
          }}
        >
          {results.map((r) => (
            <li
              key={r.slug}
              onMouseDown={(e) => {
                e.preventDefault();
                if (onSelect) onSelect(r.slug);
                else navigate(`/page/${r.slug}`);
                setQ("");
              }}
              style={{
                padding: "10px 12px",
                cursor: "pointer",
                fontSize: 14,
                borderRadius: 8,
              }}
              onMouseEnter={(e) => {
                (e.currentTarget as HTMLElement).style.background =
                  "var(--color-surface-soft)";
              }}
              onMouseLeave={(e) => {
                (e.currentTarget as HTMLElement).style.background = "transparent";
              }}
            >
              <div style={{ fontWeight: 500, color: "var(--color-ink)" }}>{r.title}</div>
              <div style={{ fontSize: 12, color: "var(--color-muted)", marginTop: 2 }}>
                {r.type} · score {r.score}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}