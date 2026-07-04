import { useEffect, useRef, useState } from "react";
import { useLocation } from "react-router-dom";
import { GraphCanvas } from "./GraphCanvas";
import type { Graph, GraphNode, GraphEdge } from "../types";

const STORAGE_KEY = "raven:graph-panel:open";
const POSITION_STORAGE_KEY = "raven:graph-panel:position";

interface PanelPosition {
  left: number;
  top: number;
}

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

function readPosition(): PanelPosition | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(POSITION_STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (typeof parsed?.left === "number" && typeof parsed?.top === "number") {
      return { left: parsed.left, top: parsed.top };
    }
  } catch {
    // Ignore corrupt localStorage and fall back to the default anchored position.
  }
  return null;
}

function writePosition(position: PanelPosition | null): void {
  if (typeof window === "undefined") return;
  try {
    if (position) {
      window.localStorage.setItem(POSITION_STORAGE_KEY, JSON.stringify(position));
    } else {
      window.localStorage.removeItem(POSITION_STORAGE_KEY);
    }
  } catch {
    // localStorage might be unavailable; dragging still works for the session.
  }
}

interface FloatingGraphPanelProps {
  vault: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
  currentNodeId?: string | null;
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
  currentNodeId,
  onOpenFullGraph,
  hidden,
}: FloatingGraphPanelProps) {
  const location = useLocation();
  const [open, setOpen] = useState<boolean>(() => readOpen());
  const [position, setPosition] = useState<PanelPosition | null>(() => readPosition());
  const panelRef = useRef<HTMLDivElement | null>(null);
  const dragRef = useRef<{
    pointerId: number | null;
    offsetX: number;
    offsetY: number;
  }>({
    pointerId: null,
    offsetX: 0,
    offsetY: 0,
  });

  // Sync state when the user reloads the page in another tab.
  useEffect(() => {
    const onStorage = (e: StorageEvent) => {
      if (e.key === STORAGE_KEY) setOpen(e.newValue === "1");
    };
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  const toggle = () => {
    const next = !open;
    setOpen(next);
    writeOpen(next);
  };

  const handleOpenFull = () => {
    if (onOpenFullGraph) onOpenFullGraph();
    else window.location.assign(`/graph?vault=${encodeURIComponent(vault)}`);
  };

  useEffect(() => {
    if (!position || typeof window === "undefined") return;
    const node = panelRef.current;
    if (!node) return;
    const rect = node.getBoundingClientRect();
    const maxLeft = Math.max(12, window.innerWidth - rect.width - 12);
    const maxTop = Math.max(12, window.innerHeight - rect.height - 12);
    const clamped = {
      left: Math.min(Math.max(12, position.left), maxLeft),
      top: Math.min(Math.max(12, position.top), maxTop),
    };
    if (clamped.left !== position.left || clamped.top !== position.top) {
      setPosition(clamped);
      writePosition(clamped);
    }
  }, [position, open]);

  useEffect(() => {
    const handleWindowResize = () => {
      const node = panelRef.current;
      if (!node || typeof window === "undefined") return;
      const rect = node.getBoundingClientRect();
      setPosition((prev) => {
        if (!prev) return prev;
        const maxLeft = Math.max(12, window.innerWidth - rect.width - 12);
        const maxTop = Math.max(12, window.innerHeight - rect.height - 12);
        const next = {
          left: Math.min(Math.max(12, prev.left), maxLeft),
          top: Math.min(Math.max(12, prev.top), maxTop),
        };
        writePosition(next);
        return next;
      });
    };
    window.addEventListener("resize", handleWindowResize);
    return () => window.removeEventListener("resize", handleWindowResize);
  }, []);

  const isGraphRoute = location.pathname.startsWith("/graph");
  if (hidden || isGraphRoute) return null;
  if (nodes.length === 0) return null;

  const handleHeaderPointerDown = (e: React.PointerEvent<HTMLDivElement>) => {
    if ((e.target as HTMLElement).closest("button")) return;
    const node = panelRef.current;
    if (!node) return;
    const rect = node.getBoundingClientRect();
    dragRef.current = {
      pointerId: e.pointerId,
      offsetX: e.clientX - rect.left,
      offsetY: e.clientY - rect.top,
    };
    const target = e.currentTarget;
    target.setPointerCapture?.(e.pointerId);

    const onPointerMove = (moveEvent: PointerEvent) => {
      if (dragRef.current.pointerId !== moveEvent.pointerId || !panelRef.current) return;
      const panelRect = panelRef.current.getBoundingClientRect();
      const maxLeft = Math.max(12, window.innerWidth - panelRect.width - 12);
      const maxTop = Math.max(12, window.innerHeight - panelRect.height - 12);
      const next = {
        left: Math.min(Math.max(12, moveEvent.clientX - dragRef.current.offsetX), maxLeft),
        top: Math.min(Math.max(12, moveEvent.clientY - dragRef.current.offsetY), maxTop),
      };
      setPosition(next);
    };

    const cleanup = () => {
      window.removeEventListener("pointermove", onPointerMove);
      window.removeEventListener("pointerup", handlePointerUp);
      window.removeEventListener("pointercancel", handlePointerUp);
      dragRef.current.pointerId = null;
    };

    const handlePointerUp = (upEvent: PointerEvent) => {
      if (dragRef.current.pointerId !== upEvent.pointerId) return;
      setPosition((prev) => {
        writePosition(prev);
        return prev;
      });
      cleanup();
    };

    window.addEventListener("pointermove", onPointerMove);
    window.addEventListener("pointerup", handlePointerUp);
    window.addEventListener("pointercancel", handlePointerUp);
  };

  return (
    <div
      ref={panelRef}
      className={`floating-graph-panel${open ? " floating-graph-panel-open" : " floating-graph-panel-closed"}`}
      aria-label="관련 그래프 패널"
      style={
        position
          ? {
              left: position.left,
              top: position.top,
              right: "auto",
              bottom: "auto",
            }
          : undefined
      }
    >
      {open ? (
        <div className="floating-graph-panel-card">
          <div
            className="floating-graph-panel-header"
            onPointerDown={handleHeaderPointerDown}
            title="헤더를 잡고 패널을 옮길 수 있습니다"
          >
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
              persistentHighlightNodeId={currentNodeId}
              onFullscreen={handleOpenFull}
              onNodeClick={(slug) => window.location.assign(`/page/${vault}/${slug}`)}
              onNodeDoubleClick={(slug) => window.location.assign(`/page/${vault}/${slug}`)}
            />
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
    const id = node.id ?? "";
    if (id === centerSlug) return true;
    if (id.endsWith(`/${centerSlug}`)) return true;
    return false;
  });
  matches.forEach((n) => localIds.add(n.id ?? ""));

  if (localIds.size === 0) return { nodes: [], edges: [] };

  const localEdges = graph.edges.filter((edge) => {
    const source = edge.source;
    const target = edge.target;
    return localIds.has(source) && localIds.has(target);
  });

  return {
    nodes: graph.nodes.filter((node) => localIds.has(node.id ?? "")),
    edges: localEdges,
  };
}
