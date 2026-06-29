import { ReactFlow, Background, Controls, MiniMap } from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { useMemo } from "react";
import type { GraphNode, GraphEdge } from "../types";

interface Props {
  nodes: GraphNode[];
  edges: GraphEdge[];
  onNodeClick?: (slug: string) => void;
}

export function GraphCanvas({ nodes, edges, onNodeClick }: Props) {
  const rfNodes = useMemo(
    () =>
      nodes.map((n) => ({
        // endpoint key = id (GraphNode의 id 필드)
        id: (n as any).id ?? n.slug,
        data: { label: (n as any).title ?? n.title },
        position: { x: Math.random() * 800, y: Math.random() * 600 },
      })),
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
