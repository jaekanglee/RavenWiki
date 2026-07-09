import { useEffect, useRef, useState } from "react";
import { useLocation } from "react-router-dom";
import { GraphCanvas } from "./GraphCanvas";
import type { Graph, GraphNode, GraphEdge } from "../types";

const STORAGE_KEY = "raven:graph-panel:open";
const POSITION_STORAGE_KEY = "raven:graph-panel:position";

/** right/bottom 기준 좌표 — CSS 기본 앵커(right:24,bottom:24)와 동일 방향 */
interface PanelPosition {
  right: number;
  bottom: number;
}

const DEFAULT_POSITION: PanelPosition = { right: 24, bottom: 24 };

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
    // Support only new right/bottom format — discard old left/top entries.
    if (typeof parsed?.right === "number" && typeof parsed?.bottom === "number") {
      return { right: parsed.right, bottom: parsed.bottom };
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
 *
 * Position is stored as right/bottom (distance from viewport edges) so the
 * default CSS anchor (right:24px, bottom:24px) is always honored when no drag
 * has occurred, and the card grows upward without clipping.
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
  // null = use CSS defaults (right:24px, bottom:24px). Non-null = user dragged.
  const [position, setPosition] = useState<PanelPosition | null>(() => readPosition());
  const panelRef = useRef<HTMLDivElement | null>(null);
  const dragRef = useRef<{
    pointerId: number | null;
    offsetFromRight: number;
    offsetFromBottom: number;
  }>({
    pointerId: null,
    offsetFromRight: 0,
    offsetFromBottom: 0,
  });

  // Sync state when the user reloads the page in another tab.
  useEffect(() => {
    const onStorage = (e: StorageEvent) => {
      if (e.key === STORAGE_KEY) setOpen(e.newValue === "1");
    };
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  // Clamp position when panel size or window changes.
  useEffect(() => {
    if (!position || typeof window === "undefined") return;
    const node = panelRef.current;
    if (!node) return;
    const rect = node.getBoundingClientRect();
    const maxRight = Math.max(12, window.innerWidth - rect.width - 12);
    const maxBottom = Math.max(12, window.innerHeight - rect.height - 12);
    const clamped = {
      right: Math.min(Math.max(12, position.right), maxRight),
      bottom: Math.min(Math.max(12, position.bottom), maxBottom),
    };
    if (clamped.right !== position.right || clamped.bottom !== position.bottom) {
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
        const maxRight = Math.max(12, window.innerWidth - rect.width - 12);
        const maxBottom = Math.max(12, window.innerHeight - rect.height - 12);
        const next = {
          right: Math.min(Math.max(12, prev.right), maxRight),
          bottom: Math.min(Math.max(12, prev.bottom), maxBottom),
        };
        writePosition(next);
        return next;
      });
    };
    window.addEventListener("resize", handleWindowResize);
    return () => window.removeEventListener("resize", handleWindowResize);
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

  const isGraphRoute = location.pathname.startsWith("/graph");
  if (hidden || isGraphRoute) return null;
  if (nodes.length === 0) return null;

  const handleHeaderPointerDown = (e: React.PointerEvent<HTMLDivElement>) => {
    if ((e.target as HTMLElement).closest("button")) return;
    e.preventDefault(); // Prevent touch/scroll default gestures from canceling drag
    const node = panelRef.current;
    if (!node) return;
    const rect = node.getBoundingClientRect();
    // 패널의 우측/하단 엣지 ~ 뷰포트 엣지까지의 거리 + 포인터 오프셋 기록
    dragRef.current = {
      pointerId: e.pointerId,
      offsetFromRight: e.clientX - rect.right,   // 포인터가 패널 우측으로부터 얼마나 안쪽
      offsetFromBottom: e.clientY - rect.bottom,  // 포인터가 패널 하단으로부터 얼마나 안쪽
    };
    // 드래그 시작 시 현재 right/bottom을 state에 기록 (CSS → inline 전환)
    const initPos = {
      right: window.innerWidth - rect.right,
      bottom: window.innerHeight - rect.bottom,
    };
    setPosition(initPos);
    const target = e.currentTarget;
    target.setPointerCapture?.(e.pointerId);

    const onPointerMove = (moveEvent: PointerEvent) => {
      if (dragRef.current.pointerId !== moveEvent.pointerId || !panelRef.current) return;
      const panelRect = panelRef.current.getBoundingClientRect();
      // 새 right = 뷰포트 우측 - (포인터X - 오프셋)
      const newRight = window.innerWidth - (moveEvent.clientX - dragRef.current.offsetFromRight);
      const newBottom = window.innerHeight - (moveEvent.clientY - dragRef.current.offsetFromBottom);
      const maxRight = Math.max(12, window.innerWidth - panelRect.width - 12);
      const maxBottom = Math.max(12, window.innerHeight - panelRect.height - 12);
      setPosition({
        right: Math.min(Math.max(12, newRight), maxRight),
        bottom: Math.min(Math.max(12, newBottom), maxBottom),
      });
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

  // position이 null이면 CSS의 right:24px/bottom:24px가 그대로 적용됨.
  // position이 있으면 inline으로 right/bottom override.
  const pos = position ?? DEFAULT_POSITION;

  return (
    <div
      ref={panelRef}
      className={`floating-graph-panel${open ? " floating-graph-panel-open" : " floating-graph-panel-closed"}`}
      aria-label="관련 그래프 패널"
      style={{
        right: pos.right,
        bottom: pos.bottom,
        left: "auto",
        top: "auto",
      }}
    >
      {open ? (
        <div className="floating-graph-panel-card">
          <div
            className="floating-graph-panel-header"
            onPointerDown={handleHeaderPointerDown}
            title="헤더를 잡고 패널을 드래그해 화면 어디든 이동할 수 있습니다"
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
              variant="minimap"
              density="dense"
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
