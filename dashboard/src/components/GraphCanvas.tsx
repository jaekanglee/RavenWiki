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
  useViewport,
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
  /** all-vault 등 고밀도 그래프에서는 기본 라벨/엣지를 낮춰 지도 시인성을 우선한다. */
  density?: "normal" | "dense";
  /** all-vault 모드에서 vault 소속을 보여주는 centroid + halo 표식. */
  vaultCentroids?: VaultCentroid[];
  /**
   * v0.7.126+: 노드 드래그 종료 시점(dragging=false + position 변화)에 호출.
   * GraphPage가 받아서 batch로 POST /api/vaults/{vault}/graph/positions 보냄.
   * 키는 node.id (= GraphNode.slug 또는 "{vault}:{slug}" for all-scope).
   */
  onPositionsChange?: (positions: Record<string, { x: number; y: number }>) => void;
}

export interface VaultCentroid {
  vault: string;
  x: number;
  y: number;
  /** vault 별 halo 반경 — vault 내 노드 분포 + count 기반. */
  radius: number;
}

// SCHEMA 9종(v0.7.44+) — type별 노드 색상. 미분류/미인식 → default gray.
// v0.7.98+ 동기화: 기존 8종(decision/manual/pattern/insight) → SCHEMA 9종 정합.
// SOT: _meta/SCHEMA.md §Type Taxonomy (concept/person/comparison/project/tool/rule/query/journal/issue)
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

// v0.7.98+ Sidebar Explorer에서 사용하는 짧은 type 라벨 (3-4글자).
// SCHEMA 9종 정합. 미인식 type은 빈 문자열 → 라벨 미표시.
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
    isClusterNode?: boolean;
    showLabel?: boolean;
  };
}) {
  const { zoom } = useViewport();
  const isClusterNode = Boolean(data.isClusterNode);
  const isEmphasized = Boolean(data.highlighted || data.persistent || isClusterNode);
  
  // 줌 레벨이 0.35 미만으로 떨어지면 일반 라벨 숨김 및 페이드아웃 (0.35~0.55 구간 보간)
  // 단, 클러스터 노드일 경우에는 줌아웃 상태에서도 항상 뚜렷하게 노출됨
  const zoomAlpha = isClusterNode ? 1.0 : zoom < 0.35 ? 0 : zoom > 0.55 ? 1 : (zoom - 0.35) / 0.2;
  const labelOpacity = isEmphasized 
    ? 1 
    : data.dim 
      ? 0.35 * zoomAlpha 
      : 0.85 * zoomAlpha;
  const labelText = data.showLabel === false ? "" : data.title ?? "";
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
          // v0.7.124+: persistent(현재 문서 등 항상 강조) 노드는 hover 시에도
          // 그 강조가 묻히지 않도록 더 크게 부풀린다 (1.45 → 1.95). 일반 노드는
          // 1 → 1.75. 결과: persistent 노드가 hover 시 더 강조되어 보이고,
          // 일반 노드보다 시각적 위계가 유지된다.
          (e.currentTarget as HTMLDivElement).style.transform = data.persistent
            ? "scale(1.95)"
            : "scale(1.75)";
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

// v0.7.123+ NebulaNode 제거. scaleMode = "PLANET" 단일이고, 노드는 항상
// obsidian type으로만 그려진다. v0.6.15 multiscale cluster mode의 잔재
// (성운 + 은하 라벨 노드) 라 dead code. 렌더 비용 + 핸들러 등록 줄임.
const nodeTypes = {
  obsidian: ObsidianNode,
};

/**
 * Server-side layout의 (id, x, y)가 prev와 의미상 달라졌는지 비교.
 * id 리스트가 바뀌거나, 같은 id의 (x,y)가 다르면 true. 그 외 (drag에 의한
 * z-index, selected 등 클라이언트 전용 필드) 변경은 무시 — xyflow 내부
 * drag store가 보존되도록 한다.
 */
function nodesLayoutChanged(
  prev: ReadonlyArray<{ id: string; position: { x: number; y: number } }>,
  next: ReadonlyArray<{ id: string; position: { x: number; y: number } }>
): boolean {
  if (prev.length !== next.length) return true;
  const map = new Map<string, { x: number; y: number }>();
  for (const n of prev) map.set(n.id, n.position);
  for (const n of next) {
    const p = map.get(n.id);
    if (!p) return true;
    if (p.x !== n.position.x || p.y !== n.position.y) return true;
  }
  return false;
}

function edgesRefChanged(
  prev: ReadonlyArray<{ id: string }>,
  next: ReadonlyArray<{ id: string }>
): boolean {
  if (prev.length !== next.length) return true;
  const seen = new Set<string>();
  for (const e of prev) seen.add(e.id);
  for (const e of next) if (!seen.has(e.id)) return true;
  return false;
}

/**
 * v0.7.124+: vault centroid (server coords) → screen coords 일괄 변환.
 * useEffect(첫 mount)와 handleMove(pan/zoom) 양쪽에서 동일 로직을 공유.
 * zoom 비례 radius 스케일을 동일하게 적용해 layer가 viewport와 함께 움직이게 한다.
 */
function vaultScreenFromCentroids(
  vaultCentroids: ReadonlyArray<VaultCentroid>,
  zoom: number,
  flowToScreenPosition: (p: { x: number; y: number }) => { x: number; y: number }
): Array<{ vault: string; x: number; y: number; radius: number }> {
  return vaultCentroids.map((vc) => {
    const center = flowToScreenPosition({ x: vc.x, y: vc.y });
    return {
      vault: vc.vault,
      x: center.x,
      y: center.y,
      radius: vc.radius * zoom,
    };
  });
}

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
  density = "normal",
  vaultCentroids,
  onPositionsChange,
}: Props) {
  const isDense = density === "dense";
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
  const { zoom } = useViewport();

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
      m.set(n.id, n);
    }
    return m;
  }, [nodes]);

  const rfNodes = useMemo(
    () =>
      nodes.map((n) => {
        const id = n.id;
        const type = n.type;
        const weight = n.weight ?? 1;
        const size = nodeSize(weight);
        const x = typeof n.x === "number" ? n.x : 0;
        const y = typeof n.y === "number" ? n.y : 0;
        const title = n.title ?? n.slug ?? id;
        return {
          id,
          type: "obsidian" as const,
          position: { x, y },
          // Primary UX: color means document type. Community ids stay backend/internal.
          data: { color: nodeColor(type), size, title },
        };
      }) as any,
    [nodes]
  );

  const rfEdges = useMemo(
    () =>
      edges.map((e, i) => ({
        id: `e${i}`,
        source: e.source,
        target: e.target,
        // 직선 edge (xyflow default bezier/smoothstep을 우회). 점 노드 사이의
        // 별자리 느낌을 위해 곡선 ❌ — 직선만 허용.
        type: "straight" as const,
        // Obsidian-style: relationship lines are quiet by default; hover reveals structure.
        // v0.7.48+: dark mode 시인성 개선 — stroke 두께/투명도 강화. 토큰이
        // opacity를 이미 들고 있어도 rfEdges에서 다시 0.16을 곱하면 사실상
        // 안 보이게 되므로, base는 토큰과 독립적인 값을 박아서 "기본 가시" 확보.
        style: {
          stroke: "var(--graph-edge)",
          strokeWidth: 1,
          strokeOpacity: 0.6,
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

  // v0.7.126+: drag-end 감지 wrapper. xyflow의 NodeChange 중 position change의
  // dragging=false가 drag 끝점. 그 시점에 (id → position) dict를 모아 부모에
  // 1회 callback. 그래야 매 mousemove마다 POST가 안 날아간다.
  const handleNodesChange = useCallback(
    (changes: Parameters<typeof onNodesChange>[0]) => {
      onNodesChange(changes);
      if (!onPositionsChange) return;
      const moved: Record<string, { x: number; y: number }> = {};
      for (const change of changes) {
        if (
          change.type === "position" &&
          change.dragging === false &&
          change.position &&
          typeof change.id === "string"
        ) {
          moved[change.id] = { x: change.position.x, y: change.position.y };
        }
      }
      if (Object.keys(moved).length > 0) onPositionsChange(moved);
    },
    [onNodesChange, onPositionsChange]
  );

  // Sync server-computed layout into xyflow's controlled state. We compare
  // id/position explicitly so dragging the user around does NOT get clobbered
  // (xyflow holds drag positions in its own store; we only re-sync when the
  // server layout reference actually shifts — e.g. orphan toggle, vault switch,
  // force-directed recompute).
  useEffect(() => {
    setFlowNodes((prev) => (nodesLayoutChanged(prev, rfNodes) ? rfNodes : prev));
  }, [rfNodes, setFlowNodes]);

  useEffect(() => {
    setFlowEdges((prev) => (edgesRefChanged(prev, rfEdges) ? rfEdges : prev));
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
      for (const edge of flowEdges) {
        if (edge.source === hoveredNode.id || edge.target === hoveredNode.id) {
          edgeIds.add(edge.id);
          nodeIds.add(String(edge.source));
          nodeIds.add(String(edge.target));
        }
      }
    }

    return {
      active: nodeIds.size > 0 || edgeIds.size > 0,
      nodeIds,
      edgeIds,
    };
  }, [flowEdges, flowNodes, nodeMap, hoveredEdgeId, hoveredNode, externalHighlightNodeId, externalHighlightType]);

  // v0.7.48: 클러스터링으로 뭉치고 푸는 기능(Multiscale zoom clustering) 제거.
  // 항상 개별 노드를 펼쳐진 상태(PLANET)로 렌더링합니다.
  const scaleMode = "PLANET";

  // 1) 줌 레벨에 따라 노드의 크기/투명도 매핑
  const displayNodes = useMemo(() => {
    return flowNodes.map((node) => {
      const id = node.id;
      const highlighted = focus.nodeIds.has(id);
      const persistent = persistentHighlightNodeId === id;
      
      const orgSize = (node.data as any).size ?? 6;
      let opacity = !focus.active || highlighted || persistent ? 1 : 0.22;
      const title = (node.data as any).title ?? id;
      const showLabel = !isDense || highlighted || persistent;

      // scaleMode === "PLANET"
      const isMoon = orgSize <= 6 && !highlighted && !persistent;
      const size = isMoon ? 4 : orgSize;
      opacity = isMoon ? 0.55 : opacity;

      return {
        ...node,
        data: {
          ...node.data,
          size,
          opacity,
          title,
          showLabel,
          highlighted,
          persistent,
        },
      };
    });
  }, [flowNodes, focus, persistentHighlightNodeId, isDense]);

  // 2) 엣지 강도 및 가시성 동적 조율
  // v0.7.123+ all-vault mode에서 edge의 source/target vault를 미리 추출.
  // dense 모드일 때 cross-vault edge는 0.08로 강하게 dim → 시각적 노이즈 제거.
  // intra-vault edge는 dense base(0.18) 유지 → vault 내부 연결은 약하게나마 보임.
  const crossVaultEdgeIds = useMemo(() => {
    if (!isDense) return new Set<string>();
    const out = new Set<string>();
    flowEdges.forEach((edge) => {
      const srcVault = String(edge.source).split(":", 1)[0];
      const tgtVault = String(edge.target).split(":", 1)[0];
      if (srcVault !== tgtVault) out.add(edge.id);
    });
    return out;
  }, [isDense, flowEdges]);

  // v0.7.127+: idle 상태에서는 edge object churn을 줄이기 위해 base edge set을 먼저 만든다.
  // dense 모드에서 특히 cross-vault edge opacity 계산이 고정이므로 focus가 없을 때는
  // 이 memoized 배열을 그대로 사용. highlight 시에만 overlay 스타일 객체를 새로 만든다.
  const baseDisplayEdges = useMemo(() => {
    return flowEdges.map((edge) => {
      const isCrossVault = crossVaultEdgeIds.has(edge.id);
      const opacity = isDense ? (isCrossVault ? 0.08 : 0.18) : 0.6;
      return {
        ...edge,
        animated: false,
        style: {
          ...(edge.style ?? {}),
          stroke: "var(--graph-edge)",
          strokeWidth: 1,
          strokeOpacity: opacity,
        },
      };
    });
  }, [flowEdges, isDense, crossVaultEdgeIds]);

  const displayEdges = useMemo(() => {
    if (!focus.active) return baseDisplayEdges;
    return baseDisplayEdges.map((edge) => {
      const highlighted = focus.edgeIds.has(edge.id);
      return {
        ...edge,
        animated: highlighted && !isDense,
        style: {
          ...(edge.style ?? {}),
          stroke: highlighted ? "var(--graph-edge-highlight)" : "var(--graph-edge)",
          strokeWidth: highlighted ? 1.5 : 1,
          strokeOpacity: highlighted ? 0.85 : 0.18,
        },
      };
    });
  }, [baseDisplayEdges, focus, isDense]);

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

  // v0.7.123+ vault halo 색상: dense 모드 + vaultCentroids 있을 때만
  // vault별 색을 결정적으로 부여. 정렬된 vault 이름 → index → 팔레트 매핑.
  const vaultColors = useMemo(() => {
    if (!isDense || !vaultCentroids) return new Map<string, string>();
    const sortedVaults = [...new Set(vaultCentroids.map((vc) => vc.vault))].sort();
    const map = new Map<string, string>();
    sortedVaults.forEach((vname, idx) => {
      map.set(vname, `var(--graph-vault-halo-${(idx % 6) + 1})`);
    });
    return map;
  }, [isDense, vaultCentroids]);

  // v0.7.123+ vault halo/label을 screen 좌표로 변환. xyflow v12에서
  // <ReactFlow> children은 viewport transform을 자동으로 받지 않으므로,
  // layer를 ReactFlow 바깥 형제로 두고 useViewport/flowToScreenPosition으로
  // 매 render + onMove 시 server → screen 좌표 변환. zoom/pan 따라 halo와
  // 라벨이 함께 움직인다.
  const [vaultScreenPositions, setVaultScreenPositions] = useState<
    Array<{ vault: string; x: number; y: number; radius: number }>
  >([]);
  useEffect(() => {
    if (!isDense || !vaultCentroids || vaultCentroids.length === 0) {
      setVaultScreenPositions([]);
      return;
    }
    const next = vaultScreenFromCentroids(vaultCentroids, zoom, flowToScreenPosition);
    setVaultScreenPositions(next);
    // v0.7.124+: zoom/pan 시의 재계산은 handleMove가 담당 (mount 1회 + vaultCentroids
    // 변경 시점에만 동기화). zoom을 deps에 넣으면 미세 pan마다 setState 폭증.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [vaultCentroids, isDense, flowToScreenPosition]);

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
    // v0.7.123+: pan/zoom 이동 시 vault halo/label도 server → screen 좌표 재계산.
    // useViewport는 useEffect dep로 zoom만 받지만 pan은 onMove가 직접 trigger.
    if (isDense && vaultCentroids && vaultCentroids.length > 0) {
      setVaultScreenPositions(
        vaultScreenFromCentroids(vaultCentroids, zoom, flowToScreenPosition)
      );
    }
  }, [rfNodesById, flowToScreenPosition, isDense, vaultCentroids, zoom]);

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
        onNodesChange={handleNodesChange as any}
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
        // Patch 7: translateExtent 확장 — 서버 layout 좌표(±500)에 여유.
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

      {/* v0.7.123+ all-vault dense 모드에서 vault halo + centroid 라벨.
          layer가 viewport transform 외부에 있으므로 server 좌표를 screen 좌표로
          변환해서 fixed로 그린다. zoom/pan 시 vaultScreenPositions가 갱신되며
          halo/label이 노드와 함께 따라간다. */}
      {isDense && vaultScreenPositions.length > 0 && (
        <div
          className="graph-vault-halo-layer"
          style={{
            position: "absolute",
            inset: 0,
            pointerEvents: "none",
            zIndex: 0,
          }}
          aria-hidden
        >
          {vaultScreenPositions.map((vc) => {
            const color = vaultColors.get(vc.vault) ?? "var(--graph-vault-halo-1)";
            return (
              <div
                key={vc.vault}
                className="graph-vault-halo"
                data-vault={vc.vault}
                style={{
                  position: "absolute",
                  left: vc.x,
                  top: vc.y,
                  width: vc.radius * 2,
                  height: vc.radius * 2,
                  transform: "translate(-50%, -50%)",
                  borderRadius: "50%",
                  background: `radial-gradient(circle, ${color} 0%, transparent 70%)`,
                  opacity: 0.18,
                  pointerEvents: "none",
                }}
              />
            );
          })}
          {vaultScreenPositions.map((vc) => (
            <div
              key={`${vc.vault}-label`}
              className="graph-vault-label"
              data-vault={vc.vault}
              style={{
                position: "absolute",
                left: vc.x,
                top: vc.y - vc.radius - 8,
                transform: "translate(-50%, -100%)",
                color: vaultColors.get(vc.vault) ?? "var(--graph-vault-halo-1)",
                fontSize: 13,
                fontWeight: 700,
                letterSpacing: "0.05em",
                textShadow: "0 0 6px var(--graph-canvas-bg), 0 0 12px var(--graph-canvas-bg)",
                whiteSpace: "nowrap",
                pointerEvents: "none",
              }}
            >
              {vc.vault}
            </div>
          ))}
        </div>
      )}

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
