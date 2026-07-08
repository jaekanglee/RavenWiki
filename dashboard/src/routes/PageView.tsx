import { useEffect, useMemo, useState } from "react";
import { useParams, useOutletContext, useNavigate } from "react-router-dom";
import { MarkdownView } from "../components/MarkdownView";
import { FloatingGraphPanel } from "../components/FloatingGraphPanel";
import { FullscreenGraphModal } from "../components/FullscreenGraphModal";
import { BacklinksPanel } from "../components/BacklinksPanel";
import { InlineMarkdownEditor } from "../components/InlineMarkdownEditor";
import { PageMetaRow } from "../components/PageMetaRow";
import { EmptyState } from "../components/ui/EmptyState";
import { Button } from "../components/ui/Button";
import { EmptyIcon } from "../lib/emptyIcons";
import { deletePage, fetchPage, getActiveVault } from "../lib/api";
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
    const source = edge.source;
    const target = edge.target;
    const connected = source === center || target === center;
    if (connected) {
      localIds.add(source);
      localIds.add(target);
    }
    return connected;
  });

  return {
    nodes: graph.nodes.filter((node) => localIds.has(node.id)),
    edges: localEdges,
  };
}


// Raven page bodies conventionally start with "# {title}" (see `raven page new`)
// so the raw .md file stays self-contained for CLI/git readers. The dashboard
// already renders `page.title` as its own <h1>, so strip that duplicate leading
// heading here before the body reaches MarkdownView — otherwise the title shows
// twice on every page.
export function stripLeadingTitleHeading(content: string, title: string): string {
  const lines = content.split(/\r?\n/);
  let i = 0;
  while (i < lines.length && lines[i].trim() === "") i++;
  const heading = lines[i]?.trim().replace(/^#\s+/, "");
  if (i >= lines.length || heading !== title.trim()) return content;
  return lines.slice(i + 1).join("\n").replace(/^\n+/, "");
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
  const ids = graph.nodes.map((n) => n.id);
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
    const source = edge.source;
    const target = edge.target;
    return ids.has(source) && ids.has(target);
  });

  return {
    nodes: graph.nodes.filter((node) => ids.has(node.id)),
    edges,
  };
}

export function PageView() {
  console.log("[Raven-Debug] PageView mount");
  const navigate = useNavigate();
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
  // Bumped after a save so the fetchPage effect below re-runs even though
  // slug/vault haven't changed — otherwise the article stays stale until
  // the user navigates away and back.
  const [reloadKey, setReloadKey] = useState(0);
  const [copied, setCopied] = useState(false);
  const handleCopy = () => {
    if (page?.filePath) {
      navigator.clipboard.writeText(page.filePath);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

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
          filePath: d.file_path,
          created: fm.created || "",
          updated: fm.updated || "",
          tags,
          content: d.content,
          backlinks: d.backlinks || [],
        });
        console.log("[Raven-Debug] setPage done");
      })
      .catch((e) => {
        console.log("[Raven-Debug] fetchPage CATCH:", e);
        setErr(String(e.message || e));
        setPage(null);
      });
  }, [slug, vault, reloadKey]);

  useEffect(() => {
    if (!vault) return;
    fetch(`/api/vaults/${encodeURIComponent(vault)}/graph`)
      .then((r) => (r.ok ? r.json() : { nodes: [], edges: [] }))
      .then((d) => setGraph({ nodes: d.nodes ?? [], edges: d.edges ?? [] }))
      .catch(() => setGraph({ nodes: [], edges: [] }));
  }, [vault]);

  const related = useMemo(
    () =>
      page
        ? splitRelatedSection(stripLeadingTitleHeading(page.content, page.title))
        : { body: "", links: [] },
    [page]
  );

  const localGraph = useMemo(() => {
    if (!page) return { nodes: [], edges: [] };
    const relatedGraph = buildRelatedGraph(graph, page.slug, related.links);
    return relatedGraph.nodes.length > 1 ? relatedGraph : buildLocalGraph(graph, page.slug);
  }, [graph, page, related.links]);

  const currentGraphNodeId = useMemo(
    () => (page ? resolveGraphId(graph, page.slug) : null),
    [graph, page]
  );

  if (page === undefined) {
    return (
      <div
        style={{
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          padding: "48px 24px",
          color: "var(--color-muted)",
          fontFamily: "var(--font-display)",
          fontSize: 14,
        }}
      >
        문서를 불러오는 중입니다...
      </div>
    );
  }
  if (page === null) {
    return (
      <EmptyState
        icon={<EmptyIcon.File />}
        title="문서를 찾을 수 없습니다"
        description={`보관소 '${vault}'에서 '${slug}' 문서를 불러오지 못했습니다. 경로가 올바른지 확인해주세요.`}
        action={
          <Button type="button" variant="primary" size="sm" onClick={() => navigate("/")}>
            홈으로 가기
          </Button>
        }
      />
    );
  }

  return (
    <div className="page-grid">
      <article style={{ minWidth: 0 }}>
        {/* Body — InlineMarkdownEditor (자체 title+actions+editor).
            v0.7.51+ viewContent = 정돈된 본문 (related.body), 편집 모드 전환 시
            전체 MD 원본(content) 안전 수정. onDeleted는 InlineMarkdownEditor
            내부에서 deletePage 호출 — 성공 시 navigate("/"). */}
        <InlineMarkdownEditor
          vault={vault}
          slug={page.slug}
          title={page.title}
          content={page.content}
          viewContent={related.body}
          onSaved={() => {
            setReloadKey((k) => k + 1);
            ctx?.refresh?.();
          }}
          onDeleted={() => {
            ctx?.refresh?.();
          }}
          filePathRow={
            page.filePath ? (
              <div
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "6px",
                  fontSize: 11,
                  fontFamily: "ui-monospace, SFMono-Regular, monospace",
                  color: "var(--color-muted)",
                  wordBreak: "break-all",
                  backgroundColor: "var(--color-surface-hover, rgba(0,0,0,0.02))",
                  padding: "4px 8px",
                  borderRadius: "4px",
                  maxWidth: "100%",
                }}
              >
                <svg
                  width="13"
                  height="13"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  style={{ flexShrink: 0, color: "var(--color-ink-muted)" }}
                >
                  <rect x="2" y="3" width="20" height="14" rx="2" ry="2" />
                  <line x1="2" y1="10" x2="22" y2="10" />
                  <line x1="6" y1="6" x2="6.01" y2="6" />
                  <line x1="10" y1="6" x2="10.01" y2="6" />
                </svg>
                <span>물리 파일 경로: {page.filePath}</span>
                <button
                  type="button"
                  onClick={handleCopy}
                  title="복사하기"
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    justifyContent: "center",
                    background: "none",
                    border: "none",
                    padding: "2px",
                    cursor: "pointer",
                    color: copied ? "var(--color-success, #10b981)" : "var(--color-muted)",
                    borderRadius: "3px",
                    marginLeft: "4px",
                    flexShrink: 0,
                    transition: "color 0.2s, background-color 0.2s",
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.backgroundColor = "var(--color-surface-active, rgba(0,0,0,0.05))";
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.backgroundColor = "transparent";
                  }}
                >
                  {copied ? (
                    <svg
                      width="12"
                      height="12"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    >
                      <polyline points="20 6 9 17 4 12" />
                    </svg>
                  ) : (
                    <svg
                      width="12"
                      height="12"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    >
                      <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
                      <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
                    </svg>
                  )}
                </button>
              </div>
            ) : null
          }
          metaRow={
            <PageMetaRow
              type={page.type}
              slug={page.slug || page.path}
              tags={page.tags || ""}
              updated={page.updated}
            />
          }
        />

        {related.links.length > 0 && (
          <div className="page-related-links" aria-label="관련 문서">
            {related.links.map((link) => {
              const resolved = resolveGraphId(graph, link) ?? link;
              const node = graph.nodes.find((n) => n.id === resolved);
              return (
                <button
                  key={link}
                  type="button"
                  className="page-related-chip"
                  onClick={() => navigate(`/page/${vault}/${resolved}`)}
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
        currentNodeId={currentGraphNodeId}
        onOpenFullGraph={() => setShowFullGraph(true)}
      />

      {showFullGraph && localGraph.nodes.length > 0 && (
        <FullscreenGraphModal
          vault={vault}
          nodes={localGraph.nodes}
          edges={localGraph.edges}
          currentNodeId={currentGraphNodeId}
          centerTitle={`${page.title} 관련 그래프`}
          onClose={() => setShowFullGraph(false)}
        />
      )}
    </div>
  );
}
