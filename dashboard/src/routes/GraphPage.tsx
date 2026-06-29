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
    <div className="graph-page-shell">
      <div className="graph-page-toolbar">
        <h1>Graph</h1>
        <div className="graph-page-meta" aria-label="그래프 상태">
          <strong>{vault}</strong>
          <span>{visibleNodes.length}/{graph.nodes.length} nodes</span>
          <span>{visibleEdges.length} edges</span>
          {orphanCount > 0 && hideOrphans && <span>{orphanCount} orphan 숨김</span>}
        </div>
        <label className="graph-page-toggle">
          <input
            type="checkbox"
            checked={hideOrphans}
            onChange={(e) => setHideOrphans(e.target.checked)}
          />
          고아 숨김
        </label>
      </div>
      <div className="graph-canvas-frame">
        <GraphCanvas
          nodes={visibleNodes}
          edges={visibleEdges}
          // 데스크탑: 1회 click → navigate
          onNodeClick={(slug) => navigate(`/page/${vault}/${slug}`)}
          // 모바일/데스크탑 공통: 더블 click/tap → navigate
          // (GraphCanvas 내부에서 coarse pointer 검출 + 320ms tap 디바운스로 처리)
          onNodeDoubleClick={(slug) => navigate(`/page/${vault}/${slug}`)}
        />
      </div>
    </div>
  );
}
