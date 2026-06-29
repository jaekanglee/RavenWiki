import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import { GraphCanvas } from "./GraphCanvas";
import type { Graph, GraphNode, GraphEdge } from "../types";

const STORAGE_KEY = "raven:graph-panel:open";

function readOpen(): boolean {
  if (typeof window === "undefined") return false;
  return window.localStorage.getItem(STORAGE_KEY) === "1";
}

function writeOpen(open: boolean): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(STORAGE_KEY, open ? "1" : "0");
  } catch {
    // localStorage might be disabled (e.g. private mode); the panel still works
    // for the current session, we just don't persist the toggle.
  }
}

interface FloatingGraphPanelProps {
  vault: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
  /** Click handler for the "전체 그래프" link — usually opens a fullscreen modal. */
  onOpenFullGraph?: () => void;
  /** When true the panel is not rendered (e.g. on /graph). */
  hidden?: boolean;
}

/**
 * FloatingGraphPanel — bottom-right overlay showing the page's related graph.
 *
 * Toggle persists in localStorage. Hidden on the dedicated /graph route so we
 * never have two competing graph surfaces in view.
 */
export function FloatingGraphPanel({
  vault,
  nodes,
  edges,
  onOpenFullGraph,
  hidden,
}: FloatingGraphPanelProps) {
  const location = useLocation();
  const [open, setOpen] = useState<boolean>(() => readOpen());

  // Sync state when the user reloads the page in another tab.
  useEffect(() => {
    const onStorage = (e: StorageEvent) => {
      if (e.key === STORAGE_KEY) setOpen(e.newValue === "1");
    };
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  const isGraphRoute = location.pathname.startsWith("/graph");
  if (hidden || isGraphRoute) return null;
  if (nodes.length === 0) return null;

  const toggle = () => {
    const next = !open;
    setOpen(next);
    writeOpen(next);
  };

  const handleOpenFull = () => {
    if (onOpenFullGraph) onOpenFullGraph();
    else window.location.assign(`/graph?vault=${encodeURIComponent(vault)}`);
  };

  return (
    <div
      className={`floating-graph-panel${open ? " floating-graph-panel-open" : " floating-graph-panel-closed"}`}
      aria-label="관련 그래프 패널"
    >
      {open ? (
        <div className="floating-graph-panel-card">
          <div className="floating-graph-panel-header">
            <strong>관련 그래프</strong>
            <span>
              {nodes.length} nodes · {edges.length} edges
            </span>
            <button
              type="button"
              className="floating-graph-panel-close"
              onClick={toggle}
              aria-label="관련 그래프 패널 접기"
              title="패널 접기"
            >
              ✕
            </button>
          </div>
          <div className="floating-graph-panel-frame">
            <GraphCanvas
              nodes={nodes}
              edges={edges}
              onNodeClick={(slug) => window.location.assign(`/page/${vault}/${slug}`)}
              onNodeDoubleClick={(slug) => window.location.assign(`/page/${vault}/${slug}`)}
            />
          </div>
          <div className="floating-graph-panel-actions">
            <button
              type="button"
              className="link-muted"
              onClick={handleOpenFull}
              title="전체 그래프 보기"
            >
              전체 그래프 →
            </button>
          </div>
        </div>
      ) : (
        <button
          type="button"
          className="floating-graph-panel-toggle"
          onClick={toggle}
          aria-label="관련 그래프 패널 열기"
          aria-expanded={false}
          title="관련 그래프 열기"
        >
          <span aria-hidden>🕸</span>
        </button>
      )}
    </div>
  );
}

// Re-export a small helper so tests can stub localStorage without a real DOM.
export const __test__ = { STORAGE_KEY, readOpen, writeOpen };

// Helper: build a local graph for the panel from the page slug.
export function buildPanelGraph(
  graph: Graph,
  centerSlug: string
): { nodes: GraphNode[]; edges: GraphEdge[] } {
  if (graph.nodes.length === 0) return { nodes: [], edges: [] };

  // Best-effort: prefer the resolveGraphId helper if the consumer has it;
  // fall back to direct membership for tests / minimal callers.
  const localIds = new Set<string>();
  const matches = graph.nodes.filter((node) => {
    const id = node.id ?? node.slug ?? "";
    if (id === centerSlug) return true;
    if (id.endsWith(`/${centerSlug}`)) return true;
    return false;
  });
  matches.forEach((n) => localIds.add(n.id ?? n.slug ?? ""));

  if (localIds.size === 0) return { nodes: [], edges: [] };

  const localEdges = graph.edges.filter((edge) => {
    const source = (edge as { source?: string }).source ?? edge.source_slug;
    const target = (edge as { target?: string }).target ?? edge.target_slug;
    return localIds.has(source) && localIds.has(target);
  });

  return {
    nodes: graph.nodes.filter((node) => localIds.has(node.id ?? node.slug ?? "")),
    edges: localEdges,
  };
}
