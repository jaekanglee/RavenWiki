import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { GraphCanvas } from "../components/GraphCanvas";
import type { Graph } from "../types";

export function GraphPage() {
  const [graph, setGraph] = useState<Graph>({ nodes: [], edges: [] });
  const navigate = useNavigate();

  useEffect(() => {
    fetch("/api/graph.json")
      .then((r) => (r.ok ? r.json() : { nodes: [], edges: [] }))
      .then(setGraph)
      .catch(() => setGraph({ nodes: [], edges: [] }));
  }, []);

  return (
    <div className="h-full">
      <h1 className="text-2xl font-bold mb-4">🕸 Graph</h1>
      <div style={{ height: "calc(100vh - 200px)", minHeight: 400 }}>
        <GraphCanvas
          nodes={graph.nodes}
          edges={graph.edges}
          onNodeClick={(slug) => navigate(`/page/${slug}`)}
        />
      </div>
    </div>
  );
}
