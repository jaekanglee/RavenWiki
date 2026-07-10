import { useEffect, useMemo, useRef, useState } from "react";
import ForceGraph from "force-graph";
import type { GraphNode, GraphEdge } from "../types";

interface Props {
  nodes: GraphNode[];
  edges: GraphEdge[];
  /** 중심 깊이/레이어 계산의 기준이 되는 노드 ID. */
  focusNodeId?: string | null;
  /** hover/click 시 선택 노드 메타를 상위 UI에 전달 */
  onNodeInspect?: (node: GraphNode) => void;
  /** single click — 데스크탑 전용 (페이지 이동) */
  onNodeClick?: (slug: string) => void;
  /** double click / double tap — 페이지 이동 */
  onNodeDoubleClick?: (slug: string) => void;
  /** 외부(인사이트 카드 등)에서 하이라이트 요청한 노드 ID */
  externalHighlightNodeId?: string | null;
  /** 현재 문서처럼 항상 강조해야 하는 노드 ID */
  persistentHighlightNodeId?: string | null;
  /** 외부에서 하이라이트 요청한 문서 타입 */
  externalHighlightType?: string | null;
  /** 전체화면 모달 요청 — 상위 컴포넌트가 모달을 열어 처리 */
  onFullscreen?: () => void;
  /** all-vault 등 고밀도 그래프에서는 기본 라벨/엣지를 낮춰 지도 시인성을 우선한다.
   * v0.7.144+: all-scope 모드 제거되어 더 이상 사용처 없음 — 보존 (재사용 가능). */
  density?: "normal" | "dense";
  /** 노드 드래그 종료 시점에 호출 */
  onPositionsChange?: (positions: Record<string, { x: number; y: number }>) => void;
  /** 캔버스 빈 공간 클릭 시 호출 */
  onBackgroundClick?: () => void;
  /** 그래프 캔버스의 용도 (기본형 vs 미니맵용) */
  variant?: "default" | "minimap";
  /** 그래프 시각화 레이아웃 모드 (기본 force-directed) */
  layoutMode?: GraphLayoutMode;
}

export type GraphLayoutMode = "force" | "concentric" | "domain" | "timeline" | "layered";

// SCHEMA 9종(v0.7.44+) — type별 노드 색상. 미분류/미인식 → default gray.
const TYPE_COLORS: Record<string, string> = {
  concept: "#22c55e",
  person: "#ec4899",
  tool: "#6b7280",
  comparison: "#ef4444",
  project: "#f97316",
  rule: "#6366f1",
  query: "#eab308",
  journal: "#06b6d4",
  issue: "#a855f7",
};
const DEFAULT_COLOR = "#9ca3af";

export function nodeColor(type: string | undefined): string {
  if (!type) return DEFAULT_COLOR;
  return TYPE_COLORS[type] ?? DEFAULT_COLOR;
}

/**
 * v0.7.136: dense에서 multiplier 7 → 4, base 10 → 7. 이전 dense 노드는
 * weight=10에서 38px (큰 동그라미 빽빽), hub는 48px로 화면 점유 과다.
 * 사용자 보고: dense 모드 노드가 "두껍다".
 *   - normal: 8 + log2(1+w)*6  (leaf 14, w=10 → 27.93, w=24 → 36.20)
 *   - dense:  7 + log2(1+w)*4  (leaf 11, w=10 → 20.28, w=24 → 25.81)
 */
export function nodeSize(
  weight: number | undefined,
  density: "normal" | "dense" = "normal",
  importance?: number | null,
  totalNodes?: number
): number {
  const w = Math.max(weight ?? 1, 1);
  const multiplier = density === "dense" ? 4 : 6;
  const base = density === "dense" ? 7 : 8;
  const baseSize = base + Math.log2(1 + w) * multiplier;

  if (typeof importance === "number" && typeof totalNodes === "number" && totalNodes > 0) {
    // PageRank 값은 평균 1.0/N 이다.
    // N * PageRank 를 하면 평균이 1.0이 된다.
    const relativeImportance = importance * totalNodes;
    const importanceFactor = Math.max(0.5, Math.min(relativeImportance, 4.0));
    return baseSize * (0.7 + Math.sqrt(importanceFactor) * 0.8);
  }
  return baseSize;
}

const TYPE_LABELS: Record<string, string> = {
  concept: "개념",
  person: "인물",
  tool: "도구",
  comparison: "비교",
  project: "프로젝트",
  rule: "규칙",
  query: "Q&A",
  journal: "일지",
  issue: "이슈",
};

const RELATION_COLORS: Record<string, string> = {
  uses: "#3b82f6",         // blue
  depends_on: "#ef4444",   // red
  implements: "#a855f7",   // purple
  implemented_by: "#d946ef", // fuchsia
  related: "#14b8a6",      // teal
};

const RELATION_DASHES: Record<string, number[]> = {
  uses: [],
  depends_on: [],
  implements: [6, 3],
  implemented_by: [2, 3],
  related: [4, 4],
};

const RELATION_LABELS: Record<string, string> = {
  uses: "Uses (사용함)",
  depends_on: "Depends on (의존함)",
  implements: "Implements (구현함)",
  implemented_by: "Implemented by (구현체)",
  related: "Related (연관)",
};

export function typeLabel(type: string | undefined): string {
  if (!type) return "";
  return TYPE_LABELS[type] ?? "";
}

export function nodeOpacity(freshness: number | null | undefined): number {
  if (typeof freshness !== "number" || Number.isNaN(freshness)) return 1;
  const normalized = Math.max(0, Math.min(freshness, 1));
  return 0.32 + normalized * 0.68;
}

export function computeFocusDepthMap(
  nodes: GraphNode[],
  edges: GraphEdge[],
  focusNodeId?: string | null,
  maxDepth = 3
): Map<string, number> {
  const focusId = focusNodeId?.trim();
  if (!focusId) return new Map();
  const nodeIds = new Set(nodes.map((node) => node.id));
  if (!nodeIds.has(focusId)) return new Map();

  const adjacency = new Map<string, Set<string>>();
  const addEdge = (source: string, target: string) => {
    if (!nodeIds.has(source) || !nodeIds.has(target)) return;
    if (!adjacency.has(source)) adjacency.set(source, new Set());
    if (!adjacency.has(target)) adjacency.set(target, new Set());
    adjacency.get(source)?.add(target);
    adjacency.get(target)?.add(source);
  };

  for (const edge of edges) {
    addEdge(String(edge.source), String(edge.target));
  }

  const depthMap = new Map<string, number>();
  const queue: Array<{ id: string; depth: number }> = [{ id: focusId, depth: 0 }];
  depthMap.set(focusId, 0);

  while (queue.length > 0) {
    const current = queue.shift();
    if (!current || current.depth >= maxDepth) continue;
    const neighbors = adjacency.get(current.id);
    if (!neighbors) continue;
    for (const nextId of neighbors) {
      if (depthMap.has(nextId)) continue;
      const nextDepth = current.depth + 1;
      depthMap.set(nextId, nextDepth);
      queue.push({ id: nextId, depth: nextDepth });
    }
  }

  return depthMap;
}

export function computeLayeredLayout(nodes: GraphNode[]): Record<string, { x: number; y: number }> {
  const layers = new Map<number, GraphNode[]>();
  let minLayer = Number.POSITIVE_INFINITY;
  let maxLayer = Number.NEGATIVE_INFINITY;

  nodes.forEach((node) => {
    const layerValue = typeof node.layer === "number" && Number.isFinite(node.layer)
      ? node.layer
      : 0;
    const bucket = Math.max(0, Math.round(layerValue));
    minLayer = Math.min(minLayer, bucket);
    maxLayer = Math.max(maxLayer, bucket);
    const group = layers.get(bucket) ?? [];
    group.push(node);
    layers.set(bucket, group);
  });

  if (!Number.isFinite(minLayer) || !Number.isFinite(maxLayer)) {
    return {};
  }

  const xStart = -430;
  const xEnd = 430;
  const layerSpan = Math.max(1, maxLayer - minLayer);
  const layerCoords: Record<string, { x: number; y: number }> = {};

  [...layers.entries()]
    .sort((a, b) => a[0] - b[0])
    .forEach(([layer, group]) => {
      const ratio = (layer - minLayer) / layerSpan;
      const x = xStart + ratio * (xEnd - xStart);
      const sortedGroup = [...group].sort((a, b) => {
        const importanceDiff = (b.importance ?? 0) - (a.importance ?? 0);
        if (importanceDiff !== 0) return importanceDiff;
        return a.id.localeCompare(b.id);
      });
      const count = sortedGroup.length;
      const spacing = Math.min(90, Math.max(42, 340 / Math.max(1, count)));

      sortedGroup.forEach((node, idx) => {
        const offsetIndex = idx - (count - 1) / 2;
        const curvature = count > 1 ? Math.sin((idx / Math.max(1, count - 1)) * Math.PI) : 0;
        layerCoords[node.id] = {
          x,
          y: offsetIndex * spacing + curvature * 18,
        };
      });
    });

  return layerCoords;
}

const isJSDOM =
  typeof window !== "undefined" &&
  (window.navigator.userAgent.includes("jsdom") ||
    window.navigator.userAgent.includes("Node.js"));

const GRAPH_SCALE_MULTIPLIER = 2.8;
const DIRECT_CLICK_PADDING_PX = 0;
const DIRECT_MOUSE_HIT_RADIUS_PX = 0;
const DIRECT_TOUCH_HIT_RADIUS_PX = 0;
const DIRECT_HIT_NODE_RADIUS_MULTIPLIER = 1;
const DIRECT_MOUSE_MOVE_TOLERANCE_PX = 8;
const DIRECT_TOUCH_MOVE_TOLERANCE_PX = 14;
const DOUBLE_CLICK_DELAY_MS = 200;

interface CanvasPoint {
  x: number;
  y: number;
}

interface HitTestNode {
  id: string;
  x?: number;
  y?: number;
  fx?: number;
  fy?: number;
  weight?: number;
  importance?: number;
}

export function isStationaryClickGesture(
  start: CanvasPoint | null,
  end: CanvasPoint,
  pointerType: "mouse" | "touch"
): boolean {
  if (!start) return true;
  const dx = end.x - start.x;
  const dy = end.y - start.y;
  const tolerance = pointerType === "touch"
    ? DIRECT_TOUCH_MOVE_TOLERANCE_PX
    : DIRECT_MOUSE_MOVE_TOLERANCE_PX;
  return Math.hypot(dx, dy) <= tolerance;
}

export function findClosestNodeHit<T extends HitTestNode>(
  nodes: T[],
  point: CanvasPoint,
  density: "normal" | "dense",
  padding = DIRECT_CLICK_PADDING_PX,
  scale = 1,
  minScreenRadius = DIRECT_MOUSE_HIT_RADIUS_PX
): T | null {
  let closest: T | null = null;
  let closestDistSq = Number.POSITIVE_INFINITY;

  const safeScale = typeof scale === "number" && scale > 0 ? scale : 1;
  const minCanvasRadius = Math.max(minScreenRadius, 0) / safeScale;

  for (const node of nodes) {
    const x = typeof node.x === "number" ? node.x : node.fx;
    const y = typeof node.y === "number" ? node.y : node.fy;
    if (typeof x !== "number" || typeof y !== "number") continue;
    const dx = point.x - x;
    const dy = point.y - y;
    const distSq = dx * dx + dy * dy;
    const visualRadius = nodeSize(node.weight, density, node.importance, nodes.length) * DIRECT_HIT_NODE_RADIUS_MULTIPLIER;
    const radius = Math.max(visualRadius + padding / safeScale, minCanvasRadius);
    if (distSq > radius * radius) continue;
    if (distSq < closestDistSq) {
      closest = node;
      closestDistSq = distSq;
    }
  }

  return closest;
}

export function shouldShowLabel(
  node: { type?: string; weight?: number },
  scale: number,
  isDense: boolean,
  isFocused: boolean,
  isHighlighted: boolean
): boolean {
  if (isFocused || isHighlighted) return true;
  if (scale < 0.7) return false;

  const isIssue = node.type === "issue";
  if (isDense) {
    return (
      (scale > 1.15 && (node.weight ?? 0) >= 3) ||
      (isIssue && scale > 1.15)
    );
  } else {
    return (
      (scale > 1.0 && (node.weight ?? 0) >= 3) ||
      (node.weight ?? 0) >= 8 ||
      (isIssue && scale > 1.0)
    );
  }
}

// v0.7.134+ (v0.7.144에서 resolveVaultColor 헬퍼와 함께 VAULT_HALO_COLORS 제거 —
// all-scope 모드 제거되면서 vault 색 식별 코드 사용처 사라짐).
// hexToRgba는 보존 (다른 ring 효과 재사용 가능).
function hexToRgba(hex: string, alpha: number): string {
  const m = hex.replace("#", "").match(/^([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})$/i);
  if (!m) return hex;
  const r = parseInt(m[1], 16);
  const g = parseInt(m[2], 16);
  const b = parseInt(m[3], 16);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

// rounded-rect 헬퍼 제거 — v0.7.139+: onRenderFramePre에서 그리던 vault halo 박스를
// 삭제하면서 호출처가 사라졌다. 향후 다른 캔버스 도형이 필요하면 재도입.



const GRAPH_LABEL_FONT = "system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif";
const HUD_LABEL_FONT = GRAPH_LABEL_FONT;
const HUD_LABEL_BASE_SIZE = 17; // 더 크게 (14 -> 17)
const NODE_LABEL_BASE_SIZE = 11.4;

export function GraphCanvas({
  nodes,
  edges,
  focusNodeId,
  onNodeInspect,
  onNodeClick,
  onNodeDoubleClick,
  externalHighlightNodeId,
  persistentHighlightNodeId,
  externalHighlightType,
  onFullscreen,
  density = "normal",
  onPositionsChange,
  onBackgroundClick,
  variant = "default",
  layoutMode = "force",
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const graphInstanceRef = useRef<any>(null);
  const isDense = density === "dense";
  // v0.7.139+: fitView 트리거 추적. scope 전환(all ↔ current) 또는 첫 데이터 로드 시에만
  // 호출하기 위해 직전 isDense와 노드 수를 보관. 검색/필터로 nodes가 바뀌어도
  // 사용자의 pan/zoom 위치가 reset되지 않는다.
  const prevIsDenseRef = useRef<boolean | null>(null);
  const prevNodeCountRef = useRef<number>(0);
  const graphNodesRef = useRef<any[]>([]);
  const pressStartRef = useRef<{ point: CanvasPoint; pointerType: "mouse" | "touch" } | null>(null);
  const pendingClickRef = useRef<{ nodeId: string; timeoutId: number; startedAt: number } | null>(null);
  const clickHandlersRef = useRef({
    onNodeClick,
    onNodeDoubleClick,
    onBackgroundClick,
  });

  const [hoveredNode, setHoveredNodeState] = useState<any>(null);
  // v0.7.139+: 현재 zoom 배율 (force-graph의 zoom() 값). onZoom 콜백에서 갱신.
  const [zoomLevel, setZoomLevel] = useState<number>(1);
  // v0.7.139+: hoveredNode를 ref로도 미러링. force-graph의 linkColor/linkWidth/
  // nodeCanvasObject는 effect 등록 시점의 클로저를 매 paint call에서 호출하므로,
  // 매번 최신 hover 상태를 보려면 ref가 필요. ref 덕분에 hoveredNode 변경 시
  // effect가 재실행되지 않아 — 캔버스가 pan/zoom 위치를 잃지 않고, 클릭이 무효화되지 않음.
  const hoveredNodeRef = useRef<any>(null);
  const setHoveredNode = (node: any) => {
    hoveredNodeRef.current = node;
    setHoveredNodeState(node);
  };

  const resolvedLabelColorRef = useRef<string>("rgba(148, 163, 184, 0.7)");
  const resolvedBgColorRef = useRef<string>("#0f172a");
  const resolvedNodeOutlineRef = useRef<string>("rgba(226, 232, 240, 0.28)");
  const resolvedEdgeColorRef = useRef<string>("rgba(148, 163, 184, 0.38)");
  const resolvedEdgeHighlightRef = useRef<string>("rgba(196, 181, 253, 0.94)");
  const focusDepthMap = useMemo(
    () => computeFocusDepthMap(nodes, edges, focusNodeId),
    [nodes, edges, focusNodeId]
  );

  // DOM Container 변경 및 테마 변경 시 Computed Style 캐싱
  useEffect(() => {
    if (isJSDOM || !containerRef.current) return;
    try {
      const style = window.getComputedStyle(containerRef.current);
      resolvedLabelColorRef.current = style.getPropertyValue("--graph-label-color").trim() || "rgba(148, 163, 184, 0.7)";
      resolvedBgColorRef.current = style.getPropertyValue("--graph-canvas-bg").trim() || "#0f172a";
      resolvedNodeOutlineRef.current = style.getPropertyValue("--graph-node-outline").trim() || "rgba(226, 232, 240, 0.28)";
      resolvedEdgeColorRef.current = style.getPropertyValue("--graph-edge").trim() || "rgba(148, 163, 184, 0.38)";
      resolvedEdgeHighlightRef.current = style.getPropertyValue("--graph-edge-highlight").trim() || "rgba(196, 181, 253, 0.94)";
    } catch (e) {
      // fallback
    }
  }, [nodes]);

  useEffect(() => {
    clickHandlersRef.current = { onNodeClick, onNodeDoubleClick, onBackgroundClick };
  }, [onNodeClick, onNodeDoubleClick, onBackgroundClick]);

  useEffect(() => {
    return () => {
      if (pendingClickRef.current) {
        window.clearTimeout(pendingClickRef.current.timeoutId);
        pendingClickRef.current = null;
      }
    };
  }, []);

  // 1. 하이라이트 및 인접 관계 집합 계산 (ref 기반 — effect deps 안 들어감)
  const highlightNodesRef = useRef<Set<string>>(new Set());
  const highlightLinksRef = useRef<Set<string>>(new Set());

  // v0.7.144+: all-scope 제거 — vault centroids + 최상단 y ref 모두 불필요.
  // (참조하던 코드: vaultCentroidsRef, vaultTopYRef, drawVaultLabel)

  const recomputeHighlights = (hover: any, extId: string | null | undefined, edgeList: typeof edges) => {
    const nodeSet = new Set<string>();
    const linkSet = new Set<string>();
    if (hover) {
      nodeSet.add(hover.id);
      edgeList.forEach((e) => {
        if (e.source === hover.id) nodeSet.add(e.target);
        if (e.target === hover.id) nodeSet.add(e.source);
      });
    }
    if (extId) {
      nodeSet.add(extId);
      edgeList.forEach((e) => {
        if (e.source === extId) nodeSet.add(e.target);
        if (e.target === extId) nodeSet.add(e.source);
      });
    }
    edgeList.forEach((e, idx) => {
      const id = `e${idx}`;
      if (hover && (e.source === hover.id || e.target === hover.id)) linkSet.add(id);
      if (extId && (e.source === extId || e.target === extId)) linkSet.add(id);
    });
    highlightNodesRef.current = nodeSet;
    highlightLinksRef.current = linkSet;
  };

  // (v0.7.139+: 이동 모드 토글 제거 — force-graph native pan/zoom이 항상 동작한다.
  // Space 단축키 핸들러도 함께 제거됨. dense 모드에서도 노드 탭 → 인사이트,
  // 더블탭 → 페이지 이동, 드래그 → 캔버스 팬으로 통일.)

  // 2. force-graph 인스턴스 초기 생성 (런타임 callable 우회를 위해 캐스팅 및 default export 감지 방어 적용)
  useEffect(() => {
    if (isJSDOM || !containerRef.current) return;

    const ForceGraphConstructor = typeof ForceGraph === "function"
      ? ForceGraph
      : (ForceGraph as any).default || ForceGraph;

    if (typeof ForceGraphConstructor !== "function") {
      console.error("ForceGraph is not a function! Check import:", ForceGraph);
      return;
    }

    const graph = (ForceGraphConstructor as any)()(containerRef.current);
    graphInstanceRef.current = graph;

    // v0.7.149+: D3 center force를 제거하여 force-graph가 렌더 틱마다 중심을 (width/2, height/2)로
    // 강제 덮어쓰고 우측 하단으로 노드들을 끌어당기는 현상을 원천 차단.
    // charge 및 link 힘은 살려두어, 좌표가 고정되지 않은 신규 노드들이 겹치지 않고 흩어지도록 구성.
    graph.d3Force("center", null);
    // 드래그 직후 연결 노드가 자연스럽게 안정화할 짧은 시간은 남긴다.
    // 0ms면 native drag가 reset한 simulation이 첫 tick 전에 멈출 수 있다.
    graph.cooldownTime(600);

    // 인터랙션 기본 설정
    graph.enableZoomInteraction(true);
    graph.enablePanInteraction(true);

    // v0.7.150+: ResizeObserver로 캔버스 크기 변화를 실시간 반영하여 우하단 쏠림 및 잘림 현상 방지
    const resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width, height } = entry.contentRect;
        if (width > 0 && height > 0) {
          graph.width(width).height(height);
        }
      }
    });
    resizeObserver.observe(containerRef.current);

    return () => {
      resizeObserver.disconnect();
      if (graphInstanceRef.current) {
        graphInstanceRef.current._destructor?.();
      }
    };
  }, []);

  // 3. Props 및 인터랙션 상태 변경 시 그래프 동기화
  useEffect(() => {
    if (isJSDOM) return;
    const graph = graphInstanceRef.current;
    if (!graph) return;

    // layoutMode에 따라 노드 배치 좌표를 실시간 산출
    let formattedNodes: any[] = [];

    if (layoutMode === "force") {
      formattedNodes = nodes.map((n) => {
        const hasPos = typeof n.x === "number" && typeof n.y === "number";
        const scaledX = hasPos ? (n.x as number) * GRAPH_SCALE_MULTIPLIER : (Math.random() - 0.5) * 16;
        const scaledY = hasPos ? (n.y as number) * GRAPH_SCALE_MULTIPLIER : (Math.random() - 0.5) * 16;
        const focusDepth = focusDepthMap.get(n.id);
        const depthRank = typeof focusDepth === "number" ? focusDepth : Number.POSITIVE_INFINITY;
        return {
          ...n,
          x: scaledX,
          y: scaledY,
          fx: hasPos ? scaledX : undefined,
          fy: hasPos ? scaledY : undefined,
          __focusDepth: focusDepth,
          __focusDepthRank: depthRank,
        };
      });
      if (focusDepthMap.size > 0) {
        formattedNodes.sort((a: any, b: any) => {
          const depthA = typeof a.__focusDepthRank === "number" ? a.__focusDepthRank : Number.POSITIVE_INFINITY;
          const depthB = typeof b.__focusDepthRank === "number" ? b.__focusDepthRank : Number.POSITIVE_INFINITY;
          if (depthA !== depthB) return depthB - depthA;
          const importanceDiff = (b.importance ?? 0) - (a.importance ?? 0);
          if (importanceDiff !== 0) return importanceDiff;
          const weightDiff = (b.weight ?? 0) - (a.weight ?? 0);
          if (weightDiff !== 0) return weightDiff;
          return String(a.id).localeCompare(String(b.id));
        });
      }
    } else if (layoutMode === "concentric") {
      // 1) Concentric View: 특정 노드(또는 중요도가 가장 높은 노드)를 중심으로 N촌 동심원 배치
      const centerId =
        externalHighlightNodeId && nodes.some(n => n.id === externalHighlightNodeId)
          ? externalHighlightNodeId
          : (persistentHighlightNodeId && nodes.some(n => n.id === persistentHighlightNodeId)
            ? persistentHighlightNodeId
            : (nodes.length > 0
              ? [...nodes].sort((a, b) => (b.importance ?? 0) - (a.importance ?? 0))[0].id
              : ""));

      // Adjacency 빌드 (무방향)
      const adj: Record<string, string[]> = {};
      nodes.forEach(n => { adj[n.id] = []; });
      edges.forEach(e => {
        const u = typeof e.source === "object" ? (e.source as any).id : e.source;
        const v = typeof e.target === "object" ? (e.target as any).id : e.target;
        if (adj[u] && adj[v]) {
          if (!adj[u].includes(v)) adj[u].push(v);
          if (!adj[v].includes(u)) adj[v].push(u);
        }
      });

      // BFS 최단거리 계산
      const dists: Record<string, number> = {};
      nodes.forEach(n => { dists[n.id] = 999999; });

      if (centerId && adj[centerId]) {
        dists[centerId] = 0;
        const queue = [centerId];
        let head = 0;
        while (head < queue.length) {
          const u = queue[head++];
          const currentDist = dists[u];
          for (const v of adj[u]) {
            if (dists[v] === 999999) {
              dists[v] = currentDist + 1;
              queue.push(v);
            }
          }
        }
      }

      // 거리 그룹화
      const distanceGroups: Record<number, string[]> = {};
      nodes.forEach(n => {
        const d = dists[n.id];
        distanceGroups[d] ??= [];
        distanceGroups[d].push(n.id);
      });

      const nodeCoords: Record<string, { x: number; y: number }> = {};
      if (centerId) {
        nodeCoords[centerId] = { x: 0, y: 0 };
      }

      const sortedDistances = Object.keys(distanceGroups)
        .map(Number)
        .filter(d => d > 0 && d !== 999999)
        .sort((a, b) => a - b);

      sortedDistances.forEach((d) => {
        const group = distanceGroups[d];
        const count = group.length;
        const radius = d * 180;
        group.forEach((nodeId, idx) => {
          const theta = (2 * Math.PI * idx) / count;
          nodeCoords[nodeId] = {
            x: radius * Math.cos(theta),
            y: radius * Math.sin(theta),
          };
        });
      });

      const disconnected = distanceGroups[999999] || [];
      if (disconnected.length > 0) {
        const maxD = sortedDistances.length > 0 ? sortedDistances[sortedDistances.length - 1] : 0;
        const radius = (maxD + 1.2) * 190;
        disconnected.forEach((nodeId, idx) => {
          const theta = (2 * Math.PI * idx) / disconnected.length;
          nodeCoords[nodeId] = {
            x: radius * Math.cos(theta),
            y: radius * Math.sin(theta),
          };
        });
      }

      formattedNodes = nodes.map((n) => {
        const coord = nodeCoords[n.id] || { x: 0, y: 0 };
        return {
          ...n,
          x: coord.x,
          y: coord.y,
          fx: coord.x,
          fy: coord.y,
        };
      });
    } else if (layoutMode === "domain") {
      // 2) Domain View: Louvain community ID별 노드 분산 배치
      const communities: Record<number, string[]> = {};
      nodes.forEach((n) => {
        const c = n.community ?? 0;
        communities[c] ??= [];
        communities[c].push(n.id);
      });

      const communityIds = Object.keys(communities).map(Number).sort((a, b) => a - b);
      const K = communityIds.length;

      const centerCoords: Record<number, { x: number; y: number }> = {};
      if (K <= 1) {
        centerCoords[communityIds[0] ?? 0] = { x: 0, y: 0 };
      } else {
        const ringRadius = Math.max(300, K * 75);
        communityIds.forEach((cid, idx) => {
          const theta = (2 * Math.PI * idx) / K;
          centerCoords[cid] = {
            x: ringRadius * Math.cos(theta),
            y: ringRadius * Math.sin(theta),
          };
        });
      }

      const nodeCoords: Record<string, { x: number; y: number }> = {};
      communityIds.forEach((cid) => {
        const group = communities[cid];
        const count = group.length;
        const center = centerCoords[cid];
        const clusterRadius = 45 + Math.sqrt(count) * 15;

        group.forEach((nodeId, idx) => {
          if (count === 1) {
            nodeCoords[nodeId] = { x: center.x, y: center.y };
          } else {
            const theta = (2 * Math.PI * idx) / count;
            nodeCoords[nodeId] = {
              x: center.x + clusterRadius * Math.cos(theta),
              y: center.y + clusterRadius * Math.sin(theta),
            };
          }
        });
      });

      formattedNodes = nodes.map((n) => {
        const coord = nodeCoords[n.id] || { x: 0, y: 0 };
        return {
          ...n,
          x: coord.x,
          y: coord.y,
          fx: coord.x,
          fy: coord.y,
        };
      });
    } else if (layoutMode === "timeline") {
      // 3) Timeline View: 작성일/수정일 기준 가로 축 정렬 배치 (Adaptive Scale 보정 적용)
      const parseDate = (dateStr: string | undefined): number => {
        if (!dateStr) return 0;
        try {
          const clean = dateStr.trim().substring(0, 10);
          return Date.parse(clean) || 0;
        } catch {
          return 0;
        }
      };

      const nowTime = Date.now();
      const nodeTimes = nodes.map((n) => {
        let t = parseDate(n.created) || parseDate(n.updated) || nowTime;
        return { id: n.id, time: t };
      });

      const times = nodeTimes.map((nt) => nt.time);
      const minTime = times.length > 0 ? Math.min(...times) : nowTime;
      const maxTime = times.length > 0 ? Math.max(...times) : nowTime;
      const timeDiff = maxTime - minTime || 1;

      const xStart = -450;
      const xEnd = 450;

      // 일(Day) 단위 격자/밀집도 분석
      const isShortRange = timeDiff <= 24 * 60 * 60 * 1000;
      const getGroupKey = (t: number): string => {
        const d = new Date(t);
        if (isShortRange) {
          return `${d.getFullYear()}-${d.getMonth()}-${d.getDate()} H${d.getHours()}`;
        } else {
          return `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`;
        }
      };

      // 그룹별 노드 매핑
      const groups: Record<string, string[]> = {};
      nodes.forEach((n) => {
        const nt = nodeTimes.find((x) => x.id === n.id);
        const t = nt ? nt.time : nowTime;
        const key = getGroupKey(t);
        groups[key] = groups[key] || [];
        groups[key].push(n.id);
      });

      const nodeCoords: Record<string, { x: number; y: number }> = {};
      const typeYOffsets: Record<string, number> = {
        concept: 150,
        project: 75,
        rule: 0,
        journal: -75,
        issue: -150,
      };

      const typeIndices: Record<string, number> = {};

      nodes.forEach((n) => {
        const nt = nodeTimes.find((x) => x.id === n.id);
        const time = nt ? nt.time : nowTime;
        
        // 1차 선형 X 좌표
        const baseX = xStart + ((time - minTime) / timeDiff) * (xEnd - xStart);

        // 2차 그룹 내 오프셋 (동일 시간대/날짜 밀집 노드 펼치기)
        const key = getGroupKey(time);
        const group = groups[key] || [];
        const groupIndex = group.indexOf(n.id);
        const groupCount = group.length;

        let adaptiveOffsetX = 0;
        if (groupCount > 1) {
          // 밀집 보정 필터: 그룹 내 노드 수에 따라 좌우로 유연하게 분산 (최대 120px 너비 내에서 분산)
          const spacing = Math.max(12, Math.min(35, 120 / groupCount));
          adaptiveOffsetX = (groupIndex - (groupCount - 1) / 2) * spacing;
        }

        const x = baseX + adaptiveOffsetX;

        const type = n.type || "other";
        typeIndices[type] ??= 0;
        const index = typeIndices[type]++;

        const baseY = typeYOffsets[type] !== undefined ? typeYOffsets[type] : -220;
        const offsetSign = index % 2 === 0 ? 1 : -1;
        const yOffset = offsetSign * (15 + (index % 3) * 10);
        const y = baseY + yOffset;

        nodeCoords[n.id] = { x, y };
      });

      formattedNodes = nodes.map((n) => {
        const coord = nodeCoords[n.id] || { x: 0, y: 0 };
        return {
          ...n,
          x: coord.x,
          y: coord.y,
          fx: coord.x,
          fy: coord.y,
        };
      });
    } else if (layoutMode === "layered") {
      // 4) Layered View: 분석된 layer 값을 가로축 깊이로 사용.
      // Concentric가 "선택 중심으로부터의 거리"라면, layered는
      // "그래프 전체에서 계산된 논리적 깊이"를 보여주는 별도 분석 뷰다.
      const nodeCoords = computeLayeredLayout(nodes);
      formattedNodes = nodes.map((n) => {
        const coord = nodeCoords[n.id] || { x: 0, y: 0 };
        return {
          ...n,
          x: coord.x,
          y: coord.y,
          fx: coord.x,
          fy: coord.y,
        };
      });
    }

    const formattedLinks = edges.map((e, idx) => ({
      id: `e${idx}`,
      source: e.source,
      target: e.target,
    }));

    graph.graphData({ nodes: formattedNodes, links: formattedLinks });
    graphNodesRef.current = formattedNodes;

    // v0.7.144+: all-scope 제거 — vault별 최상단 y 계산 불필요.

    // v0.7.139+: 데이터 변경 시점에 highlight ref를 미리 계산. hover 중에는
    // setHoveredNode → ref 동기화만 하고 effect는 재실행되지 않아, 캔버스
    // pan/zoom 위치와 클릭 상태가 보존된다.
    recomputeHighlights(hoveredNodeRef.current, externalHighlightNodeId, edges);

    // force layout에서만 드래그를 열어 노드 위치를 직접 조정할 수 있게 한다.
    // force-graph native drag가 fx/fy와 simulation reheat를 직접 처리한다.
    graph.enableNodeDrag(layoutMode === "force");

    // 이벤트 리스너 바인딩
    graph
      .onNodeClick((node: any) => {
        if (node?.id) queueResolvedNodeClick(node.id);
      })
      .onBackgroundClick(() => {
        clickHandlersRef.current.onBackgroundClick?.();
      })
      .onNodeHover((node: any) => {
        if (node) {
          onNodeInspect?.(node as GraphNode);
          setHoveredNode(node);
        } else {
          setHoveredNode(null);
        }
      })
      .onNodeDragEnd((node: any) => {
        if (layoutMode !== "force") return;
        if (!Number.isFinite(node.x) || !Number.isFinite(node.y)) return;
        node.fx = node.x;
        node.fy = node.y;
        onPositionsChange?.({
          [node.id]: {
            x: node.x / GRAPH_SCALE_MULTIPLIER,
            y: node.y / GRAPH_SCALE_MULTIPLIER,
          },
        });
      })
      // v0.7.139+: zoom 변경 시 배율 표시 갱신 (pinch / ctrl+wheel / programmatic).
      .onZoom(({ k }: { k: number }) => {
        setZoomLevel(k);
      });

    const queueResolvedNodeClick = (nodeId: string) => {
      const pending = pendingClickRef.current;
      const now = window.performance?.now?.() ?? Date.now();
      if (pending && pending.nodeId === nodeId) {
        // force-graph's native onNodeClick and our direct mouseup detector can both fire for
        // the same physical click. Ignore near-simultaneous duplicates; treat later repeats as double-click.
        if (now - pending.startedAt < 80) return;
        window.clearTimeout(pending.timeoutId);
        pendingClickRef.current = null;
        clickHandlersRef.current.onNodeDoubleClick?.(nodeId);
        return;
      }

      if (pending) {
        window.clearTimeout(pending.timeoutId);
        pendingClickRef.current = null;
      }

      // Single click must give immediate visual feedback in GraphPage's detail panel.
      // We only keep a short pending window to upgrade a second same-node click to navigation.
      clickHandlersRef.current.onNodeClick?.(nodeId);
      pendingClickRef.current = {
        nodeId,
        startedAt: now,
        timeoutId: window.setTimeout(() => {
          if (pendingClickRef.current?.nodeId !== nodeId) return;
          pendingClickRef.current = null;
        }, DOUBLE_CLICK_DELAY_MS),
      };
    };

    const getScreenPoint = (clientX: number, clientY: number) => {
      const rect = containerRef.current?.getBoundingClientRect();
      if (!rect) return null;
      const screenX = clientX - rect.left;
      const screenY = clientY - rect.top;
      if (typeof graph.screen2canvasCoords === "function") {
        return graph.screen2canvasCoords(screenX, screenY);
      }
      return graph.screen2GraphCoords(screenX, screenY);
    };

    const runDirectHitDetection = (clientX: number, clientY: number, pointerType: "mouse" | "touch") => {
      const start = pressStartRef.current;
      if (!isStationaryClickGesture(start?.point ?? null, { x: clientX, y: clientY }, pointerType)) {
        pressStartRef.current = null;
        return;
      }

      const canvasPoint = getScreenPoint(clientX, clientY);
      if (!canvasPoint) {
        pressStartRef.current = null;
        return;
      }

      const currentScale = graph?.zoom() ?? 1;
      const liveNodes = Array.isArray(graph.graphData?.().nodes)
        ? graph.graphData().nodes
        : graphNodesRef.current;
      const hitNode = findClosestNodeHit(
        liveNodes,
        canvasPoint,
        isDense ? "dense" : "normal",
        DIRECT_CLICK_PADDING_PX,
        currentScale,
        pointerType === "touch" ? DIRECT_TOUCH_HIT_RADIUS_PX : DIRECT_MOUSE_HIT_RADIUS_PX
      );

      pressStartRef.current = null;
      if (!hitNode) {
        clickHandlersRef.current.onBackgroundClick?.();
        return;
      }
      queueResolvedNodeClick(hitNode.id);
    };

    const handleMouseDown = (ev: MouseEvent) => {
      pressStartRef.current = {
        point: { x: ev.clientX, y: ev.clientY },
        pointerType: "mouse",
      };
    };

    const handleTouchStart = (ev: TouchEvent) => {
      if (ev.touches.length !== 1) {
        pressStartRef.current = null;
        return;
      }
      const touch = ev.touches[0];
      pressStartRef.current = {
        point: { x: touch.clientX, y: touch.clientY },
        pointerType: "touch",
      };
    };

    const handleMouseUp = (ev: MouseEvent) => {
      runDirectHitDetection(ev.clientX, ev.clientY, "mouse");
    };

    const handleTouchEnd = (ev: TouchEvent) => {
      if (ev.changedTouches.length !== 1) {
        pressStartRef.current = null;
        return;
      }
      const touch = ev.changedTouches[0];
      runDirectHitDetection(touch.clientX, touch.clientY, "touch");
    };

    const handleTouchCancel = () => {
      pressStartRef.current = null;
    };

    const container = containerRef.current;
    container?.addEventListener("mousedown", handleMouseDown, { passive: true });
    container?.addEventListener("touchstart", handleTouchStart, { passive: true });
    container?.addEventListener("mouseup", handleMouseUp, { passive: true });
    container?.addEventListener("touchend", handleTouchEnd, { passive: true });
    container?.addEventListener("touchcancel", handleTouchCancel, { passive: true });

    // 엣지 스타일 정의
    const crossVaultEdgeIds = new Set<string>();
    if (isDense) {
      edges.forEach((edge, idx) => {
        const srcVault = String(edge.source).split(":", 1)[0];
        const tgtVault = String(edge.target).split(":", 1)[0];
        if (srcVault !== tgtVault) {
          crossVaultEdgeIds.add(`e${idx}`);
        }
      });
    }

    graph
      .linkColor((link: any) => {
        if (link.broken_dependency) {
          return "#ef4444"; // red-500
        }
        const isHighlighted = highlightLinksRef.current.has(link.id);
        const relType = link.relation_type;
        const hasFocusActive = externalHighlightNodeId || hoveredNodeRef.current || externalHighlightType;
        
        if (relType && RELATION_COLORS[relType]) {
          const baseColor = RELATION_COLORS[relType];
          if (hasFocusActive) {
            return isHighlighted ? baseColor : `${baseColor}22`; // faded
          }
          return isHighlighted ? baseColor : `${baseColor}99`; // normal
        }
        
        if (isHighlighted) return resolvedEdgeHighlightRef.current;
        return hasFocusActive ? `${resolvedEdgeColorRef.current}16` : resolvedEdgeColorRef.current;
      })
      .linkWidth((link: any) => {
        const isHighlighted = highlightLinksRef.current.has(link.id) || link.broken_dependency;
        const isSemantic = !!link.relation_type;
        const baseWidth = isSemantic ? 1.5 : 1.05;
        return isHighlighted ? baseWidth + 1.15 : baseWidth;
      })
      .linkLineDash((link: any) => {
        const relType = link.relation_type;
        if (relType && RELATION_DASHES[relType]) {
          return RELATION_DASHES[relType];
        }
        return [];
      })
      .linkDirectionalArrowLength((link: any) => {
        const hasArrow = link.relation_type && ['uses', 'depends_on', 'implements', 'implemented_by'].includes(link.relation_type);
        return hasArrow ? 5.5 : 0;
      })
      .linkDirectionalArrowRelPos(1.0)
      .linkDirectionalArrowColor((link: any) => {
        if (link.broken_dependency) {
          return "#ef4444";
        }
        const isHighlighted = highlightLinksRef.current.has(link.id);
        const relType = link.relation_type;
        if (relType && RELATION_COLORS[relType]) {
          const baseColor = RELATION_COLORS[relType];
          const hasFocusActive = externalHighlightNodeId || hoveredNodeRef.current || externalHighlightType;
          if (hasFocusActive) {
            return isHighlighted ? baseColor : `${baseColor}22`;
          }
          return isHighlighted ? baseColor : `${baseColor}99`;
        }
        return resolvedEdgeHighlightRef.current;
      })
      .linkCurvature(0.035)
      // Remove animated particles: they made selected paths feel busy/tacky rather than clean.
      .linkDirectionalParticles(0)
      .linkDirectionalParticleWidth(0)
      .linkDirectionalParticleSpeed(0.016)
      .nodeLabel((node: any) => {
        const typeLabelStr = typeLabel(node.type);
        const typeBadge = typeLabelStr
          ? `<span style="font-size: 10px; padding: 2px 6px; border-radius: 4px; background: rgba(255, 255, 255, 0.15); margin-left: 6px;">${typeLabelStr}</span>`
          : "";
        return `
          <div style="
            padding: 6px 10px; 
            background: rgba(15, 23, 42, 0.95); 
            border: 1px solid rgba(255, 255, 255, 0.12); 
            border-radius: 4px; 
            color: #fff; 
            font-size: 12px;
            pointer-events: none;
            font-family: system-ui, -apple-system, BlinkMacSystemFont, sans-serif;
          ">
            <strong>${node.title || node.id}</strong>${typeBadge}
            <div style="font-size: 10px; color: #94a3b8; margin-top: 2px;">${node.id}</div>
          </div>
        `;
      })
      .linkLabel((link: any) => {
        if (!link.relation_type) return "";
        const relLabel = RELATION_LABELS[link.relation_type] || link.relation_type;
        
        const getTitle = (nodeOrId: any) => {
          if (typeof nodeOrId === "object" && nodeOrId !== null) {
            return nodeOrId.title || nodeOrId.id;
          }
          const found = graphNodesRef.current.find(n => n.id === nodeOrId);
          return found ? (found.title || found.id) : nodeOrId;
        };
        const sourceTitle = getTitle(link.source);
        const targetTitle = getTitle(link.target);
        
        const evidenceList = Array.isArray(link.evidence)
          ? link.evidence
          : (link.evidence ? [link.evidence] : []);
        const evidenceHtml = evidenceList.length > 0
          ? `<div style="margin-top: 4px; font-size: 11px; opacity: 0.85;"><strong>근거:</strong> ${evidenceList.join(', ')}</div>`
          : "";
        const reasonHtml = link.reason
          ? `<div style="margin-top: 4px; font-size: 11px; opacity: 0.85;"><strong>이유:</strong> ${link.reason}</div>`
          : "";
          
        return `
          <div style="
            padding: 8px 12px; 
            background: rgba(15, 23, 42, 0.95); 
            border: 1px solid rgba(255, 255, 255, 0.15); 
            border-radius: 6px; 
            color: #fff; 
            font-size: 12px; 
            max-width: 280px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25);
            pointer-events: none;
            font-family: system-ui, -apple-system, BlinkMacSystemFont, sans-serif;
          ">
            <div style="font-weight: 600; color: #818cf8; margin-bottom: 4px;">
              ${relLabel}
            </div>
            <div style="display: flex; align-items: center; gap: 4px; margin-bottom: 4px;">
              <span style="color: #cbd5e1; font-weight: 500;">${sourceTitle}</span>
              <span style="color: #64748b;">➔</span>
              <span style="color: #cbd5e1; font-weight: 500;">${targetTitle}</span>
            </div>
            ${evidenceHtml}
            ${reasonHtml}
          </div>
        `;
      });

    // 노드 스타일 커스텀 렌더링 (Obsidian 퀄리티 재현)
    // v0.7.144+: all-scope 모드 제거 — vault ring (resolveVaultColor 사용) 코드 삭제.
    // vault 외곽선 ring은 single vault에서 모든 노드가 같은 vault이라 무의미.
    graph.nodeCanvasObject((node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
      if (!node || node.x === undefined || node.y === undefined) return;
      const scale = globalScale || 1;
      const size = nodeSize(node.weight, isDense ? "dense" : "normal", node.importance, nodes.length);
      const focusDepth =
        typeof node.__focusDepth === "number"
          ? node.__focusDepth
          : focusDepthMap.get(node.id);
      const depthMultiplier =
        typeof focusDepth === "number"
          ? Math.max(0.68, 1 - focusDepth * 0.12)
          : (focusDepthMap.size > 0 ? 0.88 : 1);
      const renderedSize = size * depthMultiplier;
      // v0.7.139+: ref로 최신 hover state를 매 paint call에서 읽는다 (effect 재실행 없음).
      const currentHover = hoveredNodeRef.current;
      const isHovered = currentHover && currentHover.id === node.id;
      const isHighlighted = highlightNodesRef.current.has(node.id);
      const isPersistent = persistentHighlightNodeId === node.id;
      const isFocused =
        isHovered || isPersistent || externalHighlightNodeId === node.id;
      const fillOpacity = nodeOpacity(node.freshness);

      // 1. 노드 본체 (원) — zoom 보정 없이 픽셀 그대로 그린다.
      // force-graph의 `nodeVal/nodeRelSize` 자동 보정에 의존하지 않으므로
      // baseSize를 zoom-out에서도 가독성 있게 키웠다 (옛 공식 대비 1.7~2배).
      ctx.beginPath();
      ctx.arc(node.x, node.y, renderedSize, 0, 2 * Math.PI, false);

      // 흐릿한 비포커스 처리
      const hasFocusActive = externalHighlightNodeId || currentHover || externalHighlightType;
      const baseAlpha = hasFocusActive && !isFocused && !isHighlighted
        ? fillOpacity * 0.28
        : fillOpacity;
      const depthAlpha = typeof focusDepth === "number"
        ? Math.max(0.28, 1 - focusDepth * 0.18)
        : (focusDepthMap.size > 0 ? 0.72 : 1);
      ctx.fillStyle = hexToRgba(nodeColor(node.type), baseAlpha);
      ctx.globalAlpha = depthAlpha;
      ctx.fill();
      ctx.globalAlpha = 1;

      // 테두리 선 굵기 및 스타일을 centrality에 매핑
      let borderThickness = isFocused ? 2 : 0.8;
      if (node.centrality !== undefined && node.centrality !== null) {
        const centralityFactor = Math.min(node.centrality, 0.2) / 0.2;
        borderThickness += centralityFactor * 2.5;
      }
      ctx.lineWidth = borderThickness / scale;

      let strokeStyle = resolvedNodeOutlineRef.current;
      if (isFocused) {
        strokeStyle = resolvedEdgeHighlightRef.current;
      } else if (isHighlighted) {
        strokeStyle = "rgba(255, 255, 255, 0.72)";
      } else if (node.centrality !== undefined && node.centrality !== null && node.centrality > 0.01) {
        const alpha = Math.min(0.2 + (node.centrality * 10), 0.95);
        strokeStyle = `rgba(255, 255, 255, ${alpha})`;
      }
      ctx.strokeStyle = strokeStyle;
      ctx.stroke();

      // 이중 링 효과 (focused)
      if (isFocused) {
        ctx.beginPath();
        ctx.arc(node.x, node.y, renderedSize + 2.5 / scale, 0, 2 * Math.PI, false);
        ctx.strokeStyle = resolvedEdgeHighlightRef.current;
        ctx.lineWidth = 0.8 / scale;
        ctx.stroke();
      }

      // 붉은색 경고 Halo 효과 (Broken Dependency Alert)
      if (node.broken_dependency) {
        ctx.beginPath();
        ctx.arc(node.x, node.y, renderedSize + 4.5 / scale, 0, 2 * Math.PI, false);
        ctx.strokeStyle = "rgba(239, 68, 68, 0.75)";
        ctx.lineWidth = 2.5 / scale;
        ctx.stroke();
      }

      // 2. 텍스트 라벨 그리기 (LOD - Level of Detail)
      // dense(all-vault)에서는 라벨을 훨씬 보수적으로 노출해 "떡처럼 붙는" 현상을 줄인다.
      // current scope도 무조건 상시 노출 대신 zoom/중요도(weight) 기준을 둬 시야를 정리한다.
      const showLabel = shouldShowLabel(
        node,
        scale,
        isDense,
        isFocused,
        isHighlighted
      );
      if (showLabel) {
        const label = node.title || node.slug || node.id;
        const fontSize = NODE_LABEL_BASE_SIZE / scale;
        ctx.save();
        ctx.font = `${isFocused ? "500" : "400"} ${fontSize}px ${GRAPH_LABEL_FONT}`;
        ctx.textAlign = "center";
        ctx.textBaseline = "top";

        // v0.7.146 (B): zoom-out에서 라벨이 노드 안에 박혀서 깨짐 → 노드 옆으로 오프셋.
        // zoom-in (scale > 1.5) 이하면 라벨을 노드 오른쪽으로 띄움.
        const labelOffsetX = scale < 1.5 ? (renderedSize + 8) / scale : 0;
        const labelX = node.x + labelOffsetX;
        const labelY = node.y + renderedSize + 3.8 / scale;

        // No text outline: small canvas labels became fat/blurry with halo strokes.
        // Rely on theme-resolved high-contrast label color instead.
        ctx.fillStyle = isFocused
          ? resolvedEdgeHighlightRef.current
          : resolvedLabelColorRef.current;
        ctx.fillText(label, labelX, labelY);
        ctx.restore();
      }
      // v0.7.144+: vault 라벨 코드 제거 (all-scope 모드 들어냄)
    })
      .nodePointerAreaPaint((node: any, color: string, ctx: CanvasRenderingContext2D, globalScale: number) => {
        if (!node || node.x === undefined || node.y === undefined) return;
        const scale = globalScale || 1;
        const focusDepth = focusDepthMap.get(node.id);
        const depthMultiplier =
          typeof focusDepth === "number"
            ? Math.max(0.68, 1 - focusDepth * 0.12)
            : (focusDepthMap.size > 0 ? 0.88 : 1);
        const hitRadius = Math.max(
          nodeSize(node.weight, isDense ? "dense" : "normal") * depthMultiplier * DIRECT_HIT_NODE_RADIUS_MULTIPLIER,
          DIRECT_MOUSE_HIT_RADIUS_PX / scale
        );
        ctx.fillStyle = color;
        ctx.beginPath();
        ctx.arc(node.x, node.y, hitRadius, 0, 2 * Math.PI, false);
        ctx.fill();
      });

    // v0.7.144+: vault ring도 제거 — single vault에서는 모든 노드가 같은 vault이라 무의미.

    // 줌 아웃 시점에만 단순 텍스트로 폴더 라벨 투사 (LOD HUD)
    graph.onRenderFramePre((ctx: CanvasRenderingContext2D, globalScale: number) => {
      const scale = globalScale || 1;
      
      // 1. Domain View일 때 커뮤니티별 반투명 구획(Onion bound) 그리기
      if (layoutMode === "domain") {
        const groupStats: Record<number, { xSum: number; ySum: number; count: number; xMin: number; xMax: number; yMin: number; yMax: number }> = {};
        const groupNodes: Record<number, any[]> = {};
        const currentNodes = graph.graphData().nodes;
        
        currentNodes.forEach((node: any) => {
          const c = node.community ?? 0;
          if (!groupStats[c]) {
            groupStats[c] = { xSum: 0, ySum: 0, count: 0, xMin: 99999, xMax: -99999, yMin: 99999, yMax: -99999 };
            groupNodes[c] = [];
          }
          groupStats[c].xSum += node.x;
          groupStats[c].ySum += node.y;
          groupStats[c].count += 1;
          groupNodes[c].push(node);
          if (node.x < groupStats[c].xMin) groupStats[c].xMin = node.x;
          if (node.x > groupStats[c].xMax) groupStats[c].xMax = node.x;
          if (node.y < groupStats[c].yMin) groupStats[c].yMin = node.y;
          if (node.y > groupStats[c].yMax) groupStats[c].yMax = node.y;
        });

        ctx.save();
        const COMMUNITY_COLORS = ["#3b82f6", "#ef4444", "#a855f7", "#10b981", "#f59e0b", "#ec4899", "#14b8a6", "#6366f1", "#8b5cf6", "#f97316"];
        for (const cidStr in groupStats) {
          const cid = Number(cidStr);
          const stat = groupStats[cid];
          if (stat.count === 0) continue;
          const cx = stat.xSum / stat.count;
          const cy = stat.ySum / stat.count;
          
          const dx = stat.xMax - stat.xMin;
          const dy = stat.yMax - stat.yMin;
          const radius = Math.max(38, Math.hypot(dx, dy) / 2 + 35);
          
          ctx.beginPath();
          ctx.arc(cx, cy, radius, 0, 2 * Math.PI);
          const color = COMMUNITY_COLORS[cid % COMMUNITY_COLORS.length];
          
          // LOD 줌 연동: 줌 레벨에 따라 채우기 및 테두리 투명도 보정
          const bgOpacity = Math.max(0.01, Math.min(0.06, (0.85 - scale) * 0.08));
          const borderOpacity = Math.max(0.05, Math.min(0.24, (0.85 - scale) * 0.3));
          
          ctx.fillStyle = hexToRgba(color, bgOpacity);
          ctx.fill();
          ctx.lineWidth = 0.8 / scale;
          ctx.strokeStyle = hexToRgba(color, borderOpacity);
          ctx.stroke();

          // LOD 줌 연동: 축소 수준이 높을 때(scale < 0.85)만 대표 도메인 레이블이 크고 선명하게 투사되도록 스타일 제어
          if (scale < 0.85) {
            // 자동 의미론적 레이블 계산
            const cNodes = groupNodes[cid] || [];
            let labelSuffix = "";
            if (cNodes.length > 0) {
              // 최상위 중요 노드
              let topNode = cNodes[0];
              for (const n of cNodes) {
                if ((n.importance ?? 0) > (topNode.importance ?? 0)) {
                  topNode = n;
                }
              }
              
              // 제목 기반 키워드 빈도 추출
              const stopwords = new Set([
                "and", "the", "with", "for", "from", "main", "core", "impl", "test", "helper", "util", "utils", "config",
                "이", "그", "저", "및", "등", "을", "를", "의", "에", "과", "와", "한", "로", "으로", "에서"
              ]);
              const wordCounts: Record<string, number> = {};
              cNodes.forEach(n => {
                const wList = (n.title || "").toLowerCase().match(/[a-zA-Z가-힣0-9]{2,20}/g) || [];
                wList.forEach((w: string) => {
                  if (!stopwords.has(w)) {
                    wordCounts[w] = (wordCounts[w] || 0) + 1;
                  }
                });
              });
              const sortedWords = Object.entries(wordCounts)
                .sort((a, b) => b[1] - a[1])
                .map(entry => entry[0]);
              
              if (topNode) {
                const topWords = (topNode.title || "").match(/[a-zA-Z가-힣0-9]{2,20}/g) || [];
                const mainTopWord = topWords.find((w: string) => !stopwords.has(w.toLowerCase())) || topNode.title;
                const secondWord = sortedWords.find((w: string) => w.toLowerCase() !== mainTopWord.toLowerCase());
                const cap = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);
                if (secondWord) {
                  labelSuffix = ` (${cap(mainTopWord)} & ${cap(secondWord)})`;
                } else {
                  labelSuffix = ` (${cap(mainTopWord)})`;
                }
              }
            }

            // 줌 아웃이 많이 될수록 레이블을 더 선명하고 돋보이게 처리 (LOD HUD 디자인 시스템 최적화)
            const textOpacity = Math.min(0.75, (0.85 - scale) * 1.15);
            const fontSize = Math.max(10, Math.min(14, 14 - scale * 4)); // 줌아웃 수준에 맞춤형
            
            ctx.save();
            ctx.font = `600 ${fontSize / scale}px ${HUD_LABEL_FONT}`;
            ctx.fillStyle = color;
            ctx.globalAlpha = textOpacity;
            ctx.textAlign = "center";
            
            // 가시성을 위한 텍스트의 미세한 그림자 효과 추가 (프리미엄 디테일)
            ctx.shadowColor = "rgba(0, 0, 0, 0.4)";
            ctx.shadowBlur = 4 / scale;
            
            ctx.fillText(`Community ${cid}${labelSuffix}`, cx, cy - radius - 8 / scale);
            ctx.restore();
          }
        }
        ctx.restore();
        return;
      }

      // 2. Timeline View일 때 가이드 라인 그리기
      if (layoutMode === "timeline" && nodes.length > 0) {
        ctx.save();
        ctx.strokeStyle = "rgba(148, 163, 184, 0.12)";
        ctx.lineWidth = 0.8 / scale;
        ctx.font = `600 ${10 / scale}px ${HUD_LABEL_FONT}`;
        ctx.fillStyle = "rgba(148, 163, 184, 0.4)";
        
        const typeYOffsets: Record<string, number> = {
          concept: 150,
          project: 75,
          rule: 0,
          journal: -75,
          issue: -150,
        };
        
        for (const [typeName, yVal] of Object.entries(typeYOffsets)) {
          ctx.beginPath();
          ctx.moveTo(-500, yVal);
          ctx.lineTo(500, yVal);
          ctx.stroke();
          
          ctx.textAlign = "left";
          ctx.fillText(typeLabel(typeName) || typeName, -485, yVal - 8 / scale);
        }

        const xStart = -450;
        const xEnd = 450;
        
        const parseDate = (dateStr: string | undefined): number => {
          if (!dateStr) return 0;
          try {
            const clean = dateStr.trim().substring(0, 10);
            return Date.parse(clean) || 0;
          } catch {
            return 0;
          }
        };

        const nowTime = Date.now();
        const times = nodes.map(n => {
          return parseDate(n.created) || parseDate(n.updated) || nowTime;
        });
        const minTime = Math.min(...times);
        const maxTime = Math.max(...times);
        const timeDiff = maxTime - minTime || 1;

        // Adaptive Grid Scale 결정
        let gridPoints: { x: number; label: string }[] = [];
        
        if (timeDiff <= 2 * 60 * 60 * 1000) {
          // 2시간 이내: 15분 단위
          const step = 15 * 60 * 1000;
          const start = Math.floor(minTime / step) * step;
          for (let tVal = start; tVal <= maxTime + step; tVal += step) {
            const ratio = (tVal - minTime) / timeDiff;
            const x = xStart + ratio * (xEnd - xStart);
            if (x >= xStart - 10 && x <= xEnd + 10) {
              const d = new Date(tVal);
              const label = `${d.getHours()}:${String(d.getMinutes()).padStart(2, '0')}`;
              gridPoints.push({ x, label });
            }
          }
        } else if (timeDiff <= 24 * 60 * 60 * 1000) {
          // 24시간 이내: 2시간 단위
          const step = 2 * 60 * 60 * 1000;
          const start = Math.floor(minTime / step) * step;
          for (let tVal = start; tVal <= maxTime + step; tVal += step) {
            const ratio = (tVal - minTime) / timeDiff;
            const x = xStart + ratio * (xEnd - xStart);
            if (x >= xStart - 10 && x <= xEnd + 10) {
              const d = new Date(tVal);
              const label = `${d.getHours()}:00`;
              gridPoints.push({ x, label });
            }
          }
        } else if (timeDiff <= 7 * 24 * 60 * 60 * 1000) {
          // 7일 이내: 1일 단위
          const step = 24 * 60 * 60 * 1000;
          const start = Math.floor(minTime / step) * step;
          for (let tVal = start; tVal <= maxTime + step; tVal += step) {
            const ratio = (tVal - minTime) / timeDiff;
            const x = xStart + ratio * (xEnd - xStart);
            if (x >= xStart - 10 && x <= xEnd + 10) {
              const label = new Date(tVal).toISOString().split("T")[0].substring(5); // MM-DD
              gridPoints.push({ x, label });
            }
          }
        } else {
          // 일반적인 경우: 5개 등분
          for (let i = 0; i <= 4; i++) {
            const ratio = i / 4;
            const x = xStart + ratio * (xEnd - xStart);
            const tVal = minTime + ratio * timeDiff;
            const dateStr = new Date(tVal).toISOString().split("T")[0];
            gridPoints.push({ x, label: dateStr });
          }
        }

        ctx.strokeStyle = "rgba(148, 163, 184, 0.06)";
        gridPoints.forEach(({ x, label }) => {
          ctx.beginPath();
          ctx.moveTo(x, -250);
          ctx.lineTo(x, 200);
          ctx.stroke();
          
          ctx.textAlign = "center";
          ctx.fillText(label, x, 215 / scale);
        });
        ctx.restore();
        return;
      }

      if (layoutMode === "layered" && nodes.length > 0) {
        const currentNodes = graph.graphData().nodes as any[];
        const layerSet = new Set<number>();
        currentNodes.forEach((node: any) => {
          if (typeof node.layer === "number" && Number.isFinite(node.layer)) {
            layerSet.add(Math.max(0, Math.round(node.layer)));
          }
        });
        const layers = [...layerSet].sort((a, b) => a - b);
        if (layers.length === 0) return;

        ctx.save();
        ctx.strokeStyle = "rgba(148, 163, 184, 0.08)";
        ctx.lineWidth = 0.9 / scale;
        ctx.font = `600 ${10 / scale}px ${HUD_LABEL_FONT}`;
        ctx.fillStyle = "rgba(148, 163, 184, 0.5)";
        ctx.textAlign = "center";

        const xStart = -430;
        const xEnd = 430;
        const span = Math.max(1, layers[layers.length - 1] - layers[0]);

        layers.forEach((layer) => {
          const ratio = (layer - layers[0]) / span;
          const x = xStart + ratio * (xEnd - xStart);
          ctx.beginPath();
          ctx.moveTo(x, -260);
          ctx.lineTo(x, 260);
          ctx.stroke();
          ctx.fillText(`Layer ${layer}`, x, 276 / scale);
        });

        ctx.restore();
        return;
      }

      // 3. Force-directed 모드일 때 Centroid LOD HUD 라벨 연산
      const labelOpacity = Math.max(0, Math.min(1, (0.75 - scale) / 0.25));
      if (labelOpacity <= 0.05) return;

      const groupCoords: Record<string, { xSum: number; ySum: number; count: number; label: string }> = {};
      const currentNodes = graph.graphData().nodes;
      
      for (const node of currentNodes) {
        if (typeof node.x !== "number" || typeof node.y !== "number" || !node.folder_group) continue;
        const gid = node.folder_group;
        if (!groupCoords[gid]) {
          groupCoords[gid] = { xSum: 0, ySum: 0, count: 0, label: node.folder_label || gid };
        }
        groupCoords[gid].xSum += node.x;
        groupCoords[gid].ySum += node.y;
        groupCoords[gid].count += 1;
      }

      ctx.save();
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";

      for (const gid in groupCoords) {
        const data = groupCoords[gid];
        if (data.count < 5) continue;

        const cx = data.xSum / data.count;
        const cy = data.ySum / data.count;
        const drawY = cy - 24 / scale;

        const labelText = data.label;
        const isContent = gid === "content";
        const targetGroupAlpha = isContent ? 0.24 : 0.16;
        const textOpacity = labelOpacity * targetGroupAlpha;
        
        const fontSize = Math.max(
          isContent ? 12 : 14, 
          (isContent ? 13 : HUD_LABEL_BASE_SIZE) / scale
        );

        ctx.font = `600 ${fontSize}px ${HUD_LABEL_FONT}`;

        ctx.fillStyle = resolvedBgColorRef.current;
        ctx.globalAlpha = textOpacity * 0.75;
        for (let dx = -1.5; dx <= 1.5; dx += 1.5) {
          for (let dy = -1.5; dy <= 1.5; dy += 1.5) {
            if (dx !== 0 || dy !== 0) {
              ctx.fillText(labelText, cx + dx * (0.8 / scale), drawY + dy * (0.8 / scale));
            }
          }
        }

        ctx.fillStyle = resolvedLabelColorRef.current;
        ctx.globalAlpha = textOpacity;
        ctx.fillText(labelText, cx, drawY);
      }
      ctx.restore();
    });

    // v0.7.139+: fitView는 scope 전환(all ↔ current) 또는 첫 데이터 로드 시에만.
    // 검색/필터로 nodes가 바뀌어도 사용자의 pan/zoom 위치를 보존한다.
    // v0.7.150+: container 크기가 아직 계산되지 않았다면(width/height가 0일 때) 줌핏이 어긋나므로
    // 크기가 정상 확보될 때까지 대기 후 zoomToFit을 정확한 시점에 단 1회 실행합니다.
    const scopeChanged = prevIsDenseRef.current !== isDense;
    const firstLoad = prevNodeCountRef.current === 0 && nodes.length > 0;
    if (scopeChanged || firstLoad) {
      if (nodes.length > 0) {
        const tryFit = (retryCount = 0) => {
          const g = graphInstanceRef.current;
          if (!g) return;
          const w = g.width();
          const h = g.height();
          if (w > 0 && h > 0) {
            g.zoomToFit(300, 96);
          } else if (retryCount < 10) {
            // 크기 대기 재시도 (최대 10회, 1초)
            setTimeout(() => tryFit(retryCount + 1), 100);
          }
        };
        setTimeout(() => tryFit(), 50);
      }
    }
    prevIsDenseRef.current = isDense;
    prevNodeCountRef.current = nodes.length;

    return () => {
      container?.removeEventListener("mousedown", handleMouseDown);
      container?.removeEventListener("touchstart", handleTouchStart);
      container?.removeEventListener("mouseup", handleMouseUp);
      container?.removeEventListener("touchend", handleTouchEnd);
      container?.removeEventListener("touchcancel", handleTouchCancel);
      if (graphInstanceRef.current) {
        graphInstanceRef.current.onRenderFramePre(null);
      }
    };
  }, [
    nodes,
    edges,
    isDense,
    externalHighlightNodeId,
    persistentHighlightNodeId,
    externalHighlightType,
    onNodeInspect,
    onPositionsChange,
    layoutMode,
  ]);

  const fitGraph = () => {
    if (graphInstanceRef.current) {
      // v0.7.150+: '맞춤' 기능은 노드들의 기하학적 배치(fx/fy)를 뭉개지 않고 
      // 단순히 카메라 줌/팬을 전체 노드 영역에 맞추도록 개선합니다.
      // D3 시뮬레이션을 재가열하여 배치 데이터를 폭발시키거나 흩뿌리는 대신,
      // 원래 위치를 유지한 상태에서 zoomToFit만 즉시 실행합니다.
      graphInstanceRef.current.zoomToFit(400, 96);
    }
  };

  // v0.7.139+: programmatic zoom (factor 1.6 / 0.625). force-graph의 zoom(k)는 중심을
  // 그대로 두고 배율만 바꿔 pan/zoom UX와 일관됨.
  const ZOOM_STEP = 1.6;
  const zoomIn = () => {
    const g = graphInstanceRef.current;
    if (!g) return;
    g.zoom((g.zoom() ?? 1) * ZOOM_STEP, 400);
  };
  const zoomOut = () => {
    const g = graphInstanceRef.current;
    if (!g) return;
    g.zoom((g.zoom() ?? 1) / ZOOM_STEP, 400);
  };
  // 배율 표시 — 1.0 = 100%. 줌이 1 근처일 때만 "100%"로 단순화, 그 외엔 백분율로 표시.
  const zoomPercent = Math.round(zoomLevel * 100);
  const zoomLabel = `${zoomPercent}%`;

  const isMinimap = variant === "minimap";

  return (
    <div
      className={`graph-canvas-container${isMinimap ? " is-minimap" : ""}`}
    >
      {isJSDOM ? (
        <div data-testid="graph-canvas-mock" style={{ color: "var(--graph-text)", padding: 20 }}>
          [JSDOM Test Mock Graph Canvas]
        </div>
      ) : (
        // v0.7.139+: touchAction:none — 모바일에서 캔버스 pan이 pull-to-refresh로
        // 새지 않도록 모든 native touch gesture를 우리가 처리.
        <div
          ref={containerRef}
          style={{ width: "100%", height: "100%", touchAction: "none" }}
        />
      )}

      {/* 툴바 컨트롤 레이어 */}
      <div className="graph-canvas-toolbar">
        {onFullscreen && (
          <button
            type="button"
            onClick={onFullscreen}
            className="graph-canvas-btn"
            aria-label="그래프 전체보기"
            title="팝업으로 크게 보기"
          >
            {isMinimap ? "전체" : "전체보기"}
          </button>
        )}
        <button
          type="button"
          onClick={fitGraph}
          className="graph-canvas-btn"
          aria-label="그래프 화면 맞춤"
          title="배치를 초기화하고 모든 노드가 화면에 들어오도록 뷰를 맞춥니다"
        >
          맞춤
        </button>
        {/* v0.7.139+: 줌 컨트롤 순서: + / 배율% / − (미니맵 포함 항상 표시) */}
        <button
          type="button"
          onClick={zoomIn}
          className="graph-canvas-btn"
          aria-label="그래프 확대"
          title="확대 (단축키: +)"
        >
          +
        </button>
        <span
          aria-live="polite"
          className="graph-canvas-zoom-label"
          title={`현재 줌 배율 — 더블클릭으로 100%로 리셋`}
          onDoubleClick={() => graphInstanceRef.current?.zoomTo(1, 200)}
        >
          {zoomLabel}
        </span>
        <button
          type="button"
          onClick={zoomOut}
          className="graph-canvas-btn"
          aria-label="그래프 축소"
          title="축소 (단축키: −)"
        >
          −
        </button>

      </div>
    </div>
  );
}
