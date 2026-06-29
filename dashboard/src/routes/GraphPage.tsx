import { useEffect, useState } from "react";
import { useNavigate, useOutletContext } from "react-router-dom";
import { GraphCanvas } from "../components/GraphCanvas";
import type { Graph } from "../types";

/**
 * GraphPage — keeps the dark xyflow canvas as its essence.
 * Only applies Rausch accent to the title-bar interaction.
 * No theme bleed onto the canvas itself.
 */
export function GraphPage() {
  const [graph, setGraph] = useState<Graph>({ nodes: [], edges: [] });
  const navigate = useNavigate();
  const { vault } = useOutletContext<{ vault: string }>();

  useEffect(() => {
    if (!vault) return;
    fetch(`/api/vaults/${encodeURIComponent(vault)}/graph`)
      .then((r) => (r.ok ? r.json() : { nodes: [], edges: [] }))
      .then((d) => setGraph({ nodes: d.nodes ?? [], edges: d.edges ?? [] }))
      .catch(() => setGraph({ nodes: [], edges: [] }));
  }, [vault]);

  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column" }}>
      <div style={{ marginBottom: 16 }}>
        <h1>Graph</h1>
        <p className="text-muted" style={{ fontSize: 14, marginTop: 4 }}>
          in <strong>{vault}</strong> · 노드를 클릭하면 페이지로 이동합니다 ·{" "}
          {graph.nodes.length} nodes · {graph.edges.length} edges
        </p>
      </div>
      <div
        style={{
          flex: 1,
          minHeight: 480,
          borderRadius: "var(--radius-md)",
          overflow: "hidden",
          border: "1px solid var(--color-hairline)",
        }}
      >
        <GraphCanvas
          nodes={graph.nodes}
          edges={graph.edges}
          onNodeClick={(slug) => navigate(`/page/${vault}/${slug}`)}
        />
      </div>
    </div>
  );
}