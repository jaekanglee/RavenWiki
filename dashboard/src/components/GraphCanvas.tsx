import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  ReactFlowProvider,
  useReactFlow,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { useCallback, useEffect, useMemo, useState } from "react";
import type { GraphNode, GraphEdge } from "../types";

interface Props {
  nodes: GraphNode[];
  edges: GraphEdge[];
  onNodeClick?: (slug: string) => void;
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

// ───────────────────────────────────────────────────────────────────────────
// v0.6.11+ Graph — pinch zoom 후 노드 사라짐 fix.
//
// 변경 사항 (B 묶음 후속 패치):
//   Patch 5: ReactFlowProvider + useReactFlow().fitView() programmatic 호출.
//            - prop `fitView`는 mount 시 1회만 실행. 데이터 변경 후에는
//              재fit 안 함 → orphan toggle / vault 변경 후 빈 화면.
//            - useEffect([nodes, edges])에서 fitView({ duration: 300, padding: 0.2 })
//              호출 → 데이터 변경 시 자동 재중심.
//   Patch 6: zoom 범위 완화 (minZoom 0.1→0.05, maxZoom 3→4).
//            - pinch zoom out 시 노드가 너무 작아져 화면 밖으로 사라지는 문제.
//   Patch 7: translateExtent 확장 ([-10000,10000] → [-50000,50000]).
//            - 서버 spring layout 결과는 vault 크기에 따라 ±10000까지 갈 수 있음.
//              translateExtent가 너무 작으면 xyflow가 viewport를 clamp해서 노드가
//              화면 밖으로 밀려남.
// ───────────────────────────────────────────────────────────────────────────

export function nodeColor(type: string | undefined): string {
  if (!type) return DEFAULT_COLOR;
  return TYPE_COLORS[type] ?? DEFAULT_COLOR;
}

// 노드 크기: 8px base + sqrt(weight)×6 — weight=1→14, weight=4→20, weight=9→26
export function nodeSize(weight: number | undefined): number {
  return 8 + Math.sqrt(Math.max(weight ?? 1, 1)) * 6;
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
function ObsidianNode({ data }: { data: { color: string; size: number } }) {
  // xyflow v12는 node에 `data`만 custom으로 전달받음.
  // 좌표/타이틀은 onMouseEnter에서 GraphNode 인덱스로 조회 (아래 handle).
  return (
    <div
      className="obsidian-node"
      style={{
        width: data.size,
        height: data.size,
        borderRadius: "50%",
        background: data.color,
        border: "1px solid rgba(255,255,255,0.3)",
        boxShadow: "0 0 0 1px rgba(0,0,0,0.4)",
        cursor: "pointer",
        transition: "transform 120ms ease-out, box-shadow 120ms ease-out",
      }}
      onMouseEnter={(e) => {
        (e.currentTarget as HTMLDivElement).style.transform = "scale(1.6)";
        (e.currentTarget as HTMLDivElement).style.boxShadow =
          "0 0 0 2px rgba(255,255,255,0.6), 0 0 8px rgba(255,255,255,0.25)";
      }}
      onMouseLeave={(e) => {
        (e.currentTarget as HTMLDivElement).style.transform = "scale(1)";
        (e.currentTarget as HTMLDivElement).style.boxShadow =
          "0 0 0 1px rgba(0,0,0,0.4)";
      }}
    />
  );
}

const nodeTypes = { obsidian: ObsidianNode };

function GraphCanvasInner({ nodes, edges, onNodeClick }: Props) {
  // hover된 노드 ID — label overlay 표시용
  const [hoveredNode, setHoveredNode] = useState<{
    id: string;
    title: string;
    type: string | undefined;
    weight: number;
    x: number; // viewport (screen) px
    y: number;
  } | null>(null);

  // Patch 5: useReactFlow hook — programmatic fitView 호출용.
  // ReactFlowProvider 안에서만 동작 → GraphCanvas를 Provider로 wrap (export 시).
  const { fitView } = useReactFlow();

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
        return {
          id,
          // type 필수 — xyflow custom renderer 사용
          type: "obsidian",
          position: { x, y },
          // size/color는 data로 ObsidianNode에 전달
          data: { color: nodeColor(type), size },
          // xyflow 자체는 layout 자유: width/height 지정 안 함. nodeWidth/Height 기본 사용 안 함.
        };
      }),
    [nodes]
  );

  const rfEdges = useMemo(
    () =>
      edges.map((e, i) => ({
        id: `e${i}`,
        source: (e as any).source ?? e.source_slug,
        target: (e as any).target ?? e.target_slug,
        style: { stroke: "rgba(148, 163, 184, 0.35)", strokeWidth: 0.8 }, // 옅은 slate
      })),
    [edges]
  );

  // Patch 5: 데이터 변경 시 fitView 재호출.
  // - mount 시 (rfNodes[0] 한 번 fit)
  // - orphan toggle / vault 변경 / force-directed 재계산 후 자동 재중심.
  // - 이전 mount 1회 한정 → 빈 화면.
  useEffect(() => {
    if (rfNodes.length === 0) return;
    // 다음 tick에 호출 — xyflow가 viewport 측정을 끝낸 후 fitView가 동작.
    const id = window.setTimeout(() => {
      fitView({ duration: 300, padding: 0.2 });
    }, 50);
    return () => window.clearTimeout(id);
  }, [rfNodes, rfEdges, fitView]);

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
      setHoveredNode({
        id: node.id,
        title: meta.title,
        type: meta.type,
        weight: meta.weight ?? 0,
        x: node.position.x + size / 2,
        y: node.position.y + size / 2,
      });
    },
    [nodeMap]
  );

  const handleNodeLeave = useCallback(() => {
    setHoveredNode(null);
  }, []);

  const handleNodeClick = useCallback(
    (_: React.MouseEvent, n: { id: string }) => {
      onNodeClick?.(n.id);
    },
    [onNodeClick]
  );

  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        position: "relative",
        background: "#0a0e1a",
        // Patch 4: 모바일에서 브라우저 기본 pinch/scroll 방지
        touchAction: "none",
        userSelect: "none",
        WebkitTapHighlightColor: "transparent",
        overflow: "hidden",
      }}
    >
      <ReactFlow
        nodes={rfNodes}
        edges={rfEdges}
        nodeTypes={nodeTypes}
        onNodeClick={handleNodeClick}
        onNodeMouseEnter={handleNodeEnter}
        onNodeMouseLeave={handleNodeLeave}
        // Patch 5: programmatic fitView 사용 → prop `fitView` 제거 (중복 fit 방지).
        // Patch 3: 모바일/데스크탑 gesture 강화
        panOnDrag
        panOnScroll
        zoomOnScroll
        zoomOnPinch
        selectionOnDrag={false} // drag = pan, click = select (텍스트 선택 방지)
        // Patch 6: zoom 범위 완화 — pinch zoom out 시 노드 사라짐 방지.
        minZoom={0.05}
        maxZoom={4}
        // Patch 7: translateExtent 확장 — 서버 spring layout 결과 (±10000)에 여유.
        //   xyflow v12는 viewport를 translateExtent로 clamp하므로 너무 작으면
        //   노드가 viewport 밖으로 밀려나 사라짐.
        translateExtent={[
          [-50000, -50000],
          [50000, 50000],
        ]}
        proOptions={{ hideAttribution: true }}
      >
        <Background color="#1f2937" bgColor="#0a0e1a" size={1} gap={32} />
        <Controls
          style={{
            background: "#1f2937",
            borderColor: "#374151",
            color: "#e5e7eb",
          }}
          showInteractive={false}
        />
        <MiniMap
          style={{ background: "#1f2937" }}
          nodeColor={(n) => (n.data as any)?.color ?? DEFAULT_COLOR}
          nodeStrokeColor="rgba(255,255,255,0.3)"
          nodeBorderRadius={50}
          maskColor="rgba(10, 14, 26, 0.75)"
          pannable
          zoomable
        />
      </ReactFlow>

      {/* Patch 2: hover overlay — xyflow 외부 absolute div로 label 표시.
          xyflow 노드 자체에는 텍스트 0px → 텍스트 오버랩 0. */}
      {hoveredNode && (
        <div
          data-testid="graph-hover-label"
          style={{
            position: "absolute",
            left: hoveredNode.x,
            top: hoveredNode.y,
            transform: "translate(-50%, calc(-100% - 14px))",
            pointerEvents: "none",
            background: "rgba(17, 24, 39, 0.95)",
            color: "#e5e7eb",
            padding: "6px 10px",
            borderRadius: 6,
            fontSize: 12,
            fontWeight: 500,
            lineHeight: 1.35,
            border: "1px solid #374151",
            boxShadow: "0 6px 20px rgba(0,0,0,0.5)",
            whiteSpace: "nowrap",
            maxWidth: 320,
            zIndex: 10,
          }}
        >
          <div style={{ fontWeight: 600 }}>{hoveredNode.title}</div>
          <div
            style={{
              fontSize: 10,
              color: "#9ca3af",
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
