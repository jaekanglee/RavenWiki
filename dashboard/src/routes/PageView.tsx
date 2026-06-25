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
  const { slug } = useParams();
  const ctx = useOutletContext<Ctx>();
  const vault = ctx?.vault || getActiveVault() || "default";
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

  if (page === undefined) return <div>Loading…</div>;
  if (page === null)
    return (
      <div>
        <div className="text-red-600 mb-3">Not found: {slug}</div>
        <div className="text-sm text-gray-500">{err}</div>
      </div>
    );

  return (
    <div className="grid grid-cols-1 lg:grid-cols-[1fr_300px] gap-6">
      <article>
        <div className="flex items-start justify-between mb-2 gap-3">
          <h1 className="text-3xl font-bold">{page.title}</h1>
          <div className="flex gap-2 shrink-0">
            <EditButton vault={vault} slug={page.slug} content={page.content} onSaved={ctx?.refresh} />
            <DeleteButton vault={vault} slug={page.slug} onDeleted={() => location.assign("/")} />
          </div>
        </div>
        <div className="flex gap-2 mb-4 text-sm flex-wrap">
          <span className="px-2 py-0.5 bg-cyan-100 dark:bg-cyan-900 rounded">{page.type}</span>
          {(page.tags || "")
            .split(",")
            .map((t) => t.trim())
            .filter(Boolean)
            .map((t) => (
              <span key={t} className="px-2 py-0.5 bg-gray-100 dark:bg-gray-800 rounded">
                #{t}
              </span>
            ))}
        </div>
        <MarkdownView content={page.content} />
      </article>
      <BacklinksPanel backlinks={page.backlinks ?? []} />
    </div>
  );
}
