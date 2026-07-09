import { Link } from "react-router-dom";
import { useState } from "react";

export function BacklinksPanel({
  backlinks,
  vault,
  vertical,
}: {
  backlinks: { source_slug: string; source_title: string }[];
  vault: string;
  vertical?: boolean;
}) {
  // Mobile-friendly: collapsible on narrow screens.
  const [open, setOpen] = useState(true);
  const count = backlinks?.length ?? 0;

  if (count === 0) {
    return (
      <aside
        className="sidebar-label"
        style={{
          fontSize: 14,
          padding: vertical ? "16px 0" : 16,
          color: "var(--color-muted)",
          borderTop: vertical ? "1px solid var(--color-hairline)" : "none",
          marginTop: vertical ? 24 : 0,
        }}
      >
        <h3
          style={{
            fontSize: 11,
            fontWeight: 700,
            letterSpacing: "0.32px",
            textTransform: "uppercase",
            marginBottom: 12,
          }}
        >
          Backlinks
        </h3>
        <p style={{ fontSize: 13 }}>아직 참조 없음</p>
      </aside>
    );
  }

  return (
    <aside
      style={{
        position: vertical ? "static" : "sticky",
        top: vertical ? undefined : 32,
        alignSelf: vertical ? "stretch" : "flex-start",
        padding: vertical ? "16px 0" : 16,
        borderLeft: vertical ? "none" : "1px solid var(--color-hairline)",
        borderTop: vertical ? "1px solid var(--color-hairline)" : "none",
        marginTop: vertical ? 24 : 0,
      }}
    >
      <button
        onClick={() => setOpen(!open)}
        className="sidebar-mobile-toggle"
        style={{
          display: "none",
          alignItems: "center",
          gap: 6,
          background: "transparent",
          border: "none",
          cursor: "pointer",
          color: "var(--color-muted)",
          fontSize: 11,
          fontWeight: 700,
          letterSpacing: "0.32px",
          textTransform: "uppercase",
          padding: "0 0 8px 0",
        }}
      >
        {open ? "▾" : "▸"} Backlinks ({count})
      </button>
      {/* Desktop heading — always visible on >= 745px */}
      <h3
        className="sidebar-label"
        style={{
          fontSize: 11,
          fontWeight: 700,
          letterSpacing: "0.32px",
          textTransform: "uppercase",
          color: "var(--color-muted)",
          marginBottom: 12,
        }}
      >
        Backlinks ({count})
      </h3>
      {open && (
        <ul className="sidebar-text" style={{ listStyle: "none", padding: 0, margin: 0 }}>
          {backlinks.map((b) => (
            <li key={b.source_slug} style={{ marginBottom: 8 }}>
              <Link
                to={`/page/${vault}/${b.source_slug}`}
                className="link-ink"
                style={{ fontSize: 14 }}
              >
                ← {b.source_title}
              </Link>
            </li>
          ))}
        </ul>
      )}
    </aside>
  );
}