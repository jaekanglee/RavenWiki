import { useEffect, useMemo, useState } from "react";
import { useParams, useOutletContext } from "react-router-dom";
import { MarkdownView } from "../components/MarkdownView";
import { FloatingGraphPanel } from "../components/FloatingGraphPanel";
import { FullscreenGraphModal } from "../components/FullscreenGraphModal";
import { BacklinksPanel } from "../components/BacklinksPanel";
import { EditButton } from "../components/EditButton";
import { DeleteButton } from "../components/DeleteButton";
import { PageMetaRow } from "../components/PageMetaRow";
import { fetchPage, getActiveVault } from "../lib/api";
import type { Graph, Page } from "../types";

interface Ctx {
  vault: string;
  refresh: () => void;
}

export function buildLocalGraph(graph: Graph, centerSlug: string): Graph {
  const center = resolveGraphId(graph, centerSlug);
  if (!center) return { nodes: [], edges: [] };

  const localIds = new Set<string>([center]);
  const localEdges = graph.edges.filter((edge) => {
    const source = (edge as any).source ?? edge.source_slug;
    const target = (edge as any).target ?? edge.target_slug;
    const connected = source === center || target === center;
    if (connected) {
      localIds.add(source);
      localIds.add(target);
    }
    return connected;
  });

  return {
    nodes: graph.nodes.filter((node) => localIds.has(node.id ?? node.slug)),
    edges: localEdges,
  };
}


export function splitRelatedSection(content: string): { body: string; links: string[] } {
  const extractLinks = (text: string): string[] => {
    const links: string[] = [];
    const seen = new Set<string>();
    const re = /\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|[^\]]+)?\]\]/g;
    for (const match of text.matchAll(re)) {
      let slug = match[1].trim();
      if (slug.endsWith(".md")) slug = slug.slice(0, -3);
      if (!slug || seen.has(slug)) continue;
      seen.add(slug);
      links.push(slug);
    }
    return links;
  };

  const lines = content.split(/\r?\n/);
  const idx = lines.findIndex((line) => line.trim().replace(/^#+\s*/, "") === "관련");
  if (idx >= 0) {
    const body = lines.slice(0, idx).join("\n").trimEnd();
    return { body, links: extractLinks(lines.slice(idx + 1).join("\n")) };
  }

  // Some Raven pages end with a wikilink-only paragraph instead of an explicit
  // "관련" heading. Treat that trailing paragraph as structured related data.
  const paragraphs = content.trimEnd().split(/\n\s*\n/);
  const tail = paragraphs[paragraphs.length - 1] ?? "";
  const tailLinks = extractLinks(tail);
  const tailWithoutLinks = tail
    .replace(/\[\[[^\]]+\]\]/g, "")
    .replace(/[·,|\-–—\s]/g, "")
    .trim();
  if (tailLinks.length > 0 && tailWithoutLinks.length === 0) {
    return {
      body: paragraphs.slice(0, -1).join("\n\n").trimEnd(),
      links: tailLinks,
    };
  }

  return { body: content, links: [] };
}

// Match a graph node id by suffix of path segments. Both "users" and
// "concept/users" should resolve to id "concept/users" so URL slugs that
// carry an extra prefix (e.g. "content/concept/users") still find a node.
export function resolveGraphId(graph: Graph, slug: string): string | null {
  const ids = graph.nodes.map((n) => n.id ?? n.slug);
  if (ids.includes(slug)) return slug;
  const segments = slug.split("/");
  const matches = ids.filter((id) => {
    const idSegs = id.split("/");
    // id is a suffix of slug: idSegs == last N segments of slug
    if (idSegs.length <= segments.length) {
      return segments.slice(-idSegs.length).every((s, i) => s === idSegs[i]);
    }
    // slug is a suffix of id: slug == last N segments of id
    return idSegs.slice(-segments.length).every((s, i) => s === segments[i]);
  });
  if (matches.length === 0) return null;
  return matches.sort((a, b) => a.length - b.length)[0];
}

export function buildRelatedGraph(graph: Graph, centerSlug: string, relatedLinks: string[]): Graph {
  const center = resolveGraphId(graph, centerSlug);
  if (!center) return { nodes: [], edges: [] };

  const ids = new Set<string>([center]);
  for (const link of relatedLinks) {
    const resolved = resolveGraphId(graph, link);
    if (resolved) ids.add(resolved);
  }

  const edges = graph.edges.filter((edge) => {
    const source = (edge as any).source ?? edge.source_slug;
    const target = (edge as any).target ?? edge.target_slug;
    return ids.has(source) && ids.has(target);
  });

  return {
    nodes: graph.nodes.filter((node) => ids.has(node.id ?? node.slug)),
    edges,
  };
}

export function PageView() {
  console.log("[Raven-Debug] PageView mount");
  const params = useParams();
  const slug = params["*"];
  // v0.6.9 (P15 fix): URL의 :vault 파라미터를 SOT로 사용. Layout의 ctx.vault가
  // Wizard 후 stale여도 URL 우선이면 stale race 차단.
  const vaultFromUrl = params.vault;
  const ctx = useOutletContext<Ctx>();
  const vault = vaultFromUrl || ctx?.vault || getActiveVault() || "default";
  console.log("[Raven-Debug] PageView vault=", vault, "slug=", slug);
  const [page, setPage] = useState<Page | null | undefined>(undefined);
  const [graph, setGraph] = useState<Graph>({ nodes: [], edges: [] });
  const [err, setErr] = useState<string | null>(null);
  const [showFullGraph, setShowFullGraph] = useState(false);

  useEffect(() => {
    if (!slug) {
      console.log("[Raven-Debug] useEffect early return (no slug)");
      return;
    }
    console.log("[Raven-Debug] useEffect fetchPage start");
    setPage(undefined);
    setErr(null);
    fetchPage(vault, slug)
      .then((d) => {
        console.log("[Raven-Debug] fetchPage OK, slug=", d.slug);
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
        console.log("[Raven-Debug] setPage done");
      })
      .catch((e) => {
        console.log("[Raven-Debug] fetchPage CATCH:", e);
        setErr(String(e.message || e));
        setPage(null);
      });
  }, [slug, vault]);

  useEffect(() => {
    if (!vault) return;
    fetch(`/api/vaults/${encodeURIComponent(vault)}/graph`)
      .then((r) => (r.ok ? r.json() : { nodes: [], edges: [] }))
      .then((d) => setGraph({ nodes: d.nodes ?? [], edges: d.edges ?? [] }))
      .catch(() => setGraph({ nodes: [], edges: [] }));
  }, [vault]);

  const related = useMemo(
    () => (page ? splitRelatedSection(page.content) : { body: "", links: [] }),
    [page]
  );

  const localGraph = useMemo(() => {
    if (!page) return { nodes: [], edges: [] };
    const relatedGraph = buildRelatedGraph(graph, page.slug, related.links);
    return relatedGraph.nodes.length > 1 ? relatedGraph : buildLocalGraph(graph, page.slug);
  }, [graph, page, related.links]);

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
    <div className="page-grid">
      <article style={{ minWidth: 0 }}>
        {/* Action row sits above the title (compact icon-only). */}
        <div className="page-header-actions" aria-label="문서 작업">
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

        {/* Title row — only the title now. The local graph is a floating overlay. */}
        <h1 className="page-header-title">{page.title}</h1>

        {/* Meta row — type chip + 📑 Index marker + tags (v0.6.21+) */}
        <PageMetaRow
          type={page.type}
          slug={page.slug || page.path}
          tags={page.tags || ""}
          updated={page.updated}
        />

        {/* Body */}
        <MarkdownView content={related.body || page.content} vault={vault} />

        {related.links.length > 0 && (
          <div className="page-related-links" aria-label="관련 문서">
            {related.links.map((link) => {
              const resolved = resolveGraphId(graph, link) ?? link;
              const node = graph.nodes.find((n) => (n.id ?? n.slug) === resolved);
              return (
                <button
                  key={link}
                  type="button"
                  className="page-related-chip"
                  onClick={() => window.location.assign(`/page/${vault}/${resolved}`)}
                >
                  {node?.title ?? link}
                </button>
              );
            })}
          </div>
        )}
      </article>

      <BacklinksPanel backlinks={page.backlinks ?? []} vault={vault} />

      {/* Floating overlay panel — bottom-right. Hidden automatically on /graph. */}
      <FloatingGraphPanel
        vault={vault}
        nodes={localGraph.nodes}
        edges={localGraph.edges}
        onOpenFullGraph={() => setShowFullGraph(true)}
      />

      {showFullGraph && localGraph.nodes.length > 0 && (
        <FullscreenGraphModal
          vault={vault}
          nodes={localGraph.nodes}
          edges={localGraph.edges}
          centerTitle={page?.title ?? slug ?? "관련 그래프"}
          onClose={() => setShowFullGraph(false)}
        />
      )}
    </div>
  );
}