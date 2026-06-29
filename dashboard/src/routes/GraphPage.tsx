import { useEffect, useMemo, useState } from "react";
import { useNavigate, useOutletContext } from "react-router-dom";
import { GraphCanvas } from "../components/GraphCanvas";
import type { Graph, GraphNode } from "../types";

/**
 * GraphPage — dark xyflow canvas + orphan hide toggle.
 * v0.6.10+:
 * - 백엔드가 nodes[i].x/y force-directed 좌표 제공.
 * - weight=0 (고아, in-degree 없음) 노드를 기본적으로 숨김.
 * - "고아 숨김" 체크박스로 토글 (기본 ON).
 */
export function GraphPage() {
  const [graph, setGraph] = useState<Graph>({ nodes: [], edges: [] });
  const [hideOrphans, setHideOrphans] = useState(true); // 기본 ON
  const navigate = useNavigate();
  const { vault } = useOutletContext<{ vault: string }>();

  useEffect(() => {
    if (!vault) return;
    fetch(`/api/vaults/${encodeURIComponent(vault)}/graph`)
      .then((r) => (r.ok ? r.json() : { nodes: [], edges: [] }))
      .then((d) => setGraph({ nodes: d.nodes ?? [], edges: d.edges ?? [] }))
      .catch(() => setGraph({ nodes: [], edges: [] }));
  }, [vault]);

  // 표시할 노드 (orphan 가시성 토글 + 연결된 엣지만 필터링)
  const visibleNodes = useMemo<GraphNode[]>(() => {
    if (!hideOrphans) return graph.nodes;
    return graph.nodes.filter((n) => (n.weight ?? 0) > 0);
  }, [graph.nodes, hideOrphans]);

  const visibleEdges = useMemo(() => {
    const visibleIds = new Set(visibleNodes.map((n) => n.id ?? n.slug));
    return graph.edges.filter((e) => {
      const s = (e as any).source ?? e.source_slug;
      const t = (e as any).target ?? e.target_slug;
      return visibleIds.has(s) && visibleIds.has(t);
    });
  }, [graph.edges, visibleNodes]);

  const orphanCount = useMemo(
    () => graph.nodes.filter((n) => (n.weight ?? 0) === 0).length,
    [graph.nodes]
  );

  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column" }}>
      <div style={{ marginBottom: 16, display: "flex", alignItems: "flex-end", gap: 24 }}>
        <div style={{ flex: 1 }}>
          <h1>Graph</h1>
          <p className="text-muted" style={{ fontSize: 14, marginTop: 4 }}>
            in <strong>{vault}</strong> · 노드를 클릭하면 페이지로 이동합니다 ·{" "}
            {visibleNodes.length} / {graph.nodes.length} nodes · {visibleEdges.length} edges
            {orphanCount > 0 && hideOrphans && ` · ${orphanCount} orphan 숨김`}
          </p>
        </div>
        <label
          style={{
            display: "flex",
            alignItems: "center",
            gap: 6,
            fontSize: 13,
            color: "var(--color-text-muted)",
            cursor: "pointer",
            userSelect: "none",
          }}
        >
          <input
            type="checkbox"
            checked={hideOrphans}
            onChange={(e) => setHideOrphans(e.target.checked)}
          />
          고아 숨김
        </label>
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
          nodes={visibleNodes}
          edges={visibleEdges}
          onNodeClick={(slug) => navigate(`/page/${vault}/${slug}`)}
        />
      </div>
    </div>
  );
}
