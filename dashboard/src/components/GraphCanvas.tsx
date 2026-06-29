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
  decision: "#a855f7",   // purple
  concept: "#22c55e",    // green
  manual: "#3b82f6",     // blue
  pattern: "#f97316",    // orange
  insight: "#eab308",    // yellow
  journal: "#06b6d4",    // cyan
  person: "#ec4899",     // pink
  comparison: "#ef4444", // red
  tool: "#6b7280",       // gray
  rule: "#6366f1",       // indigo
};
const DEFAULT_COLOR = "#9ca3af"; // 미분류 (type='?') 회색

// FNV-1a 32-bit hash — deterministic position용 (slug → 균등 분포 정수).
// 같은 vault → 같은 노드 위치 보장 (재방문 시 layout 일관).
function fnv1a(str: string): number {
  let h = 0x811c9dc5;
  for (let i = 0; i < str.length; i++) {
    h ^= str.charCodeAt(i);
    h = (h + ((h << 1) + (h << 4) + (h << 7) + (h << 8) + (h << 24))) >>> 0;
  }
  return h;
}

function nodeColor(type: string | undefined): string {
  if (!type) return DEFAULT_COLOR;
  return TYPE_COLORS[type] ?? DEFAULT_COLOR;
}

export function GraphCanvas({ nodes, edges, onNodeClick }: Props) {
  const rfNodes = useMemo(
    () =>
      nodes.map((n) => {
        const id = (n as any).id ?? n.slug;
        // Patch #1: deterministic position — slug 기반 fnv1a 해시.
        const hx = fnv1a(id);
        const hy = fnv1a(id + "y");
        const type = (n as any).type ?? n.type;
        // Patch #3: in-degree(weight) 기반 노드 크기 — sqrt 스케일.
        const weight = (n as any).weight ?? 1;
        const size = 16 + Math.sqrt(Math.max(weight, 1)) * 8;
        return {
          id,
          data: { label: (n as any).title ?? n.title },
          position: { x: (hx >>> 0) % 800, y: (hy >>> 0) % 600 },
          // Patch #2: type별 색상 + Patch #3: 가변 크기.
          style: {
            background: nodeColor(type),
            width: size,
            height: size,
            fontSize: 11,
            color: "#fff",
            border: "1px solid rgba(0,0,0,0.15)",
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
      })),
    [edges]
  );

  return (
    <div style={{ width: "100%", height: "100%" }}>
      <ReactFlow
        nodes={rfNodes}
        edges={rfEdges}
        onNodeClick={(_, n) => onNodeClick?.(n.id)}
        fitView
      >
        <Background />
        <Controls />
        <MiniMap />
      </ReactFlow>
    </div>
  );
}