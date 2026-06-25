import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { MarkdownView } from "../components/MarkdownView";
import { BacklinksPanel } from "../components/BacklinksPanel";
import type { Page } from "../types";

export function PageView() {
  const { slug } = useParams();
  const [page, setPage] = useState<Page | null | undefined>(undefined);

  useEffect(() => {
    if (!slug) return;
    setPage(undefined);
    const safe = slug.replace(/[^a-zA-Z0-9_\-/.@]/g, "_");
    fetch(`/api/page-${safe}.json`)
      .then((r) => (r.ok ? r.json() : null))
      .then(setPage)
      .catch(() => setPage(null));
  }, [slug]);

  if (page === undefined) return <div>Loading…</div>;
  if (page === null) return <div>Not found: {slug}</div>;

  return (
    <div className="grid grid-cols-1 lg:grid-cols-[1fr_300px] gap-6">
      <article>
        <h1 className="text-3xl font-bold mb-2">{page.title}</h1>
        <div className="flex gap-2 mb-4 text-sm flex-wrap">
          <span className="px-2 py-0.5 bg-cyan-100 dark:bg-cyan-900 rounded">
            {page.type}
          </span>
          {(page.tags || "")
            .split(",")
            .map((t) => t.trim())
            .filter(Boolean)
            .map((t) => (
              <span
                key={t}
                className="px-2 py-0.5 bg-gray-100 dark:bg-gray-800 rounded"
              >
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
