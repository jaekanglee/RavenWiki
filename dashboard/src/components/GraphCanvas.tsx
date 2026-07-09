import { useEffect, useMemo, useRef, useState } from "react";
import ForceGraph from "force-graph";
import type { GraphNode, GraphEdge } from "../types";

interface Props {
  nodes: GraphNode[];
  edges: GraphEdge[];
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
}

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
export function nodeSize(weight: number | undefined, density: "normal" | "dense" = "normal"): number {
  const w = Math.max(weight ?? 1, 1);
  const multiplier = density === "dense" ? 4 : 6;
  const base = density === "dense" ? 7 : 8;
  return base + Math.log2(1 + w) * multiplier;
}

// Sidebar와 GraphPage에서 사용하는 타입 라벨 매핑 및 typeLabel 헬퍼 복원 (v0.7.132+)
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

export function typeLabel(type: string | undefined): string {
  if (!type) return "";
  return TYPE_LABELS[type] ?? "";
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
    const visualRadius = nodeSize(node.weight, density) * DIRECT_HIT_NODE_RADIUS_MULTIPLIER;
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

const graphButtonStyle = {
  border: "1px solid var(--graph-border)",
  background: "var(--graph-surface)",
  color: "var(--graph-text)",
  borderRadius: 999,
  padding: "6px 10px",
  fontSize: 12,
  fontWeight: 600,
  cursor: "pointer",
  backdropFilter: "blur(8px)",
} as const;

const GRAPH_LABEL_FONT = "system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif";
const HUD_LABEL_FONT = GRAPH_LABEL_FONT;
const HUD_LABEL_BASE_SIZE = 17; // 더 크게 (14 -> 17)
const NODE_LABEL_BASE_SIZE = 11.4;

export function GraphCanvas({
  nodes,
  edges,
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
    graph.cooldownTime(0); // 물리 애니메이션 냉각 단축

    // 인터랙션 기본 설정
    graph.enableZoomInteraction(true);
    graph.enablePanInteraction(true);

    return () => {
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

    // 데이터 가공 (fx/fy 고정으로 FA2 레이아웃 반영 및 뭉침 방지를 위한 스케일 배율 적용)
    const formattedNodes = nodes.map((n) => {
      const hasPos = typeof n.x === "number" && typeof n.y === "number";
      // 좌표가 없는 신규 노드는 (0,0) 주변에 미세한 난수(Jitter)를 주어 시작점으로 설정.
      // D3 시뮬레이션의 원점이 (0,0)이 되므로 수동 배치 노드와 공간적 일관성 확보.
      const scaledX = hasPos ? (n.x as number) * GRAPH_SCALE_MULTIPLIER : (Math.random() - 0.5) * 16;
      const scaledY = hasPos ? (n.y as number) * GRAPH_SCALE_MULTIPLIER : (Math.random() - 0.5) * 16;
      return {
        ...n,
        // Keep x/y aligned with the actually rendered force-graph coordinates.
        // Hit testing also uses x/y, so leaving them unscaled makes taps land away from the visual node.
        x: scaledX,
        y: scaledY,
        fx: hasPos ? scaledX : undefined,
        fy: hasPos ? scaledY : undefined,
      };
    });

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

    // 드래그 제어
    // v0.7.139+: 노드 드래그 완전 비활성화 — 모바일/터치패드에서 살짝만 손가락이 움직여도
    // force-graph이 drag로 인식해서 click이 무시되는 버그 방지. dense 모드는 이전부터 off.
    // 사용자가 위치를 미세 조정하고 싶을 땐 '배치 초기화' 버튼으로 force-directed 재배치.
    graph.enableNodeDrag(false);

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
        const isHighlighted = highlightLinksRef.current.has(link.id);
        // Use theme tokens instead of fixed gray/white so light mode paths stay readable.
        if (isHighlighted) return resolvedEdgeHighlightRef.current;
        return resolvedEdgeColorRef.current;
      })
      .linkWidth((link: any) => {
        const isHighlighted = highlightLinksRef.current.has(link.id);
        // Keep paths thin, but dark mode needs enough contrast against the navy canvas.
        return isHighlighted ? 2.15 : 1.05;
      })
      .linkCurvature(0.035)
      // Remove animated particles: they made selected paths feel busy/tacky rather than clean.
      .linkDirectionalParticles(0)
      .linkDirectionalParticleWidth(0)
      .linkDirectionalParticleSpeed(0.016);

    // 노드 스타일 커스텀 렌더링 (Obsidian 퀄리티 재현)
    // v0.7.144+: all-scope 모드 제거 — vault ring (resolveVaultColor 사용) 코드 삭제.
    // vault 외곽선 ring은 single vault에서 모든 노드가 같은 vault이라 무의미.
    graph.nodeCanvasObject((node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
      if (!node || node.x === undefined || node.y === undefined) return;
      const scale = globalScale || 1;
      const size = nodeSize(node.weight, isDense ? "dense" : "normal");
      // v0.7.139+: ref로 최신 hover state를 매 paint call에서 읽는다 (effect 재실행 없음).
      const currentHover = hoveredNodeRef.current;
      const isHovered = currentHover && currentHover.id === node.id;
      const isHighlighted = highlightNodesRef.current.has(node.id);
      const isPersistent = persistentHighlightNodeId === node.id;
      const isFocused =
        isHovered || isPersistent || externalHighlightNodeId === node.id;

      // 1. 노드 본체 (원) — zoom 보정 없이 픽셀 그대로 그린다.
      // force-graph의 `nodeVal/nodeRelSize` 자동 보정에 의존하지 않으므로
      // baseSize를 zoom-out에서도 가독성 있게 키웠다 (옛 공식 대비 1.7~2배).
      ctx.beginPath();
      ctx.arc(node.x, node.y, size, 0, 2 * Math.PI, false);

      // 흐릿한 비포커스 처리
      const hasFocusActive = externalHighlightNodeId || currentHover || externalHighlightType;
      ctx.fillStyle = hasFocusActive && !isFocused && !isHighlighted
        ? `${nodeColor(node.type)}36`
        : nodeColor(node.type);
      ctx.fill();

      // 테두리 선
      ctx.lineWidth = isFocused ? 2 / scale : 0.8 / scale;
      ctx.strokeStyle = isFocused
        ? resolvedEdgeHighlightRef.current
        : isHighlighted
        ? "rgba(255, 255, 255, 0.72)"
        : resolvedNodeOutlineRef.current;
      ctx.stroke();

      // 이중 링 효과 (focused)
      if (isFocused) {
        ctx.beginPath();
        ctx.arc(node.x, node.y, size + 2.5 / scale, 0, 2 * Math.PI, false);
        ctx.strokeStyle = resolvedEdgeHighlightRef.current;
        ctx.lineWidth = 0.8 / scale;
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
        const labelOffsetX = scale < 1.5 ? (size + 8) / scale : 0;
        const labelX = node.x + labelOffsetX;
        const labelY = node.y + size + 3.8 / scale;

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
        const hitRadius = Math.max(
          nodeSize(node.weight, isDense ? "dense" : "normal") * DIRECT_HIT_NODE_RADIUS_MULTIPLIER,
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
      
      // [개선] HUD 노출 줌 레벨을 0.75 이하로 제한 (줌 100% 근처 및 이상에서는 HUD 완벽 제거)
      // scale = 0.75 일 때 opacity = 0, scale = 0.5 일 때 opacity = 1
      const labelOpacity = Math.max(0, Math.min(1, (0.75 - scale) / 0.25));
      if (labelOpacity <= 0.05) return;

      // 1. 실시간 Centroid 연산
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

      // 2. HUD 라벨 그리기 (단순 텍스트 + 테마 변수)
      ctx.save();
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";

      const totalNodes = currentNodes.length || 1;

      for (const gid in groupCoords) {
        const data = groupCoords[gid];
        if (data.count === 0) continue;
        
        // [A안] 노드 개수가 5개 미만인 지극히 작은 소수 그룹(root, _meta 등)은 HUD 라벨 그리기 생략해 잡음 제거
        if (data.count < 5) continue;

        const cx = data.xSum / data.count;
        const cy = data.ySum / data.count;
        
        // centroid보다 위쪽으로 약간 이동 (y 오프셋)
        const drawY = cy - 24 / scale;

        const labelText = data.label;
        const isContent = gid === "content";
        
        // [B안 + alpha] 지배적 content의 opacity를 0.24로 살짝 올리고, meta/root/raw 등은 0.16 이하로 약화
        const targetGroupAlpha = isContent ? 0.24 : 0.16;
        const textOpacity = labelOpacity * targetGroupAlpha;
        
        const fontSize = Math.max(
          isContent ? 12 : 14, 
          (isContent ? 13 : HUD_LABEL_BASE_SIZE) / scale
        );

        ctx.font = `600 ${fontSize}px ${HUD_LABEL_FONT}`;

        // 텍스트 시인성 확보를 위한 뒷배경 outline 효과 (테마 변수)
        ctx.fillStyle = resolvedBgColorRef.current;
        ctx.globalAlpha = textOpacity * 0.75;
        for (let dx = -1.5; dx <= 1.5; dx += 1.5) {
          for (let dy = -1.5; dy <= 1.5; dy += 1.5) {
            if (dx !== 0 || dy !== 0) {
              ctx.fillText(labelText, cx + dx * (0.8 / scale), drawY + dy * (0.8 / scale));
            }
          }
        }

        // 본문 텍스트 (테마 변수)
        ctx.fillStyle = resolvedLabelColorRef.current;
        ctx.globalAlpha = textOpacity;
        ctx.fillText(labelText, cx, drawY);
      }
      ctx.restore();
    });

    // v0.7.139+: fitView는 scope 전환(all ↔ current) 또는 첫 데이터 로드 시에만.
    // 검색/필터로 nodes가 바뀌어도 사용자의 pan/zoom 위치를 보존한다.
    const scopeChanged = prevIsDenseRef.current !== isDense;
    const firstLoad = prevNodeCountRef.current === 0 && nodes.length > 0;
    if (scopeChanged || firstLoad) {
      if (nodes.length > 0) {
        setTimeout(() => {
          if (graphInstanceRef.current) {
            graphInstanceRef.current.zoomToFit(300, 96);
          }
        }, 50);
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
        graphInstanceRef.current.onRenderFramePre(() => {}); // cleanup 콜백 (타입 안정 no-op)
      }
    };
  }, [
    nodes,
    edges,
    isDense,
    // v0.7.144+: vaultCentroids 의존성 완전히 제거 (all-scope 모드 종료).
    // v0.7.139+: hoveredNode/highlightNodes/highlightLinks는 ref 기반이라 effect deps에서 제외.
    // hover 시 effect가 재실행되지 않아 — 캔버스 pan/zoom 위치가 유지되고 클릭이 무효화되지 않음.
    externalHighlightNodeId,
    persistentHighlightNodeId,
    externalHighlightType,
    onNodeInspect,
    onPositionsChange,
  ]);

  const fitGraph = () => {
    if (graphInstanceRef.current) {
      // fx/fy를 날려서 시뮬레이션을 풀고 fitView 재배치
      const { nodes: currentNodes } = graphInstanceRef.current.graphData();
      currentNodes.forEach((n: any) => {
        n.fx = undefined;
        n.fy = undefined;
      });
      graphInstanceRef.current.cooldownTime(800);
      
      // v0.7.148+: force-graph API 버전에 따른 방어적 시뮬레이션 reheat 처리
      const graphInst = graphInstanceRef.current;
      if (typeof graphInst.d3ReheatSimulation === "function") {
        graphInst.d3ReheatSimulation();
      } else if (typeof graphInst.reheatSimulation === "function") {
        graphInst.reheatSimulation();
      } else if (typeof graphInst.d3AlphaTarget === "function") {
        graphInst.d3AlphaTarget(0.3);
        setTimeout(() => {
          if (graphInstanceRef.current) {
            graphInstanceRef.current.d3AlphaTarget(0);
          }
        }, 120);
      }

      setTimeout(() => {
        if (graphInstanceRef.current) {
          graphInstanceRef.current.zoomToFit(400, 96);
        }
      }, 150);
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

  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        position: "relative",
        background: "var(--graph-canvas-bg)",
        overflow: "hidden",
      }}
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
      <div
        style={{
          position: "absolute",
          right: 12,
          top: 12,
          zIndex: 10,
          display: "flex",
          gap: 8,
          pointerEvents: "auto",
        }}
      >
        {onFullscreen && (
          <button
            type="button"
            onClick={onFullscreen}
            style={graphButtonStyle}
            aria-label="그래프 전체보기"
            title="팝업으로 크게 보기"
          >
            전체보기
          </button>
        )}
        <button
          type="button"
          onClick={fitGraph}
          style={graphButtonStyle}
          aria-label="그래프 화면 맞춤"
          title="배치를 초기화하고 모든 노드가 화면에 들어오도록 뷰를 맞춥니다"
        >
          맞춤
        </button>
        {/* v0.7.139+: 줌 컨트롤 (− / 배율 / +). 모바일/데스크탑 공통 */}
        <button
          type="button"
          onClick={zoomOut}
          style={{ ...graphButtonStyle, minWidth: 32, padding: "6px 8px" }}
          aria-label="그래프 축소"
          title="축소 (단축키: −)"
        >
          −
        </button>
        <span
          aria-live="polite"
          style={{
            ...graphButtonStyle,
            cursor: "default",
            minWidth: 52,
            textAlign: "center",
            fontVariantNumeric: "tabular-nums",
          }}
          title={`현재 줌 배율 — 더블클릭으로 100%로 리셋`}
          onDoubleClick={() => graphInstanceRef.current?.zoomTo(1, 200)}
        >
          {zoomLabel}
        </span>
        <button
          type="button"
          onClick={zoomIn}
          style={{ ...graphButtonStyle, minWidth: 32, padding: "6px 8px" }}
          aria-label="그래프 확대"
          title="확대 (단축키: +)"
        >
          +
        </button>
      </div>
    </div>
  );
}
