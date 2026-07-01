import {
  ReactFlow,
  Background,
  Controls,
  ReactFlowProvider,
  useReactFlow,
  Handle,
  Position,
  useNodesState,
  useEdgesState,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { GraphNode, GraphEdge } from "../types";

interface Props {
  nodes: GraphNode[];
  edges: GraphEdge[];
  /** hover/click 시 선택 노드 메타를 상위 UI에 전달 */
  onNodeInspect?: (node: GraphNode) => void;
  /** single click — 데스크탑 전용 (페이지 이동), 모바일에서는 no-op (라벨 토글) */
  onNodeClick?: (slug: string) => void;
  /** double click / double tap — 모바일+데스크탑 공통 페이지 이동 */
  onNodeDoubleClick?: (slug: string) => void;
  /** 외부(인사이트 카드 등)에서 하이라이트 요청한 노드 ID */
  externalHighlightNodeId?: string | null;
  /** 현재 문서처럼 항상 강조해야 하는 노드 ID */
  persistentHighlightNodeId?: string | null;
  /** 외부에서 하이라이트 요청한 문서 타입 */
  externalHighlightType?: string | null;
  /** 전체화면 모달 요청 — 상위 컴포넌트가 모달을 열어 처리 */
  onFullscreen?: () => void;
}

// SCHEMA 8종(확장 매핑) — type별 노드 색상. 미분류/미인식 → default gray.
const TYPE_COLORS: Record<string, string> = {
  decision: "#a855f7",
  concept: "#22c55e",
  manual: "#3b82f6",
  pattern: "#f97316",
  insight: "#eab308",
  journal: "#06b6d4",
  person: "#ec4899",
  comparison: "#ef4444",
  tool: "#6b7280",
  rule: "#6366f1",
};
const DEFAULT_COLOR = "#9ca3af";

// Community palette (v0.6.15+ Louvain). 같은 community id → 같은 색.
// palette는 type 색과 다르도록 의도적으로 선택 — 구조 vs metadata 시각 구분.
// GraphPage가 import해서 toolbar 옆에 palette dot 15개로 시각화한다.
export const COMMUNITY_PALETTE: string[] = [
  "#22c55e", "#3b82f6", "#f97316", "#a855f7", "#ec4899",
  "#eab308", "#06b6d4", "#ef4444", "#6366f1", "#84cc16",
  "#14b8a6", "#f43f5e", "#a3a3a3", "#facc15", "#8b5cf6",
];

export function communityColor(community: number | undefined): string {
  if (community === undefined || community < 0) return DEFAULT_COLOR;
  return COMMUNITY_PALETTE[community % COMMUNITY_PALETTE.length];
}

// ───────────────────────────────────────────────────────────────────────────
// v0.6.12 Graph — UX 3개 fix.
//
// 이전 (v0.6.11+): Patch 5/6/7 — programmatic fitView, zoom 범위 완화, translateExtent 확장.
//
// 변경 사항 (v0.6.12, 3개 패치 묶음):
//   Patch 1 (edge 가시화): edge stroke 옅어서 "선이 안 보인다"는 사용자 보고.
//     → stroke를 mid gray(#6b7280)로 + strokeWidth 1.5 + opacity 0.6로 강화.
//       dark 배경(#0a0e1a)에서 명확히 보이는 명도대. 모바일/데스크탑 공통.
//
//   Patch 2 (모바일 click vs double-click): 모바일에서 1회 탭 → label 표시,
//     더블 탭 → 페이지 이동. 데스크탑은 기존 hover label + 1회 click → navigate 유지.
//     → isCoarsePointer(pointer:coarse) 또는 matchMedia('(pointer:coarse)')로
//       touch device 감지. 노드 클릭이 발생할 때 tap-count를 누적해 single/double 구분.
//       라우팅은 onNodeDoubleClick → navigate, 라벨 토글은 onNodeClick.
//     → GraphPage에 onNodeDoubleClick prop 추가 (navigate) + 기존 onNodeClick은
//       모바일에서는 no-op (label은 이미 hover/tap으로 표시됨).
//
//   Patch 3 (노드 드래그): xyflow의 기본 nodesDraggable=true이지만 prop이 명시되지
//     않아 default 토글이 헷갈릴 수 있음 + ObsidianNode wrapper에
//     `nodrag` 클래스 지정이 없어 노드 wrapper 자체가 pan으로 잡힘.
//     → ReactFlow에 `nodesDraggable={true}` 명시 + 노드 wrapper는 pointerEvents:
//       'all'로 드래그 가능. 메모리상 이동만 — 백엔드 저장은 다음 라운드.
//     → ObsidianNode 자체에 `data-no-restyle` 등 영향 없도록 pointer-events만 설정.
// ───────────────────────────────────────────────────────────────────────────

export function nodeColor(type: string | undefined, community?: number): string {
  // v0.6.15+: community 색상이 우선 (구조 기반 색). community=-1 또는 없으면 type 색 fallback.
  if (community !== undefined && community >= 0) {
    return communityColor(community);
  }
  if (!type) return DEFAULT_COLOR;
  return TYPE_COLORS[type] ?? DEFAULT_COLOR;
}

// 노드 크기: Obsidian Graph처럼 작은 점. weight=1→6.5, weight=4→9, weight=9→11.5
export function nodeSize(weight: number | undefined): number {
  return 4 + Math.sqrt(Math.max(weight ?? 1, 1)) * 2.5;
}

// ───────────────────────────────────────────────────────────────────────────
// ObsidianNode — xyflow custom renderer.
//   - 외형: 둥근 점 (borderRadius 50%).
//   - 호버 시: 점 자체는 그대로, but wrapper가 scale 1.6으로 살짝 부풀고
//              ring이 생겨 "선택 가능" 신호.
//   - 텍스트 ❌ — label은 hover overlay(Patch 2)로 분리.
//   - 자기 자신은 absolute <div>로 label 표시하지 않고, 부모의 hover overlay에 의존.
//     → xyflow의 nodeWidth/Height가 작아도 텍스트가 노드 박스에 영향 없음.
// ───────────────────────────────────────────────────────────────────────────
// ObsidianNode — xyflow custom renderer.
//   - 외형: 둥근 점 + 그 아래에 작은 title 라벨 (Obsidian-style, 상시 표시).
//   - hover/포커스 시 라벨 또렷, 비포커스 시 흐리게.
function ObsidianNode({
  data,
}: {
  data: {
    color: string;
    size: number;
    opacity?: number;
    highlighted?: boolean;
    title?: string;
    dim?: boolean;
    persistent?: boolean;
  };
}) {
  // xyflow v12는 node에 `data`만 custom으로 전달받음.
  // 좌표/타이틀은 onMouseEnter에서 GraphNode 인덱스로 조회 (아래 handle).
  // Patch 3: pointerEvents: 'all' + cursor: 'grab' 으로 모바일에서 노드 잡기 신호.
  //   onMouseEnter는 hover-only (데스크탑). 모바일에선 클릭으로 라벨 토글됨.
  const isEmphasized = Boolean(data.highlighted || data.persistent);
  const labelOpacity = isEmphasized ? 1 : data.dim ? 0.35 : 0.85;
  const labelText = data.title ?? "";
  return (
    <div
      className="obsidian-node-wrap"
      style={{
        // 노드 wrapper는 dot + label 영역 전체를 잡되, xyflow node box는 dot 크기로 유지
        // (라벨은 absolute로 띄움). pointerEvents는 dot만 받게.
        position: "relative",
        width: data.size,
        height: data.size,
        opacity: data.opacity ?? 1,
        pointerEvents: "none",
      }}
    >
      <div
        className="obsidian-node"
        style={{
          width: data.size,
          height: data.size,
          borderRadius: "50%",
          background: data.color,
          border: data.persistent
            ? "2px solid var(--graph-edge-highlight)"
            : "1px solid var(--graph-node-outline)",
          boxShadow: isEmphasized
            ? "var(--graph-node-glow)"
            : "0 0 0 1px var(--graph-node-outline)",
          cursor: "grab",
          pointerEvents: "all",
          touchAction: "none",
          transition: "transform 120ms ease-out, box-shadow 120ms ease-out",
          transform: data.persistent ? "scale(1.45)" : "scale(1)",
        }}
        onMouseEnter={(e) => {
          (e.currentTarget as HTMLDivElement).style.transform = "scale(1.75)";
          (e.currentTarget as HTMLDivElement).style.boxShadow = "var(--graph-node-glow)";
        }}
        onMouseLeave={(e) => {
          (e.currentTarget as HTMLDivElement).style.transform = data.persistent
            ? "scale(1.45)"
            : "scale(1)";
          (e.currentTarget as HTMLDivElement).style.boxShadow = isEmphasized
            ? "var(--graph-node-glow)"
            : "0 0 0 1px var(--graph-node-outline)";
        }}
      >
      {/* React Flow custom nodes need explicit handles; otherwise edges are kept in
          data but no SVG edge path is created. Keep handles invisible so the node
          remains an Obsidian-style dot. */}
      <Handle
        type="target"
        position={Position.Top}
        style={{ opacity: 0, width: 1, height: 1, pointerEvents: "none" }}
        isConnectable={false}
      />
      <Handle
        type="source"
        position={Position.Bottom}
        style={{ opacity: 0, width: 1, height: 1, pointerEvents: "none" }}
        isConnectable={false}
      />
      </div>
      {labelText && (
        <div
          className="obsidian-node-label"
          style={{
            position: "absolute",
            top: "100%",
            left: "50%",
            transform: "translateX(-50%)",
            marginTop: 4,
            fontSize: 11,
            lineHeight: 1.25,
            color: "var(--graph-label-color)",
            textShadow: "var(--graph-label-shadow)",
            // 최대 2줄 + 폭 180px까지 줄바꿈 허용, 더 길면 잘림.
            width: 180,
            maxWidth: 180,
            whiteSpace: "normal",
            overflow: "hidden",
            display: "-webkit-box",
            WebkitLineClamp: 2,
            WebkitBoxOrient: "vertical",
            textAlign: "center",
            opacity: labelOpacity,
            fontWeight: data.persistent ? 700 : 500,
            pointerEvents: "none",
            userSelect: "none",
            transition: "opacity 120ms ease-out",
          }}
        >
          {labelText}
        </div>
      )}
    </div>
  );
}

const nodeTypes = { obsidian: ObsidianNode };

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

function GraphCanvasInner({
  nodes,
  edges,
  onNodeInspect,
  onNodeClick,
  onNodeDoubleClick,
  externalHighlightNodeId,
  persistentHighlightNodeId,
  externalHighlightType,
  onFullscreen,
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  // hover된 노드 ID — label overlay 표시용
  const [hoveredNode, setHoveredNode] = useState<{
    id: string;
    title: string;
    type: string | undefined;
    weight: number;
    x: number; // viewport (screen) px
    y: number;
  } | null>(null);
  const [hoveredEdgeId, setHoveredEdgeId] = useState<string | null>(null);

  // Patch 2: 모바일/터치 디바이스 감지.
  // - matchMedia('(pointer:coarse)') → 터치스크린 (모바일/태블릿)
  // - 1회 click → label 토글 (hoveredNode가 이미 있으면 clear, 없으면 set)
  // - 더블 click → onNodeDoubleClick (navigate)
  // 데스크탑은 1회 click → onNodeClick (navigate), hover로는 label 표시.
  // 이 분기를 컴포넌트 안에서 결정한다 (consumer 단순화).
  //
  // 모바일 더블탭 디텍션: xyflow의 onNodeDoubleClick는 `dblclick` 이벤트에 바인딩
  // 되어 있어 터치 디바이스에서는 안정적으로 발생하지 않는다 (브라우저 의존).
  // → 자체 tap debouncer: 1회 click 발생 후 320ms 안에 같은 노드 click이
  //   다시 들어오면 "double-tap"으로 판단 → onNodeDoubleClick 호출.
  //   320ms 안에 두 번째 tap이 없으면 single-tap 확정 → label toggle.
  const [isCoarse, setIsCoarse] = useState<boolean>(() => {
    if (typeof window === "undefined" || !window.matchMedia) return false;
    return window.matchMedia("(pointer:coarse)").matches;
  });
  useEffect(() => {
    if (typeof window === "undefined" || !window.matchMedia) return;
    const mq = window.matchMedia("(pointer:coarse)");
    const handler = (e: MediaQueryListEvent) => setIsCoarse(e.matches);
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, []);

  // Patch 2: 모바일 tap 디바운서용 ref. 마지막 클릭 노드 + 타이머.
  const tapStateRef = useRef<{ id: string | null; timer: number | null }>({
    id: null,
    timer: null,
  });

  // Patch 5: useReactFlow hook — programmatic fitView 호출용.
  // ReactFlowProvider 안에서만 동작 → GraphCanvas를 Provider로 wrap (export 시).
  const { fitView, flowToScreenPosition } = useReactFlow();

  // Patch 2: 모바일 tap 디바운서 타이머 cleanup.
  useEffect(() => {
    const tap = tapStateRef.current;
    return () => {
      if (tap.timer != null) {
        window.clearTimeout(tap.timer);
        tap.timer = null;
      }
    };
  }, []);

  // 노드 ID → GraphNode 매핑 (overlay에 메타 표시)
  const nodeMap = useMemo(() => {
    const m = new Map<string, GraphNode>();
    for (const n of nodes) {
      const id = (n as any).id ?? n.slug;
      m.set(id, n);
    }
    return m;
  }, [nodes]);

  const rfNodes = useMemo(
    () =>
      nodes.map((n) => {
        const id = (n as any).id ?? n.slug;
        const type = (n as any).type ?? n.type;
        const weight = (n as any).weight ?? 1;
        const size = nodeSize(weight);
        const x = typeof n.x === "number" ? n.x : 0;
        const y = typeof n.y === "number" ? n.y : 0;
        const title = (n as any).title ?? n.slug ?? id;
        const community = (n as any).community as number | undefined;
        return {
          id,
          type: "obsidian" as const,
          position: { x, y },
          // v0.6.15+: pass community to nodeColor — community palette overrides type color.
          data: { color: nodeColor(type, community), size, title, community },
        };
      }) as any,
    [nodes]
  );

  const rfEdges = useMemo(
    () =>
      edges.map((e, i) => ({
        id: `e${i}`,
        source: (e as any).source ?? e.source_slug,
        target: (e as any).target ?? e.target_slug,
        // 직선 edge (xyflow default bezier/smoothstep을 우회). 점 노드 사이의
        // 별자리 느낌을 위해 곡선 ❌ — 직선만 허용.
        type: "straight" as const,
        // Obsidian-style: relationship lines are quiet by default; hover reveals structure.
        style: {
          stroke: "var(--graph-edge)",
          strokeWidth: 0.65,
          strokeOpacity: 0.16,
        },
        // xyflow marker 정의 (선택): 끝점 화살표는 일단 생략 — 점 노드 중심에
        // 닿는 직선만으로도 관계 가시화에 충분.
      })),
    [edges]
  );

  // React Flow controlled state. Without this, dragging changes are discarded because
  // every render reuses the memoized server layout nodes.
  const [flowNodes, setFlowNodes, onNodesChange] = useNodesState(rfNodes);
  const [flowEdges, setFlowEdges, onEdgesChange] = useEdgesState(rfEdges);

  useEffect(() => {
    setFlowNodes(rfNodes);
  }, [rfNodes, setFlowNodes]);

  useEffect(() => {
    setFlowEdges(rfEdges);
  }, [rfEdges, setFlowEdges]);

  const focus = useMemo(() => {
    const nodeIds = new Set<string>();
    const edgeIds = new Set<string>();

    // 1) 외부에서 전달된 노드 하이라이트
    if (externalHighlightNodeId) {
      nodeIds.add(externalHighlightNodeId);
      // 해당 노드와 연결된 엣지 및 이웃 노드들도 하이라이트
      for (const edge of flowEdges) {
        if (edge.source === externalHighlightNodeId || edge.target === externalHighlightNodeId) {
          edgeIds.add(edge.id);
          nodeIds.add(String(edge.source));
          nodeIds.add(String(edge.target));
        }
      }
    }

    // 2) 외부에서 전달된 특정 타입 하이라이트
    if (externalHighlightType) {
      // 해당 타입인 노드들을 모두 하이라이트
      for (const fn of flowNodes) {
        const nodeMeta = nodeMap.get(fn.id);
        if (nodeMeta && (nodeMeta.type === externalHighlightType || (!nodeMeta.type && externalHighlightType === "미분류"))) {
          nodeIds.add(fn.id);
        }
      }
    }

    // 3) 마우스 오버된 edge 하이라이트
    if (hoveredEdgeId) {
      const edge = flowEdges.find((e) => e.id === hoveredEdgeId);
      if (edge) {
        edgeIds.add(edge.id);
        nodeIds.add(String(edge.source));
        nodeIds.add(String(edge.target));
      }
    }

    // 4) 마우스 오버된 노드 하이라이트
    if (hoveredNode) {
      nodeIds.add(hoveredNode.id);
      const hoveredCommunity = (hoveredNode as any).community as number | undefined;
      for (const edge of flowEdges) {
        if (edge.source === hoveredNode.id || edge.target === hoveredNode.id) {
          edgeIds.add(edge.id);
          nodeIds.add(String(edge.source));
          nodeIds.add(String(edge.target));
        }
      }
      // v0.6.15+: 같은 community에 속한 노드도 함께 highlight. structural grouping
      // 가 가장 큰 차별점 — hover가 "이 문서랑 같은 community"를 보여준다.
      if (hoveredCommunity !== undefined && hoveredCommunity >= 0) {
        for (const fn of flowNodes) {
          if (
            (fn as any).data?.community === hoveredCommunity &&
            !nodeIds.has(fn.id)
          ) {
            nodeIds.add(fn.id);
          }
        }
      }
    }

    return {
      active: nodeIds.size > 0 || edgeIds.size > 0,
      nodeIds,
      edgeIds,
    };
  }, [flowEdges, flowNodes, nodeMap, hoveredEdgeId, hoveredNode, externalHighlightNodeId, externalHighlightType]);

  const displayNodes = useMemo(
    () =>
      flowNodes.map((node) => {
        const highlighted = focus.nodeIds.has(node.id);
        const persistent = persistentHighlightNodeId === node.id;
        return {
          ...node,
          data: {
            color: (node.data as any).color,
            size: (node.data as any).size,
            title: (node.data as any).title,
            highlighted,
            persistent,
            dim: focus.active && !highlighted && !persistent,
            opacity: !focus.active || highlighted || persistent ? 1 : 0.22,
          },
        };
      }),
    [flowNodes, focus, persistentHighlightNodeId]
  );

  const displayEdges = useMemo(
    () =>
      flowEdges.map((edge) => {
        const highlighted = focus.edgeIds.has(edge.id);
        return {
          ...edge,
          animated: highlighted,
          style: {
            ...(edge.style ?? {}),
            stroke: highlighted ? "var(--graph-edge-highlight)" : "var(--graph-edge)",
            strokeWidth: highlighted ? 1.35 : 0.65,
            strokeOpacity: !focus.active ? 0.16 : highlighted ? 0.82 : 0.045,
          },
        };
      }),
    [flowEdges, focus]
  );

  const fitGraph = useCallback(() => {
    window.setTimeout(() => {
      fitView({ duration: 360, padding: 0.32, minZoom: 0.01, maxZoom: 1.2 });
    }, 20);
  }, [fitView]);

  const resetLayout = useCallback(() => {
    setFlowNodes(rfNodes);
    fitGraph();
  }, [rfNodes, setFlowNodes, fitGraph]);

  // Patch 5: 데이터 변경 시 fitView 재호출.
  // - mount 시 (rfNodes[0] 한 번 fit)
  // - orphan toggle / vault 변경 / force-directed 재계산 후 자동 재중심.
  // - 이전 mount 1회 한정 → 빈 화면.
  useEffect(() => {
    if (flowNodes.length === 0) return;
    // 다음 tick에 호출 — xyflow가 viewport 측정을 끝낸 후 fitView가 동작.
    const id = window.setTimeout(() => {
      fitView({ duration: 300, padding: 0.32, minZoom: 0.01, maxZoom: 1.2 });
    }, 50);
    return () => window.clearTimeout(id);
  }, [flowNodes.length, flowEdges.length, fitView]);

  // hover 시 GraphNode 메타 + screen 좌표 계산
  const handleNodeEnter = useCallback(
    (
      _event: React.MouseEvent | React.TouchEvent,
      node: { id: string; position: { x: number; y: number } }
    ) => {
      const meta = nodeMap.get(node.id);
      if (!meta) return;
      // 노드 중심 좌표 = server x/y + size/2
      const size = nodeSize(meta.weight);
      // 화면 좌표로 변환 — overlay는 position: fixed로 그려진다.
      // xyflow의 flowToScreenPosition이 viewport 변환/zoom/pan을 모두 반영한다.
      const screen = flowToScreenPosition({
        x: node.position.x + size / 2,
        y: node.position.y + size / 2,
      });
      onNodeInspect?.(meta);
      setHoveredNode({
        id: node.id,
        title: meta.title,
        type: meta.type,
        weight: meta.weight ?? 0,
        x: screen.x,
        y: screen.y,
      });
    },
    [nodeMap, onNodeInspect, flowToScreenPosition]
  );

  const handleNodeLeave = useCallback(() => {
    setHoveredNode(null);
  }, []);

  const handleNodeClick = useCallback(
    (_: React.MouseEvent, n: { id: string }) => {
      // Patch 2: 모바일(coarse pointer)에서는 1회 click이 label 토글,
      // 더블 tap(320ms 내 같은 노드 재클릭)은 navigate.
      // 데스크탑은 1회 click → navigate (기존 동작).
      if (isCoarse) {
        const tap = tapStateRef.current;
        // 같은 노드 & 타이머 살아있으면 → double-tap 확정.
        if (tap.id === n.id && tap.timer != null) {
          window.clearTimeout(tap.timer);
          tap.id = null;
          tap.timer = null;
          // 라벨이 떠있으면 즉시 닫기 (탭 → 페이지 이동 흐름 자연스럽게).
          setHoveredNode(null);
          onNodeDoubleClick?.(n.id);
          return;
        }
        // 첫 tap 또는 다른 노드 tap → 타이머 시작, label toggle.
        if (tap.timer != null) {
          window.clearTimeout(tap.timer);
        }
        const meta = nodeMap.get(n.id);
        if (!meta) {
          // meta 없으면 안전하게 단일 탭으로 처리.
          tap.id = n.id;
          tap.timer = window.setTimeout(() => {
            tap.id = null;
            tap.timer = null;
          }, 320);
          return;
        }
        onNodeInspect?.(meta);
        // 같은 노드 재탭이 아니면 label은 즉시 토글 + 첫 탭 예약.
        setHoveredNode((prev) => {
          if (prev && prev.id === n.id) return null;
          const size = nodeSize(meta.weight);
          const baseX = typeof meta.x === "number" ? meta.x : 0;
          const baseY = typeof meta.y === "number" ? meta.y : 0;
          // 화면 좌표로 변환 — 모바일 1회 탭에서도 노드 위치에 정확히 라벨 표시.
          // v0.6.12 1차에서 server coords 그대로 썼더니 zoom/pan 후 라벨이 어긋남.
          const screen = flowToScreenPosition({
            x: baseX + size / 2,
            y: baseY + size / 2,
          });
          return {
            id: n.id,
            title: meta.title,
            type: meta.type,
            weight: meta.weight ?? 0,
            x: screen.x,
            y: screen.y,
          };
        });
        tap.id = n.id;
        tap.timer = window.setTimeout(() => {
          tap.id = null;
          tap.timer = null;
        }, 320);
        return;
      }
      onNodeClick?.(n.id);
    },
    [isCoarse, nodeMap, onNodeInspect, onNodeClick, onNodeDoubleClick, flowToScreenPosition]
  );

  const handleNodeDoubleClick = useCallback(
    (_: React.MouseEvent, n: { id: string }) => {
      // Patch 2: 더블 click/tap → 페이지 이동 (모바일+데스크탑 공통).
      // 모바일(coarse)인 경우 single click에서 onNodeClick이 navigate를 호출하지
      // 않으므로 이 핸들러가 navigate의 단일 진입점.
      onNodeDoubleClick?.(n.id);
    },
    [onNodeDoubleClick]
  );

  // Patch 2+: viewport(zoom/pan) 이동 시 표시 중인 라벨의 screen 좌표를
  //   재계산해서 노드 위에 정확히 머무르게 한다.
  //   화면 좌표 → 화면 좌표 함수라 server coords는 rfNodes에서 다시 읽는다.
  const rfNodesById = useMemo(() => {
    const m = new Map<string, { x: number; y: number }>();
    for (const rn of flowNodes) {
      m.set(rn.id, rn.position);
    }
    return m;
  }, [flowNodes]);

  const handleMove = useCallback(() => {
    setHoveredNode((prev) => {
      if (!prev) return prev;
      const pos = rfNodesById.get(prev.id);
      if (!pos) return prev;
      const screen = flowToScreenPosition({
        x: pos.x + nodeSize(prev.weight) / 2,
        y: pos.y + nodeSize(prev.weight) / 2,
      });
      return { ...prev, x: screen.x, y: screen.y };
    });
  }, [rfNodesById, flowToScreenPosition]);

  return (
    <div
      ref={containerRef}
      style={{
        width: "100%",
        height: "100%",
        position: "relative",
        background: "var(--graph-canvas-bg)",
        // Patch 4: 모바일에서 브라우저 기본 pinch/scroll 방지
        touchAction: "none",
        userSelect: "none",
        WebkitTapHighlightColor: "transparent",
        overflow: "hidden",
      }}
    >
      <ReactFlow
        nodes={displayNodes as any}
        edges={displayEdges}
        onNodesChange={onNodesChange as any}
        onEdgesChange={onEdgesChange as any}
        nodeTypes={nodeTypes}
        onNodeClick={handleNodeClick}
        onNodeDoubleClick={handleNodeDoubleClick}
        onNodeMouseEnter={handleNodeEnter}
        onNodeMouseLeave={handleNodeLeave}
        onEdgeMouseEnter={(_, edge) => setHoveredEdgeId(edge.id)}
        onEdgeMouseLeave={() => setHoveredEdgeId(null)}
        // Patch 2+: viewport 이동 시 표시 중인 라벨의 screen 좌표 재계산.
        onMove={handleMove}
        // Patch 3: 노드 드래그 활성화 (xyflow v12 기본값 true이지만 명시).
        //   모바일에서 노드를 잡고 캔버스 자유 이동 가능. 메모리상 이동 — 백엔드
        //   저장은 다음 라운드(v0.6.13 후보).
        nodesDraggable={true}
        nodesConnectable={false}
        // Patch 5: programmatic fitView 사용 → prop `fitView` 제거 (중복 fit 방지).
        // Patch 3: 모바일/데스크탑 gesture 강화
        panOnDrag
        // Canvas hover + mouse wheel = zoom in/out. Keep scroll-pan off so wheel is
        // always interpreted as graph zoom, matching the user's desktop expectation.
        panOnScroll={false}
        zoomOnScroll
        zoomOnPinch
        selectionOnDrag={false} // drag = pan, click = select (텍스트 선택 방지)
        // Patch 6: zoom 범위 완화 — pinch zoom out 시 노드 사라짐 방지.
        minZoom={0.005}
        maxZoom={8}
        // Patch 7: translateExtent 확장 — 서버 spring layout 결과 (±10000)에 여유.
        //   xyflow v12는 viewport를 translateExtent로 clamp하므로 너무 작으면
        //   노드가 viewport 밖으로 밀려나 사라짐.
        translateExtent={[
          [-100000, -100000],
          [100000, 100000],
        ]}
        proOptions={{ hideAttribution: true }}
      >
        <Background color="var(--graph-grid)" bgColor="var(--graph-canvas-bg)" size={1} gap={32} />
        <Controls
          style={{
            background: "var(--graph-surface-strong)",
            borderColor: "var(--graph-border)",
            color: "var(--graph-text)",
          }}
          showInteractive={false}
        />
      </ReactFlow>

      {/* 전체보기 / 맞춤보기 / 배치 초기화 버튼 */}
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
          aria-label="그래프 맞춤보기"
          title="모든 노드가 화면에 들어오도록 뷰를 맞춥니다"
        >
          맞춤보기
        </button>
        <button
          type="button"
          onClick={resetLayout}
          style={graphButtonStyle}
          aria-label="그래프 배치 초기화"
        >
          배치 초기화
        </button>
      </div>

      {/* Patch 2: hover/tap overlay — position: fixed로 화면 좌표에 정확히 표시.
            v0.6.12 1차에서 absolute + server coords 썼더니 zoom/pan 후 라벨이
            어긋나서 "안 보임" 증상. 화면 좌표 + fixed → 어느 viewport 상태에서든
            노드 위에 정확히 표시. xyflow 노드 자체에는 텍스트 0px → 텍스트 오버랩 0. */}
      {hoveredNode && (
        <div
          data-testid="graph-hover-label"
          style={{
            position: "fixed",
            left: hoveredNode.x,
            top: hoveredNode.y,
            transform: "translate(-50%, calc(-100% - 14px))",
            pointerEvents: "none",
            background: "var(--graph-tooltip-bg)",
            color: "var(--graph-text)",
            padding: "6px 10px",
            borderRadius: 6,
            fontSize: 12,
            fontWeight: 500,
            lineHeight: 1.35,
            border: "1px solid var(--graph-tooltip-border)",
            boxShadow: "var(--graph-tooltip-shadow)",
            whiteSpace: "nowrap",
            maxWidth: 320,
            zIndex: 10,
          }}
        >
          <div style={{ fontWeight: 600 }}>{hoveredNode.title}</div>
          <div
            style={{
              fontSize: 10,
              color: "var(--graph-text-muted)",
              marginTop: 2,
              display: "flex",
              gap: 8,
            }}
          >
            {hoveredNode.type && <span>type: {hoveredNode.type}</span>}
            <span>links: {hoveredNode.weight}</span>
          </div>
        </div>
      )}
    </div>
  );
}

// Patch 5: useReactFlow는 ReactFlowProvider 안에서만 동작.
// 기존 호출처(<GraphCanvas ... />)가 깨지지 않도록 named export를
// ReactFlowProvider로 wrap한 HOC로 재export.
export function GraphCanvas(props: Props) {
  return (
    <ReactFlowProvider>
      <GraphCanvasInner {...props} />
    </ReactFlowProvider>
  );
}
