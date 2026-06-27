import { useEffect, useState } from "react";
import { useParams, useOutletContext } from "react-router-dom";
import { MarkdownView } from "../components/MarkdownView";
import { BacklinksPanel } from "../components/BacklinksPanel";
import { EditButton } from "../components/EditButton";
import { DeleteButton } from "../components/DeleteButton";
import { fetchPage, getActiveVault } from "../lib/api";
import type { Page } from "../types";

interface Ctx {
  vault: string;
  refresh: () => void;
}

export function PageView() {
  const params = useParams();
  const slug = params["*"];
  // v0.6.9 (P15 fix): URL의 :vault 파라미터를 SOT로 사용. Layout의 ctx.vault가
  // Wizard 후 stale여도 URL 우선이면 stale race 차단.
  const vaultFromUrl = params.vault;
  const ctx = useOutletContext<Ctx>();
  const vault = vaultFromUrl || ctx?.vault || getActiveVault() || "default";
  const [page, setPage] = useState<Page | null | undefined>(undefined);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    if (!slug) return;
    setPage(undefined);
    setErr(null);
    fetchPage(vault, slug)
      .then((d) => {
        const fm = d.frontmatter || {};
        const tags = (fm.tags || "").replace(/[\[\]]/g, "").trim();
        setPage({
          slug: d.slug,
          title: fm.title || d.slug,
          type: fm.type || "?",
          path: d.slug,
          created: fm.created || "",
          updated: fm.updated || "",
          tags,
          content: d.content,
          backlinks: [],
        });
      })
      .catch((e) => {
        setErr(String(e.message || e));
        setPage(null);
      });
  }, [slug, vault]);

  if (page === undefined) {
    return <div className="text-muted">Loading…</div>;
  }
  if (page === null) {
    return (
      <div>
        <div style={{ color: "var(--color-error-text)", marginBottom: 12 }}>
          Not found: {slug}
        </div>
        <div style={{ fontSize: 13, color: "var(--color-muted)" }}>{err}</div>
      </div>
    );
  }

  return (
    <div
      className="page-grid"
      style={{
        display: "grid",
        gridTemplateColumns: "minmax(0, 1fr) 240px",
        gap: 32,
      }}
    >
      <article style={{ minWidth: 0 }}>
        {/* Header — title + actions */}
        <div
          style={{
            display: "flex",
            alignItems: "flex-start",
            justifyContent: "space-between",
            marginBottom: 16,
            gap: 16,
          }}
        >
          <h1>{page.title}</h1>
          <div style={{ display: "flex", gap: 8, flexShrink: 0 }}>
            <EditButton
              vault={vault}
              slug={page.slug}
              content={page.content}
              onSaved={ctx?.refresh}
            />
            <DeleteButton
              vault={vault}
              slug={page.slug}
              onDeleted={() => location.assign("/")}
            />
          </div>
        </div>

        {/* Meta row — type badge + tags as ink pills */}
        <div
          style={{
            display: "flex",
            gap: 8,
            marginBottom: 32,
            flexWrap: "wrap",
            alignItems: "center",
          }}
        >
          <span className="chip-strong">{page.type}</span>
          {page.updated && (
            <span style={{ fontSize: 13, color: "var(--color-muted)" }}>
              updated {String(page.updated).slice(0, 10)}
            </span>
          )}
          {(page.tags || "")
            .split(",")
            .map((t) => t.trim())
            .filter(Boolean)
            .map((t) => (
              <span key={t} className="chip">
                #{t}
              </span>
            ))}
        </div>

        {/* Body */}
        <MarkdownView content={page.content} />
      </article>

      <BacklinksPanel backlinks={page.backlinks ?? []} />
    </div>
  );
}