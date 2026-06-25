import { Link } from "react-router-dom";
import { useEffect, useState } from "react";
import type { Page } from "../types";

export function HomePage() {
  const [index, setIndex] = useState<Page[]>([]);

  useEffect(() => {
    fetch("/api/index.json")
      .then((r) => (r.ok ? r.json() : []))
      .then(setIndex)
      .catch(() => setIndex([]));
  }, []);

  const recent = [...index]
    .sort((a, b) => String(b.updated).localeCompare(String(a.updated)))
    .slice(0, 12);

  // Stats — small upper band, ink-only
  const types = Array.from(new Set(index.map((p) => p.type))).filter(Boolean);

  return (
    <div style={{ maxWidth: 1120 }}>
      {/* Hero band — modest, h1 ≤ 28px */}
      <section style={{ paddingTop: 16, paddingBottom: 48 }}>
        <h1 style={{ marginBottom: 12 }}>Wiki Home</h1>
        <p className="text-body" style={{ fontSize: 16, maxWidth: 640 }}>
          전체 {index.length}개 페이지 · {types.length}개 타입. 최근 수정된 페이지를
          모았습니다.
        </p>
      </section>

      {/* Recent section — 64px top padding */}
      <section style={{ paddingBottom: 64 }}>
        <div
          style={{
            display: "flex",
            alignItems: "baseline",
            justifyContent: "space-between",
            marginBottom: 24,
          }}
        >
          <h2>최근 수정</h2>
          <Link to="/search" className="link-muted">
            전체 검색 →
          </Link>
        </div>

        {recent.length === 0 ? (
          <p className="text-muted">아직 페이지가 없음</p>
        ) : (
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))",
              gap: 16,
            }}
          >
            {recent.map((p) => (
              <Link
                key={p.slug}
                to={`/page/${p.slug}`}
                className="card-flat"
                style={{
                  display: "block",
                  textDecoration: "none",
                  transition: "box-shadow 0.12s ease, transform 0.12s ease",
                }}
                onMouseEnter={(e) => {
                  (e.currentTarget as HTMLElement).style.boxShadow =
                    "var(--shadow-card)";
                  (e.currentTarget as HTMLElement).style.transform = "translateY(-1px)";
                }}
                onMouseLeave={(e) => {
                  (e.currentTarget as HTMLElement).style.boxShadow = "none";
                  (e.currentTarget as HTMLElement).style.transform = "none";
                }}
              >
                <div style={{ display: "flex", gap: 8, marginBottom: 12, flexWrap: "wrap" }}>
                  <span className="chip">{p.type}</span>
                  {p.updated && (
                    <span style={{ fontSize: 12, color: "var(--color-muted)" }}>
                      {String(p.updated).slice(0, 10)}
                    </span>
                  )}
                </div>
                <div
                  style={{
                    fontSize: 16,
                    fontWeight: 600,
                    color: "var(--color-ink)",
                    marginBottom: 8,
                    lineHeight: 1.3,
                  }}
                >
                  {p.title}
                </div>
                <div
                  style={{
                    fontSize: 13,
                    color: "var(--color-muted)",
                    fontFamily: "ui-monospace, SFMono-Regular, monospace",
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                  }}
                >
                  {p.path}
                </div>
              </Link>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}