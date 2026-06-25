import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { MarkdownView } from "../components/MarkdownView";
import { BacklinksPanel } from "../components/BacklinksPanel";
import { EditButton } from "../components/EditButton";
import { DeleteButton } from "../components/DeleteButton";
import type { Page } from "../types";

export function PageView() {
  const { slug } = useParams();
  const [page, setPage] = useState<Page | null | undefined>(undefined);

  useEffect(() => {
    if (!slug) return;
    setPage(undefined);
    const safe = slug.replace(/[^a-zA-Z0-9_\-/.@]/g, "_");
    // 1) 정적 API 시도
    fetch(`/api/page-${safe}.json`)
      .then((r) => (r.ok ? r.json() : null))
      .then((p) => {
        // 2) 없으면 localStorage fallback (정적 데모용)
        if (!p && typeof window !== "undefined") {
          const local = localStorage.getItem(`wiki:local:${slug}`);
          if (local) {
            // 로컬 저장본은 frontmatter+body, 단순히 body만 노출
            const body = local.includes("---")
              ? local.split("---").slice(2).join("---").trim()
              : local;
            return {
              slug,
              title: slug.split("/").pop() || slug,
              type: "concept",
              path: slug,
              created: new Date().toISOString().slice(0, 10),
              updated: new Date().toISOString().slice(0, 10),
              tags: "",
              content: body,
              backlinks: [],
            };
          }
        }
        return p;
      })
      .then(setPage)
      .catch(() => setPage(null));
  }, [slug]);

  if (page === undefined) return <div>Loading…</div>;
  if (page === null) return <div>Not found: {slug}</div>;

  return (
    <div className="grid grid-cols-1 lg:grid-cols-[1fr_300px] gap-6">
      <article>
        <div className="flex items-start justify-between mb-2 gap-3">
          <h1 className="text-3xl font-bold">{page.title}</h1>
          <div className="flex gap-2 shrink-0">
            <EditButton page={{ slug: page.slug, content: page.content }} />
            <DeleteButton slug={page.slug} />
          </div>
        </div>
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
