import { ReactFlow, Background, Controls, MiniMap } from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { useMemo } from "react";
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

// v0.6.10 Patch A1/A2/A3 — dark theme + server-side force layout (x/y 사용).
// - 백엔드가 nodes[i].x/y를 Fruchterman-Reingold spring algorithm으로 계산 후 반환.
// - fnv1a 폴백 제거 (서버 결정성 보장).
// - 컨테이너/노드/엣지 모두 dark navy 톤.
function nodeColor(type: string | undefined): string {
  if (!type) return DEFAULT_COLOR;
  return TYPE_COLORS[type] ?? DEFAULT_COLOR;
}

export function GraphCanvas({ nodes, edges, onNodeClick }: Props) {
  const rfNodes = useMemo(
    () =>
      nodes.map((n) => {
        const id = (n as any).id ?? n.slug;
        const type = (n as any).type ?? n.type;
        // weight = in-degree; size = sqrt scale.
        const weight = (n as any).weight ?? 1;
        const size = 16 + Math.sqrt(Math.max(weight, 1)) * 8;
        // 서버 계산 좌표 사용. 없으면 0,0으로 fallback.
        const x = typeof n.x === "number" ? n.x : 0;
        const y = typeof n.y === "number" ? n.y : 0;
        return {
          id,
          data: { label: (n as any).title ?? n.title },
          position: { x, y },
          style: {
            background: nodeColor(type),
            width: size,
            height: size,
            fontSize: 11,
            color: "#e5e7eb", // light gray text on dark bg
            border: "1px solid rgba(255,255,255,0.18)",
          },
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
        style: { stroke: "#4a5568", strokeWidth: 1 }, // 어두운 회색 톤
      })),
    [edges]
  );

  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        background: "#0a0e1a", // 어두운 navy 배경
      }}
    >
      <ReactFlow
        nodes={rfNodes}
        edges={rfEdges}
        onNodeClick={(_, n) => onNodeClick?.(n.id)}
        fitView
      >
        {/* Patch A2: dark background — xyflow background color 오버라이드 */}
        <Background color="#374151" bgColor="#0a0e1a" size={1} />
        <Controls
          style={{
            background: "#1f2937",
            borderColor: "#374151",
            color: "#e5e7eb",
          }}
        />
        <MiniMap
          style={{ background: "#1f2937" }}
          nodeColor={(n) => nodeColor((n.data as any)?.type)}
          maskColor="rgba(10, 14, 26, 0.7)"
        />
      </ReactFlow>
    </div>
  );
}
